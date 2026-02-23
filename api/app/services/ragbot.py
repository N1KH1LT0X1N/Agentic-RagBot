"""
RagBot Workflow Service
Wraps the RagBot workflow and formats comprehensive responses
"""

import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Ensure project root is in path for src imports
_project_root = str(Path(__file__).parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.workflow import create_guild
from src.state import PatientInput
from app.models.schemas import (
    AnalysisResponse, Analysis, Prediction, BiomarkerFlag,
    SafetyAlert, KeyDriver, DiseaseExplanation, Recommendations,
    ConfidenceAssessment, AgentOutput
)


class RagBotService:
    """
    Service class to manage RagBot workflow lifecycle.
    Initializes once, then handles multiple analysis requests.
    """
    
    def __init__(self):
        """Initialize the workflow (loads vector store, models, etc.)"""
        self.guild = None
        self.initialized = False
        self.init_time = None
    
    def initialize(self):
        """Initialize the Clinical Insight Guild (expensive operation)"""
        if self.initialized:
            return
        
        print("INFO: Initializing RagBot workflow...")
        start_time = time.time()
        
        import os
        
        try:
            # Set working directory via environment so vector store paths resolve
            # without a process-global os.chdir() (which is thread-unsafe).
            ragbot_root = Path(__file__).parent.parent.parent.parent
            os.environ["RAGBOT_ROOT"] = str(ragbot_root)
            print(f"INFO: Project root: {ragbot_root}")
            
            # Temporarily chdir only during initialization (single-threaded at startup)
            original_dir = os.getcwd()
            os.chdir(ragbot_root)
            
            self.guild = create_guild()
            self.initialized = True
            self.init_time = datetime.now()
            
            elapsed = (time.time() - start_time) * 1000
            print(f"OK: RagBot initialized successfully ({elapsed:.0f}ms)")
        
        except Exception as e:
            print(f"ERROR: Failed to initialize RagBot: {e}")
            raise
        
        finally:
            # Restore original directory
            os.chdir(original_dir)
    
    def get_uptime_seconds(self) -> float:
        """Get API uptime in seconds"""
        if not self.init_time:
            return 0.0
        return (datetime.now() - self.init_time).total_seconds()
    
    def is_ready(self) -> bool:
        """Check if service is ready to handle requests"""
        return self.initialized and self.guild is not None
    
    def analyze(
        self,
        biomarkers: Dict[str, float],
        patient_context: Dict[str, Any],
        model_prediction: Dict[str, Any],
        extracted_biomarkers: Dict[str, float] = None
    ) -> AnalysisResponse:
        """
        Run complete analysis workflow and format full detailed response.
        
        Args:
            biomarkers: Dictionary of biomarker names to values
            patient_context: Patient demographic information
            model_prediction: Disease prediction (disease, confidence, probabilities)
            extracted_biomarkers: Original extracted biomarkers (for natural language input)
        
        Returns:
            Complete AnalysisResponse with all details
        """
        if not self.is_ready():
            raise RuntimeError("RagBot service not initialized. Call initialize() first.")
        
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        try:
            # Create PatientInput
            patient_input = PatientInput(
                biomarkers=biomarkers,
                model_prediction=model_prediction,
                patient_context=patient_context
            )
            
            # Run workflow
            workflow_result = self.guild.run(patient_input)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Format response
            response = self._format_response(
                request_id=request_id,
                workflow_result=workflow_result,
                input_biomarkers=biomarkers,
                extracted_biomarkers=extracted_biomarkers,
                patient_context=patient_context,
                model_prediction=model_prediction,
                processing_time_ms=processing_time_ms
            )
            
            return response
        
        except Exception as e:
            # Re-raise with context
            raise RuntimeError(f"Analysis failed during workflow execution: {str(e)}") from e
    
    def _format_response(
        self,
        request_id: str,
        workflow_result: Dict[str, Any],
        input_biomarkers: Dict[str, float],
        extracted_biomarkers: Dict[str, float],
        patient_context: Dict[str, Any],
        model_prediction: Dict[str, Any],
        processing_time_ms: float
    ) -> AnalysisResponse:
        """
        Format complete detailed response from workflow result.
        Preserves ALL data from workflow execution.
        
        workflow_result is now the full LangGraph state dict containing:
        - final_response: dict from response_synthesizer
        - agent_outputs: list of AgentOutput objects
        - biomarker_flags: list of BiomarkerFlag objects
        - safety_alerts: list of SafetyAlert objects
        - sop_version, processing_timestamp, etc.
        """
        
        # The synthesizer output is nested inside final_response
        final_response = workflow_result.get("final_response", {}) or {}
        
        # Extract main prediction
        prediction = Prediction(
            disease=model_prediction["disease"],
            confidence=model_prediction["confidence"],
            probabilities=model_prediction.get("probabilities", {})
        )
        
        # Biomarker flags: prefer state-level data (BiomarkerFlag objects from validator),
        # fall back to synthesizer output
        state_flags = workflow_result.get("biomarker_flags", [])
        if state_flags:
            biomarker_flags = []
            for flag in state_flags:
                if hasattr(flag, 'model_dump'):
                    biomarker_flags.append(BiomarkerFlag(**flag.model_dump()))
                elif isinstance(flag, dict):
                    biomarker_flags.append(BiomarkerFlag(**flag))
        else:
            biomarker_flags_source = final_response.get("biomarker_flags", [])
            if not biomarker_flags_source:
                biomarker_flags_source = final_response.get("analysis", {}).get("biomarker_flags", [])
            biomarker_flags = [
                BiomarkerFlag(**flag) if isinstance(flag, dict) else BiomarkerFlag(**flag.model_dump())
                for flag in biomarker_flags_source
            ]
        
        # Safety alerts: prefer state-level data, fall back to synthesizer
        state_alerts = workflow_result.get("safety_alerts", [])
        if state_alerts:
            safety_alerts = []
            for alert in state_alerts:
                if hasattr(alert, 'model_dump'):
                    safety_alerts.append(SafetyAlert(**alert.model_dump()))
                elif isinstance(alert, dict):
                    safety_alerts.append(SafetyAlert(**alert))
        else:
            safety_alerts_source = final_response.get("safety_alerts", [])
            if not safety_alerts_source:
                safety_alerts_source = final_response.get("analysis", {}).get("safety_alerts", [])
            safety_alerts = [
                SafetyAlert(**alert) if isinstance(alert, dict) else SafetyAlert(**alert.model_dump())
                for alert in safety_alerts_source
            ]
        
        # Extract key drivers from synthesizer output
        key_drivers_data = final_response.get("key_drivers", [])
        if not key_drivers_data:
            key_drivers_data = final_response.get("analysis", {}).get("key_drivers", [])
        key_drivers = []
        for driver in key_drivers_data:
            if isinstance(driver, dict):
                key_drivers.append(KeyDriver(**driver))
        
        # Disease explanation from synthesizer
        disease_exp_data = final_response.get("disease_explanation", {})
        if not disease_exp_data:
            disease_exp_data = final_response.get("analysis", {}).get("disease_explanation", {})
        disease_explanation = DiseaseExplanation(
            pathophysiology=disease_exp_data.get("pathophysiology", ""),
            citations=disease_exp_data.get("citations", []),
            retrieved_chunks=disease_exp_data.get("retrieved_chunks")
        )
        
        # Recommendations from synthesizer
        recs_data = final_response.get("recommendations", {})
        if not recs_data:
            recs_data = final_response.get("clinical_recommendations", {})
        if not recs_data:
            recs_data = final_response.get("analysis", {}).get("recommendations", {})
        recommendations = Recommendations(
            immediate_actions=recs_data.get("immediate_actions", []),
            lifestyle_changes=recs_data.get("lifestyle_changes", []),
            monitoring=recs_data.get("monitoring", []),
            follow_up=recs_data.get("follow_up")
        )
        
        # Confidence assessment from synthesizer
        conf_data = final_response.get("confidence_assessment", {})
        if not conf_data:
            conf_data = final_response.get("analysis", {}).get("confidence_assessment", {})
        confidence_assessment = ConfidenceAssessment(
            prediction_reliability=conf_data.get("prediction_reliability", "UNKNOWN"),
            evidence_strength=conf_data.get("evidence_strength", "UNKNOWN"),
            limitations=conf_data.get("limitations", []),
            reasoning=conf_data.get("reasoning")
        )
        
        # Alternative diagnoses
        alternative_diagnoses = final_response.get("alternative_diagnoses")
        if alternative_diagnoses is None:
            alternative_diagnoses = final_response.get("analysis", {}).get("alternative_diagnoses")
        
        # Assemble complete analysis
        analysis = Analysis(
            biomarker_flags=biomarker_flags,
            safety_alerts=safety_alerts,
            key_drivers=key_drivers,
            disease_explanation=disease_explanation,
            recommendations=recommendations,
            confidence_assessment=confidence_assessment,
            alternative_diagnoses=alternative_diagnoses
        )
        
        # Agent outputs from state (these are src.state.AgentOutput objects)
        agent_outputs_data = workflow_result.get("agent_outputs", [])
        agent_outputs = []
        for agent_out in agent_outputs_data:
            if hasattr(agent_out, 'model_dump'):
                agent_outputs.append(AgentOutput(**agent_out.model_dump()))
            elif isinstance(agent_out, dict):
                agent_outputs.append(AgentOutput(**agent_out))
        
        # Workflow metadata
        workflow_metadata = {
            "sop_version": workflow_result.get("sop_version"),
            "processing_timestamp": workflow_result.get("processing_timestamp"),
            "agents_executed": len(agent_outputs),
            "workflow_success": True
        }
        
        # Conversational summary (if available)
        conversational_summary = final_response.get("conversational_summary")
        if not conversational_summary:
            conversational_summary = final_response.get("patient_summary", {}).get("narrative")
        
        # Generate conversational summary if not present
        if not conversational_summary:
            conversational_summary = self._generate_conversational_summary(
                prediction=prediction,
                safety_alerts=safety_alerts,
                key_drivers=key_drivers,
                recommendations=recommendations
            )
        
        # Assemble final response
        response = AnalysisResponse(
            status="success",
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            extracted_biomarkers=extracted_biomarkers,
            input_biomarkers=input_biomarkers,
            patient_context=patient_context,
            prediction=prediction,
            analysis=analysis,
            agent_outputs=agent_outputs,
            workflow_metadata=workflow_metadata,
            conversational_summary=conversational_summary,
            processing_time_ms=processing_time_ms,
            sop_version=workflow_result.get("sop_version", "Baseline")
        )
        
        return response
    
    def _generate_conversational_summary(
        self,
        prediction: Prediction,
        safety_alerts: list,
        key_drivers: list,
        recommendations: Recommendations
    ) -> str:
        """Generate a simple conversational summary"""
        
        summary_parts = []
        summary_parts.append("Hi there!\n")
        summary_parts.append("Based on your biomarkers, I analyzed your results.\n")
        
        # Prediction
        summary_parts.append(f"\nPrimary Finding: {prediction.disease}")
        summary_parts.append(f"   Confidence: {prediction.confidence:.0%}\n")
        
        # Safety alerts
        if safety_alerts:
            summary_parts.append("\nIMPORTANT SAFETY ALERTS:")
            for alert in safety_alerts[:3]:  # Top 3
                summary_parts.append(f"   - {alert.biomarker}: {alert.message}")
                summary_parts.append(f"     Action: {alert.action}")
        
        # Key drivers
        if key_drivers:
            summary_parts.append("\nWhy this prediction?")
            for driver in key_drivers[:3]:  # Top 3
                summary_parts.append(f"   - {driver.biomarker} ({driver.value}): {driver.explanation[:100]}...")
        
        # Recommendations
        if recommendations.immediate_actions:
            summary_parts.append("\nWhat You Should Do:")
            for i, action in enumerate(recommendations.immediate_actions[:3], 1):
                summary_parts.append(f"   {i}. {action}")
        
        summary_parts.append("\nImportant: This is an AI-assisted analysis, NOT medical advice.")
        summary_parts.append("   Please consult a healthcare professional for proper diagnosis and treatment.")
        
        return "\n".join(summary_parts)


# Global service instance (singleton)
_ragbot_service = None


def get_ragbot_service() -> RagBotService:
    """Get or create the global RagBot service instance"""
    global _ragbot_service
    if _ragbot_service is None:
        _ragbot_service = RagBotService()
    return _ragbot_service
