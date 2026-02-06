"""
MediGuard AI RAG-Helper
Biomarker-Disease Linker Agent - Connects biomarker values to predicted disease
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Dict, List
from src.state import GuildState, AgentOutput, KeyDriver
from src.llm_config import llm_config
from langchain_core.prompts import ChatPromptTemplate


class BiomarkerDiseaseLinkerAgent:
    """Agent that links specific biomarker values to the predicted disease"""
    
    def __init__(self, retriever):
        """
        Initialize with a retriever for biomarker-disease connections.
        
        Args:
            retriever: Vector store retriever for biomarker evidence
        """
        self.retriever = retriever
        self.llm = llm_config.explainer
    
    def link(self, state: GuildState) -> GuildState:
        """
        Link biomarkers to disease prediction.
        
        Args:
            state: Current guild state
        
        Returns:
            Updated state with biomarker-disease links
        """
        print("\n" + "="*70)
        print("EXECUTING: Biomarker-Disease Linker Agent (RAG)")
        print("="*70)
        
        model_prediction = state['model_prediction']
        disease = model_prediction['disease']
        biomarkers = state['patient_biomarkers']
        
        # Get biomarker analysis from previous agent
        biomarker_analysis = self._get_biomarker_analysis(state)
        
        # Identify key drivers
        print(f"\nIdentifying key drivers for {disease}...")
        key_drivers = self._identify_key_drivers(
            disease, 
            biomarkers, 
            biomarker_analysis,
            state
        )
        
        print(f"✓ Identified {len(key_drivers)} key biomarker drivers")
        
        # Create agent output
        output = AgentOutput(
            agent_name="Biomarker-Disease Linker",
            findings={
                "disease": disease,
                "key_drivers": [kd.model_dump() for kd in key_drivers],
                "total_drivers": len(key_drivers),
                "feature_importance_calculated": True
            }
        )
        
        # Update state
        print(f"\n✓ Biomarker-disease linking complete")
        
        return {'agent_outputs': [output]}
    
    def _get_biomarker_analysis(self, state: GuildState) -> dict:
        """Extract biomarker analysis from previous agent output"""
        for output in state.get('agent_outputs', []):
            if output.agent_name == "Biomarker Analyzer":
                return output.findings
        return {}
    
    def _identify_key_drivers(
        self,
        disease: str,
        biomarkers: Dict[str, float],
        analysis: dict,
        state: GuildState
    ) -> List[KeyDriver]:
        """Identify which biomarkers are driving the disease prediction"""
        
        # Get out-of-range biomarkers from analysis
        flags = analysis.get('biomarker_flags', [])
        abnormal_biomarkers = [
            f for f in flags 
            if f['status'] != 'NORMAL'
        ]
        
        # Get disease-relevant biomarkers
        relevant = analysis.get('relevant_biomarkers', [])
        
        # Focus on biomarkers that are both abnormal AND disease-relevant
        key_biomarkers = [
            f for f in abnormal_biomarkers
            if f['name'] in relevant
        ]
        
        # If no key biomarkers found, use top abnormal ones
        if not key_biomarkers:
            key_biomarkers = abnormal_biomarkers[:5]
        
        print(f"  Analyzing {len(key_biomarkers)} key biomarkers...")
        
        # Generate key drivers with evidence
        key_drivers = []
        for biomarker_flag in key_biomarkers[:5]:  # Top 5
            driver = self._create_key_driver(
                biomarker_flag,
                disease,
                state
            )
            key_drivers.append(driver)
        
        return key_drivers
    
    def _create_key_driver(
        self,
        biomarker_flag: dict,
        disease: str,
        state: GuildState
    ) -> KeyDriver:
        """Create a KeyDriver object with evidence from RAG"""
        
        name = biomarker_flag['name']
        value = biomarker_flag['value']
        unit = biomarker_flag['unit']
        status = biomarker_flag['status']
        
        # Retrieve evidence linking this biomarker to the disease
        query = f"How does {name} relate to {disease}? What does {status} {name} indicate?"
        
        try:
            docs = self.retriever.invoke(query)
            evidence_text = self._extract_evidence(docs, name, disease)
            contribution = self._estimate_contribution(biomarker_flag, len(docs))
        except Exception as e:
            print(f"  Warning: Evidence retrieval failed for {name}: {e}")
            evidence_text = f"{status} {name} may be related to {disease}."
            contribution = "Unknown"
        
        # Generate explanation using LLM
        explanation = self._generate_explanation(
            name, value, unit, status, disease, evidence_text
        )
        
        return KeyDriver(
            biomarker=name,
            value=value,
            contribution=contribution,
            explanation=explanation,
            evidence=evidence_text[:500]  # Truncate long evidence
        )
    
    def _extract_evidence(self, docs: list, biomarker: str, disease: str) -> str:
        """Extract relevant evidence from retrieved documents"""
        if not docs:
            return f"Limited evidence available for {biomarker} in {disease}."
        
        # Combine relevant passages
        evidence = []
        for doc in docs[:2]:  # Top 2 docs
            content = doc.page_content
            # Extract sentences mentioning the biomarker
            sentences = content.split('.')
            relevant_sentences = [
                s.strip() for s in sentences 
                if biomarker.lower() in s.lower() or disease.lower() in s.lower()
            ]
            evidence.extend(relevant_sentences[:2])
        
        return ". ".join(evidence[:3]) + "." if evidence else content[:300]
    
    def _estimate_contribution(self, biomarker_flag: dict, doc_count: int) -> str:
        """Estimate the contribution percentage (simplified)"""
        status = biomarker_flag['status']
        
        # Simple heuristic based on severity
        if 'CRITICAL' in status:
            base = 40
        elif status in ['HIGH', 'LOW']:
            base = 25
        else:
            base = 10
        
        # Adjust based on evidence strength
        evidence_boost = min(doc_count * 2, 15)
        
        total = min(base + evidence_boost, 60)
        return f"{total}%"
    
    def _generate_explanation(
        self,
        biomarker: str,
        value: float,
        unit: str,
        status: str,
        disease: str,
        evidence: str
    ) -> str:
        """Generate patient-friendly explanation"""
        
        prompt = f"""Explain in 1-2 sentences how this biomarker result relates to {disease}:

Biomarker: {biomarker}
Value: {value} {unit}
Status: {status}

Medical Evidence: {evidence}

Write in patient-friendly language, explaining what this means for the diagnosis."""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            return f"{biomarker} at {value} {unit} is {status}, which may be associated with {disease}."


def create_biomarker_linker_agent(retriever):
    """Factory function to create agent with retriever"""
    return BiomarkerDiseaseLinkerAgent(retriever)
