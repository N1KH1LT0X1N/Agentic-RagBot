"""
MediGuard AI RAG-Helper
Response Synthesizer Agent - Compiles all findings into final structured JSON
"""

import json
from typing import Dict, List, Any
from src.state import GuildState
from src.llm_config import llm_config
from langchain_core.prompts import ChatPromptTemplate


class ResponseSynthesizerAgent:
    """Agent that synthesizes all specialist findings into the final response"""
    
    def __init__(self):
        self.llm = llm_config.get_synthesizer()
    
    def synthesize(self, state: GuildState) -> GuildState:
        """
        Synthesize all agent outputs into final response.
        
        Args:
            state: Complete guild state with all agent outputs
        
        Returns:
            Updated state with final_response
        """
        print("\n" + "="*70)
        print("EXECUTING: Response Synthesizer Agent")
        print("="*70)
        
        model_prediction = state['model_prediction']
        patient_biomarkers = state['patient_biomarkers']
        patient_context = state.get('patient_context', {})
        agent_outputs = state.get('agent_outputs', [])
        
        # Collect findings from all agents
        findings = self._collect_findings(agent_outputs)
        
        print(f"\nSynthesizing findings from {len(agent_outputs)} specialist agents...")
        
        # Build structured response
        recs = self._build_recommendations(findings)
        response = {
            "patient_summary": self._build_patient_summary(patient_biomarkers, findings),
            "prediction_explanation": self._build_prediction_explanation(model_prediction, findings),
            "confidence_assessment": self._build_confidence_assessment(findings),
            "safety_alerts": self._build_safety_alerts(findings),
            "metadata": self._build_metadata(state),
            "biomarker_flags": self._build_biomarker_flags(findings),
            "key_drivers": self._build_key_drivers(findings),
            "disease_explanation": self._build_disease_explanation(findings),
            "recommendations": recs,
            "clinical_recommendations": recs,  # Alias for backward compatibility
            "alternative_diagnoses": self._build_alternative_diagnoses(findings),
            "analysis": {
                "biomarker_flags": self._build_biomarker_flags(findings),
                "safety_alerts": self._build_safety_alerts(findings),
                "key_drivers": self._build_key_drivers(findings),
                "disease_explanation": self._build_disease_explanation(findings),
                "recommendations": recs,
                "confidence_assessment": self._build_confidence_assessment(findings),
                "alternative_diagnoses": self._build_alternative_diagnoses(findings)
            }
        }
        
        # Generate patient-friendly summary
        response["patient_summary"]["narrative"] = self._generate_narrative_summary(
            model_prediction,
            findings,
            response
        )
        
        print("\nResponse synthesis complete")
        print(f"  - Patient summary: Generated")
        print(f"  - Prediction explanation: {len(response['prediction_explanation']['key_drivers'])} key drivers")
        print(f"  - Recommendations: {len(response['clinical_recommendations']['immediate_actions'])} immediate actions")
        print(f"  - Safety alerts: {len(response['safety_alerts'])} alerts")
        
        return {'final_response': response}
    
    def _collect_findings(self, agent_outputs: List) -> Dict[str, Any]:
        """Organize all agent findings by agent name"""
        findings = {}
        for output in agent_outputs:
            findings[output.agent_name] = output.findings
        return findings
    
    def _build_patient_summary(self, biomarkers: Dict, findings: Dict) -> Dict:
        """Build patient summary section"""
        biomarker_analysis = findings.get("Biomarker Analyzer", {})
        flags = biomarker_analysis.get('biomarker_flags', [])
        
        # Count biomarker statuses
        critical = len([f for f in flags if 'CRITICAL' in f.get('status', '')])
        abnormal = len([f for f in flags if f.get('status') != 'NORMAL'])
        
        return {
            "total_biomarkers_tested": len(biomarkers),
            "biomarkers_in_normal_range": len(flags) - abnormal,
            "biomarkers_out_of_range": abnormal,
            "critical_values": critical,
            "overall_risk_profile": biomarker_analysis.get('summary', 'Assessment complete'),
            "narrative": ""  # Will be filled later
        }
    
    def _build_prediction_explanation(self, model_prediction: Dict, findings: Dict) -> Dict:
        """Build prediction explanation section"""
        disease_explanation = findings.get("Disease Explainer", {})
        linker_findings = findings.get("Biomarker-Disease Linker", {})
        
        disease = model_prediction['disease']
        confidence = model_prediction['confidence']
        
        # Get key drivers
        key_drivers_raw = linker_findings.get('key_drivers', [])
        key_drivers = [
            {
                "biomarker": kd.get('biomarker'),
                "value": kd.get('value'),
                "contribution": kd.get('contribution'),
                "explanation": kd.get('explanation'),
                "evidence": kd.get('evidence', '')[:200]  # Truncate
            }
            for kd in key_drivers_raw
        ]
        
        return {
            "primary_disease": disease,
            "confidence": confidence,
            "key_drivers": key_drivers,
            "mechanism_summary": disease_explanation.get('mechanism_summary', disease_explanation.get('summary', '')),
            "pathophysiology": disease_explanation.get('pathophysiology', ''),
            "pdf_references": disease_explanation.get('citations', [])
        }

    def _build_biomarker_flags(self, findings: Dict) -> List[Dict]:
        biomarker_analysis = findings.get("Biomarker Analyzer", {})
        return biomarker_analysis.get('biomarker_flags', [])

    def _build_key_drivers(self, findings: Dict) -> List[Dict]:
        linker_findings = findings.get("Biomarker-Disease Linker", {})
        return linker_findings.get('key_drivers', [])

    def _build_disease_explanation(self, findings: Dict) -> Dict:
        disease_explanation = findings.get("Disease Explainer", {})
        return {
            "pathophysiology": disease_explanation.get('pathophysiology', ''),
            "citations": disease_explanation.get('citations', []),
            "retrieved_chunks": disease_explanation.get('retrieved_chunks')
        }
    
    def _build_recommendations(self, findings: Dict) -> Dict:
        """Build clinical recommendations section"""
        guidelines = findings.get("Clinical Guidelines", {})
        
        return {
            "immediate_actions": guidelines.get('immediate_actions', []),
            "lifestyle_changes": guidelines.get('lifestyle_changes', []),
            "monitoring": guidelines.get('monitoring', []),
            "guideline_citations": guidelines.get('guideline_citations', [])
        }
    
    def _build_confidence_assessment(self, findings: Dict) -> Dict:
        """Build confidence assessment section"""
        assessment = findings.get("Confidence Assessor", {})
        
        return {
            "prediction_reliability": assessment.get('prediction_reliability', 'UNKNOWN'),
            "evidence_strength": assessment.get('evidence_strength', 'UNKNOWN'),
            "limitations": assessment.get('limitations', []),
            "recommendation": assessment.get('recommendation', 'Consult healthcare provider'),
            "assessment_summary": assessment.get('assessment_summary', ''),
            "alternative_diagnoses": assessment.get('alternative_diagnoses', [])
        }

    def _build_alternative_diagnoses(self, findings: Dict) -> List[Dict]:
        assessment = findings.get("Confidence Assessor", {})
        return assessment.get('alternative_diagnoses', [])
    
    def _build_safety_alerts(self, findings: Dict) -> List[Dict]:
        """Build safety alerts section"""
        biomarker_analysis = findings.get("Biomarker Analyzer", {})
        return biomarker_analysis.get('safety_alerts', [])
    
    def _build_metadata(self, state: GuildState) -> Dict:
        """Build metadata section"""
        from datetime import datetime
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_version": "MediGuard AI RAG-Helper v1.0",
            "sop_version": "Baseline",
            "agents_executed": [output.agent_name for output in state.get('agent_outputs', [])],
            "disclaimer": "This is an AI-assisted analysis tool for patient self-assessment. It is NOT a substitute for professional medical advice, diagnosis, or treatment. Always consult qualified healthcare providers for medical decisions."
        }
    
    def _generate_narrative_summary(
        self,
        model_prediction,
        findings: Dict,
        response: Dict
    ) -> str:
        """Generate a patient-friendly narrative summary using LLM"""
        
        disease = model_prediction['disease']
        confidence = model_prediction['confidence']
        reliability = response['confidence_assessment']['prediction_reliability']
        
        # Get key points
        critical_count = response['patient_summary']['critical_values']
        abnormal_count = response['patient_summary']['biomarkers_out_of_range']
        key_drivers = response['prediction_explanation']['key_drivers']
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical AI assistant explaining test results to a patient.
            Write a clear, compassionate 3-4 sentence summary that:
            1. States the predicted condition and confidence level
            2. Highlights the most important biomarker findings
            3. Emphasizes the need for medical consultation
            4. Offers reassurance while being honest about findings
            
            Use patient-friendly language. Avoid medical jargon. Be supportive and clear."""),
            ("human", """Disease Predicted: {disease}
            Model Confidence: {confidence:.1%}
            Overall Reliability: {reliability}
            Critical Values: {critical}
            Out-of-Range Values: {abnormal}
            Top Biomarker Drivers: {drivers}
            
            Write a compassionate patient summary.""")
        ])
        
        chain = prompt | self.llm
        
        try:
            driver_names = [kd['biomarker'] for kd in key_drivers[:3]]
            
            response_obj = chain.invoke({
                "disease": disease,
                "confidence": confidence,
                "reliability": reliability,
                "critical": critical_count,
                "abnormal": abnormal_count,
                "drivers": ", ".join(driver_names) if driver_names else "Multiple biomarkers"
            })
            
            return response_obj.content.strip()
            
        except Exception as e:
            print(f"Warning: Narrative generation failed: {e}")
            return f"Your test results suggest {disease} with {confidence:.1%} confidence. {abnormal_count} biomarker(s) are out of normal range. Please consult with a healthcare provider for professional evaluation and guidance."


# Create agent instance for import
response_synthesizer_agent = ResponseSynthesizerAgent()
