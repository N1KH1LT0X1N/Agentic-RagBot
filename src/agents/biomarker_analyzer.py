"""
MediGuard AI RAG-Helper
Biomarker Analyzer Agent - Validates biomarker values and flags anomalies
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Dict, List
from src.state import GuildState, AgentOutput, BiomarkerFlag
from src.biomarker_validator import BiomarkerValidator
from src.llm_config import llm_config


class BiomarkerAnalyzerAgent:
    """Agent that validates biomarker values and generates comprehensive analysis"""
    
    def __init__(self):
        self.validator = BiomarkerValidator()
        self.llm = llm_config.analyzer
    
    def analyze(self, state: GuildState) -> GuildState:
        """
        Main agent function to analyze biomarkers.
        
        Args:
            state: Current guild state with patient input
        
        Returns:
            Updated state with biomarker analysis
        """
        print("\n" + "="*70)
        print("EXECUTING: Biomarker Analyzer Agent")
        print("="*70)
        
        biomarkers = state['patient_biomarkers']
        patient_context = state.get('patient_context', {})
        gender = patient_context.get('gender', 'male')
        predicted_disease = state['model_prediction']['disease']
        
        # Validate all biomarkers
        print(f"\nValidating {len(biomarkers)} biomarkers...")
        flags, alerts = self.validator.validate_all(
            biomarkers=biomarkers,
            gender=gender,
            threshold_pct=state['sop'].biomarker_analyzer_threshold
        )
        
        # Get disease-relevant biomarkers
        relevant_biomarkers = self.validator.get_disease_relevant_biomarkers(predicted_disease)
        
        # Generate summary using LLM
        summary = self._generate_summary(biomarkers, flags, alerts, relevant_biomarkers, predicted_disease)
        
        # Create agent output
        output = AgentOutput(
            agent_name="Biomarker Analyzer",
            findings={
                "biomarker_flags": [flag.model_dump() for flag in flags],
                "safety_alerts": [alert.model_dump() for alert in alerts],
                "relevant_biomarkers": relevant_biomarkers,
                "summary": summary,
                "validation_complete": True
            }
        )
        
        # Update state
        print(f"\n✓ Analysis complete:")
        print(f"  - {len(flags)} biomarkers validated")
        print(f"  - {len([f for f in flags if f.status != 'NORMAL'])} out-of-range values")
        print(f"  - {len(alerts)} safety alerts generated")
        print(f"  - {len(relevant_biomarkers)} disease-relevant biomarkers identified")
        
        return {'agent_outputs': [output]}
    
    def _generate_summary(
        self,
        biomarkers: Dict[str, float],
        flags: List[BiomarkerFlag],
        alerts: List,
        relevant_biomarkers: List[str],
        disease: str
    ) -> str:
        """Generate a concise summary of biomarker findings"""
        
        # Count anomalies
        critical = [f for f in flags if 'CRITICAL' in f.status]
        high_low = [f for f in flags if f.status in ['HIGH', 'LOW']]
        
        prompt = f"""You are a medical data analyst. Provide a brief, clinical summary of these biomarker results.

**Patient Context:**
- Predicted Disease: {disease}
- Total Biomarkers Tested: {len(biomarkers)}
- Critical Values: {len(critical)}
- Out-of-Range Values: {len(high_low)}

**Key Findings:**
{self._format_key_findings(critical, high_low, relevant_biomarkers)}

Provide a 2-3 sentence summary highlighting:
1. Overall risk profile
2. Most concerning findings
3. Alignment with predicted disease

Keep it concise and clinical."""

        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Warning: LLM summary generation failed: {e}")
            return f"Biomarker analysis complete. {len(critical)} critical values, {len(high_low)} out-of-range values detected."
    
    def _format_key_findings(self, critical, high_low, relevant):
        """Format findings for LLM prompt"""
        findings = []
        
        if critical:
            findings.append("CRITICAL VALUES:")
            for f in critical[:3]:  # Top 3
                findings.append(f"  - {f.name}: {f.value} {f.unit} ({f.status})")
        
        if high_low:
            findings.append("\nOUT-OF-RANGE VALUES:")
            for f in high_low[:5]:  # Top 5
                findings.append(f"  - {f.name}: {f.value} {f.unit} ({f.status})")
        
        if relevant:
            findings.append(f"\nDISEASE-RELEVANT BIOMARKERS: {', '.join(relevant[:5])}")
        
        return "\n".join(findings) if findings else "All biomarkers within normal range."


# Create agent instance for import
biomarker_analyzer_agent = BiomarkerAnalyzerAgent()
