"""
MediGuard AI RAG-Helper
Confidence Assessor Agent - Evaluates prediction reliability
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Dict, List
from src.state import GuildState, AgentOutput
from src.llm_config import llm_config
from langchain_core.prompts import ChatPromptTemplate


class ConfidenceAssessorAgent:
    """Agent that assesses the reliability and limitations of the prediction"""
    
    def __init__(self):
        self.llm = llm_config.analyzer
    
    def assess(self, state: GuildState) -> GuildState:
        """
        Assess prediction confidence and identify limitations.
        
        Args:
            state: Current guild state
        
        Returns:
            Updated state with confidence assessment
        """
        print("\n" + "="*70)
        print("EXECUTING: Confidence Assessor Agent")
        print("="*70)
        
        model_prediction = state['model_prediction']
        disease = model_prediction['disease']
        ml_confidence = model_prediction['confidence']
        probabilities = model_prediction.get('probabilities', {})
        biomarkers = state['patient_biomarkers']
        
        # Collect previous agent findings
        biomarker_analysis = self._get_agent_findings(state, "Biomarker Analyzer")
        disease_explanation = self._get_agent_findings(state, "Disease Explainer")
        linker_findings = self._get_agent_findings(state, "Biomarker-Disease Linker")
        
        print(f"\nAssessing confidence for {disease} prediction...")
        
        # Evaluate evidence strength
        evidence_strength = self._evaluate_evidence_strength(
            biomarker_analysis,
            disease_explanation,
            linker_findings
        )
        
        # Identify limitations
        limitations = self._identify_limitations(
            biomarkers,
            biomarker_analysis,
            probabilities
        )
        
        # Calculate aggregate reliability
        reliability = self._calculate_reliability(
            ml_confidence,
            evidence_strength,
            len(limitations)
        )
        
        # Generate assessment summary
        assessment_summary = self._generate_assessment(
            disease,
            ml_confidence,
            reliability,
            evidence_strength,
            limitations
        )
        
        # Create agent output
        output = AgentOutput(
            agent_name="Confidence Assessor",
            findings={
                "prediction_reliability": reliability,
                "ml_confidence": ml_confidence,
                "evidence_strength": evidence_strength,
                "limitations": limitations,
                "assessment_summary": assessment_summary,
                "recommendation": self._get_recommendation(reliability),
                "alternative_diagnoses": self._get_alternatives(probabilities)
            }
        )
        
        # Update state
        print(f"\n✓ Confidence assessment complete")
        print(f"  - Prediction reliability: {reliability}")
        print(f"  - Evidence strength: {evidence_strength}")
        print(f"  - Limitations identified: {len(limitations)}")
        
        return {'agent_outputs': [output]}
    
    def _get_agent_findings(self, state: GuildState, agent_name: str) -> dict:
        """Extract findings from a specific agent"""
        for output in state.get('agent_outputs', []):
            if output.agent_name == agent_name:
                return output.findings
        return {}
    
    def _evaluate_evidence_strength(
        self,
        biomarker_analysis: dict,
        disease_explanation: dict,
        linker_findings: dict
    ) -> str:
        """Evaluate the strength of supporting evidence"""
        
        score = 0
        max_score = 5
        
        # Check biomarker validation quality
        flags = biomarker_analysis.get('biomarker_flags', [])
        abnormal_count = len([f for f in flags if f.get('status') != 'NORMAL'])
        if abnormal_count >= 3:
            score += 1
        if abnormal_count >= 5:
            score += 1
        
        # Check disease explanation quality
        if disease_explanation.get('retrieval_quality', 0) >= 3:
            score += 1
        
        # Check biomarker-disease linking
        key_drivers = linker_findings.get('key_drivers', [])
        if len(key_drivers) >= 2:
            score += 1
        if len(key_drivers) >= 4:
            score += 1
        
        # Map score to categorical rating
        if score >= 4:
            return "STRONG"
        elif score >= 2:
            return "MODERATE"
        else:
            return "WEAK"
    
    def _identify_limitations(
        self,
        biomarkers: Dict[str, float],
        biomarker_analysis: dict,
        probabilities: Dict[str, float]
    ) -> List[str]:
        """Identify limitations and uncertainties"""
        limitations = []
        
        # Check for missing biomarkers
        expected_biomarkers = 24
        if len(biomarkers) < expected_biomarkers:
            missing = expected_biomarkers - len(biomarkers)
            limitations.append(f"Missing data: {missing} biomarker(s) not provided")
        
        # Check for close alternative predictions
        sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_probs) >= 2:
            top1, prob1 = sorted_probs[0]
            top2, prob2 = sorted_probs[1]
            if prob2 > 0.15:  # Alternative is significant
                limitations.append(
                    f"Differential diagnosis: {top2} also possible ({prob2:.1%} probability)"
                )
        
        # Check for normal biomarkers despite prediction
        flags = biomarker_analysis.get('biomarker_flags', [])
        relevant = biomarker_analysis.get('relevant_biomarkers', [])
        normal_relevant = [
            f for f in flags
            if f.get('name') in relevant and f.get('status') == 'NORMAL'
        ]
        if len(normal_relevant) >= 2:
            limitations.append(
                f"Some disease-relevant biomarkers are within normal range"
            )
        
        # Check for safety alerts (indicates complexity)
        alerts = biomarker_analysis.get('safety_alerts', [])
        if len(alerts) >= 2:
            limitations.append(
                "Multiple critical values detected; professional evaluation essential"
            )
        
        return limitations
    
    def _calculate_reliability(
        self,
        ml_confidence: float,
        evidence_strength: str,
        limitation_count: int
    ) -> str:
        """Calculate overall prediction reliability"""
        
        score = 0
        
        # ML confidence contribution
        if ml_confidence >= 0.8:
            score += 3
        elif ml_confidence >= 0.6:
            score += 2
        elif ml_confidence >= 0.4:
            score += 1
        
        # Evidence strength contribution
        if evidence_strength == "STRONG":
            score += 3
        elif evidence_strength == "MODERATE":
            score += 2
        else:
            score += 1
        
        # Limitation penalty
        score -= min(limitation_count, 3)
        
        # Map to categorical
        if score >= 5:
            return "HIGH"
        elif score >= 3:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_assessment(
        self,
        disease: str,
        ml_confidence: float,
        reliability: str,
        evidence_strength: str,
        limitations: List[str]
    ) -> str:
        """Generate human-readable assessment summary"""
        
        prompt = f"""As a medical AI assessment system, provide a brief confidence statement about this prediction:

