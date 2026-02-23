"""
MediGuard AI RAG-Helper
Clinical Guidelines Agent - Retrieves evidence-based recommendations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List
from src.state import GuildState, AgentOutput
from src.llm_config import llm_config
from langchain_core.prompts import ChatPromptTemplate


class ClinicalGuidelinesAgent:
    """Agent that retrieves clinical guidelines and recommendations using RAG"""
    
    def __init__(self, retriever):
        """
        Initialize with a retriever for clinical guidelines.
        
        Args:
            retriever: Vector store retriever for guidelines documents
        """
        self.retriever = retriever
        self.llm = llm_config.explainer
    
    def recommend(self, state: GuildState) -> GuildState:
        """
        Retrieve clinical guidelines and generate recommendations.
        
        Args:
            state: Current guild state
        
        Returns:
            Updated state with clinical recommendations
        """
        print("\n" + "="*70)
        print("EXECUTING: Clinical Guidelines Agent (RAG)")
        print("="*70)
        
        model_prediction = state['model_prediction']
        disease = model_prediction['disease']
        confidence = model_prediction['confidence']
        
        # Get biomarker analysis
        biomarker_analysis = state.get('biomarker_analysis') or {}
        safety_alerts = biomarker_analysis.get('safety_alerts', [])
        
        # Retrieve guidelines
        print(f"\nRetrieving clinical guidelines for {disease}...")
        
        query = f"""What are the clinical practice guidelines for managing {disease}? 
        Include lifestyle modifications, monitoring recommendations, and when to seek medical care."""
        
        docs = self.retriever.invoke(query)
        
        print(f"Retrieved {len(docs)} guideline documents")
        
        # Generate recommendations
        if state['sop'].require_pdf_citations and not docs:
            recommendations = {
                "immediate_actions": [
                    "Insufficient evidence available in the knowledge base. Please consult a healthcare provider."
                ],
                "lifestyle_changes": [],
                "monitoring": [],
                "citations": []
            }
        else:
            recommendations = self._generate_recommendations(
                disease,
                docs,
                safety_alerts,
                confidence,
                state
            )
        
        # Create agent output
        output = AgentOutput(
            agent_name="Clinical Guidelines",
            findings={
                "disease": disease,
                "immediate_actions": recommendations['immediate_actions'],
                "lifestyle_changes": recommendations['lifestyle_changes'],
                "monitoring": recommendations['monitoring'],
                "guideline_citations": recommendations['citations'],
                "safety_priority": len(safety_alerts) > 0,
                "citations_missing": state['sop'].require_pdf_citations and not docs
            }
        )
        
        # Update state
        print("\nRecommendations generated")
        print(f"  - Immediate actions: {len(recommendations['immediate_actions'])}")
        print(f"  - Lifestyle changes: {len(recommendations['lifestyle_changes'])}")
        print(f"  - Monitoring recommendations: {len(recommendations['monitoring'])}")
        
        return {'agent_outputs': [output]}
    
    def _generate_recommendations(
        self,
        disease: str,
        docs: list,
        safety_alerts: list,
        confidence: float,
        state: GuildState
    ) -> dict:
        """Generate structured recommendations using LLM and guidelines"""
        
        # Format retrieved guidelines
        guidelines_context = "\n\n---\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')}\n\n{doc.page_content}"
            for doc in docs
        ])
        
        # Build safety context
        safety_context = ""
        if safety_alerts:
            safety_context = "\n**CRITICAL SAFETY ALERTS:**\n"
            for alert in safety_alerts[:3]:
                safety_context += f"- {alert.get('biomarker', 'Unknown')}: {alert.get('message', '')}\n"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a clinical decision support system providing evidence-based recommendations.
            Based on clinical practice guidelines, provide actionable recommendations for patient self-assessment.
            
            Structure your response with these sections:
            1. IMMEDIATE_ACTIONS: Urgent steps (especially if safety alerts present)
            2. LIFESTYLE_CHANGES: Diet, exercise, and behavioral modifications
            3. MONITORING: What to track and how often
            
            Make recommendations specific, actionable, and guideline-aligned. 
            Always emphasize consulting healthcare professionals for diagnosis and treatment."""),
            ("human", """Disease: {disease}
            Prediction Confidence: {confidence:.1%}
            {safety_context}
            
            Clinical Guidelines Context:
            {guidelines}
            
            Please provide structured recommendations for patient self-assessment.""")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "disease": disease,
                "confidence": confidence,
                "safety_context": safety_context,
                "guidelines": guidelines_context
            })
            
            recommendations = self._parse_recommendations(response.content)
            
        except Exception as e:
            print(f"Warning: LLM recommendation generation failed: {e}")
            recommendations = self._get_default_recommendations(disease, safety_alerts)
        
        # Add citations
        recommendations['citations'] = self._extract_citations(docs)
        
        return recommendations
    
    def _parse_recommendations(self, content: str) -> dict:
        """Parse LLM response into structured recommendations"""
        recommendations = {
            "immediate_actions": [],
            "lifestyle_changes": [],
            "monitoring": []
        }
        
        current_section = None
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            line_upper = line_stripped.upper()
            
            # Detect section headers
            if 'IMMEDIATE' in line_upper or 'URGENT' in line_upper:
                current_section = 'immediate_actions'
            elif 'LIFESTYLE' in line_upper or 'CHANGES' in line_upper or 'DIET' in line_upper:
                current_section = 'lifestyle_changes'
            elif 'MONITORING' in line_upper or 'TRACK' in line_upper:
                current_section = 'monitoring'
            # Add bullet points or numbered items
            elif current_section and line_stripped:
                # Remove bullet points and numbers
                cleaned = line_stripped.lstrip('•-*0123456789. ')
                if cleaned and len(cleaned) > 10:  # Minimum length filter
                    recommendations[current_section].append(cleaned)
        
        # If parsing failed, create default structure
        if not any(recommendations.values()):
            sentences = content.split('.')
            recommendations['immediate_actions'] = [s.strip() for s in sentences[:2] if s.strip()]
            recommendations['lifestyle_changes'] = [s.strip() for s in sentences[2:4] if s.strip()]
            recommendations['monitoring'] = [s.strip() for s in sentences[4:6] if s.strip()]
        
        return recommendations
    
    def _get_default_recommendations(self, disease: str, safety_alerts: list) -> dict:
        """Provide default recommendations if LLM fails"""
        recommendations = {
            "immediate_actions": [],
            "lifestyle_changes": [],
            "monitoring": []
        }
        
        # Add safety-based immediate actions
        if safety_alerts:
            recommendations['immediate_actions'].append(
                "Consult healthcare provider immediately regarding critical biomarker values"
            )
            recommendations['immediate_actions'].append(
                "Bring this report and recent lab results to your appointment"
            )
        else:
            recommendations['immediate_actions'].append(
                f"Schedule appointment with healthcare provider to discuss {disease} findings"
            )
        
        # Generic lifestyle changes
        recommendations['lifestyle_changes'].extend([
            "Follow a balanced, nutrient-rich diet as recommended by healthcare provider",
            "Maintain regular physical activity appropriate for your health status",
            "Track symptoms and biomarker trends over time"
        ])
        
        # Generic monitoring
        recommendations['monitoring'].extend([
            f"Regular monitoring of {disease}-related biomarkers as advised by physician",
            "Keep a health journal tracking symptoms, diet, and activities",
            "Schedule follow-up appointments as recommended"
        ])
        
        return recommendations
    
    def _extract_citations(self, docs: list) -> List[str]:
        """Extract citations from retrieved guideline documents"""
        citations = []
        
        for doc in docs:
            source = doc.metadata.get('source', 'Unknown')
            
            # Clean up source path
            if '\\' in source or '/' in source:
                source = Path(source).name
            
            citations.append(source)
        
        return list(set(citations))  # Remove duplicates


def create_clinical_guidelines_agent(retriever):
    """Factory function to create agent with retriever"""
    return ClinicalGuidelinesAgent(retriever)
