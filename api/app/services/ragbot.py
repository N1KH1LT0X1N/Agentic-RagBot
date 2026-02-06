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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

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
        
        print("🔧 Initializing RagBot workflow...")
        start_time = time.time()
        
        # Save current directory
        import os
        original_dir = os.getcwd()
        
        try:
            # Change to RagBot root (parent of api directory)
            # This ensures vector store paths resolve correctly
            ragbot_root = Path(__file__).parent.parent.parent.parent
            os.chdir(ragbot_root)
            print(f"📂 Working directory: {ragbot_root}")
            
            self.guild = create_guild()
            self.initialized = True
            self.init_time = datetime.now()
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ RagBot initialized successfully ({elapsed:.0f}ms)")
        
        except Exception as e:
            print(f"❌ Failed to initialize RagBot: {e}")
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
            raise RuntimeError(f"Analysis failed: {str(e)}") from e
    
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
        """
        
        # Extract main prediction
        prediction = Prediction(
            disease=model_prediction["disease"],
            confidence=model_prediction["confidence"],
            probabilities=model_prediction.get("probabilities", {})
        )
        
        # Extract biomarker flags
        biomarker_flags = [
            BiomarkerFlag(**flag) 
            for flag in workflow_result.get("biomarker_flags", [])
        ]
        
        # Extract safety alerts
        safety_alerts = [
            SafetyAlert(**alert) 
            for alert in workflow_result.get("safety_alerts", [])
        ]
        
        # Extract key drivers
        key_drivers_data = workflow_result.get("key_drivers", [])
        key_drivers = []
        for driver in key_drivers_data:
            if isinstance(driver, dict):
                key_drivers.append(KeyDriver(**driver))
        
        # Disease explanation
        disease_exp_data = workflow_result.get("disease_explanation", {})
        disease_explanation = DiseaseExplanation(
            pathophysiology=disease_exp_data.get("pathophysiology", ""),
            citations=disease_exp_data.get("citations", []),
            retrieved_chunks=disease_exp_data.get("retrieved_chunks")
        )
        
        # Recommendations
        recs_data = workflow_result.get("recommendations", {})
        recommendations = Recommendations(
            immediate_actions=recs_data.get("immediate_actions", []),
            lifestyle_changes=recs_data.get("lifestyle_changes", []),
            monitoring=recs_data.get("monitoring", []),
            follow_up=recs_data.get("follow_up")
        )
        
        # Confidence assessment
        conf_data = workflow_result.get("confidence_assessment", {})
        confidence_assessment = ConfidenceAssessment(
            prediction_reliability=conf_data.get("prediction_reliability", "UNKNOWN"),
            evidence_strength=conf_data.get("evidence_strength", "UNKNOWN"),
            limitations=conf_data.get("limitations", []),
            reasoning=conf_data.get("reasoning")
        )
        
        # Alternative diagnoses
        alternative_diagnoses = workflow_result.get("alternative_diagnoses")
        
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
        
        # Agent outputs (preserve full detail)
        agent_outputs_data = workflow_result.get("agent_outputs", [])
        agent_outputs = []
        for agent_out in agent_outputs_data:
            if isinstance(agent_out, dict):
                agent_outputs.append(AgentOutput(**agent_out))
        
        # Workflow metadata
        workflow_metadata = {
            "sop_version": workflow_result.get("sop_version"),
            "processing_timestamp": workflow_result.get("processing_timestamp"),
            "agents_executed": len(agent_outputs),
            "workflow_success": True
        }
        
        # Conversational summary (if available)
        conversational_summary = workflow_result.get("conversational_summary")
        
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
        summary_parts.append("Hi there! 👋\n")
        summary_parts.append("Based on your biomarkers, I analyzed your results.\n")
        
        # Prediction
        confidence_emoji = "🔴" if prediction.confidence > 0.7 else "🟡"
        summary_parts.append(f"\n{confidence_emoji} **Primary Finding:** {prediction.disease}")
        summary_parts.append(f"   Confidence: {prediction.confidence:.0%}\n")
        
        # Safety alerts
        if safety_alerts:
            summary_parts.append("\n⚠️ **IMPORTANT SAFETY ALERTS:**")
            for alert in safety_alerts[:3]:  # Top 3
                summary_parts.append(f"   • {alert.biomarker}: {alert.message}")
                summary_parts.append(f"     → {alert.action}")
        
        # Key drivers
        if key_drivers:
            summary_parts.append("\n🔍 **Why this prediction?**")
            for driver in key_drivers[:3]:  # Top 3
                summary_parts.append(f"   • **{driver.biomarker}** ({driver.value}): {driver.explanation[:100]}...")
        
        # Recommendations
        if recommendations.immediate_actions:
            summary_parts.append("\n✅ **What You Should Do:**")
            for i, action in enumerate(recommendations.immediate_actions[:3], 1):
                summary_parts.append(f"   {i}. {action}")
        
        summary_parts.append("\nℹ️ **Important:** This is an AI-assisted analysis, NOT medical advice.")
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