Disease Predicted: {disease}
ML Model Confidence: {ml_confidence:.1%}
Overall Reliability: {reliability}
Evidence Strength: {evidence_strength}
Limitations: {len(limitations)} identified

Write a 2-3 sentence assessment that:
1. States the overall reliability
2. Mentions key strengths or weaknesses
3. Emphasizes the need for professional medical consultation

Be honest about uncertainty. Patient safety is paramount."""

        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Warning: Assessment generation failed: {e}")
            return f"The {disease} prediction has {reliability.lower()} reliability based on available data. Professional medical evaluation is strongly recommended for accurate diagnosis."
    
    def _get_recommendation(self, reliability: str) -> str:
        """Get action recommendation based on reliability"""
        if reliability == "HIGH":
            return "High confidence prediction. Schedule medical consultation to confirm diagnosis and discuss treatment options."
        elif reliability == "MODERATE":
            return "Moderate confidence prediction. Medical consultation recommended for professional evaluation and additional testing if needed."
        else:
            return "Low confidence prediction. Professional medical assessment essential. Additional tests may be required for accurate diagnosis."
    
    def _get_alternatives(self, probabilities: Dict[str, float]) -> List[Dict[str, any]]:
        """Get alternative diagnoses to consider"""
        sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        
        alternatives = []
        for disease, prob in sorted_probs[1:4]:  # Top 3 alternatives
            if prob > 0.05:  # Only significant alternatives
                alternatives.append({
                    "disease": disease,
                    "probability": prob,
                    "note": "Consider discussing with healthcare provider"
                })
        
        return alternatives


# Create agent instance for import
confidence_assessor_agent = ConfidenceAssessorAgent()
