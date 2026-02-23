"""
MediGuard AI RAG-Helper
Disease Explainer Agent - Retrieves disease pathophysiology from medical PDFs
"""

from pathlib import Path
from src.state import GuildState, AgentOutput
from src.llm_config import llm_config
from langchain_core.prompts import ChatPromptTemplate


class DiseaseExplainerAgent:
    """Agent that retrieves and explains disease mechanisms using RAG"""
    
    def __init__(self, retriever):
        """
        Initialize with a retriever for medical PDFs.
        
        Args:
            retriever: Vector store retriever for disease documents
        """
        self.retriever = retriever
        self.llm = llm_config.explainer
    
    def explain(self, state: GuildState) -> GuildState:
        """
        Retrieve and explain disease pathophysiology.
        
        Args:
            state: Current guild state
        
        Returns:
            Updated state with disease explanation
        """
        print("\n" + "="*70)
        print("EXECUTING: Disease Explainer Agent (RAG)")
        print("="*70)
        
        model_prediction = state['model_prediction']
        disease = model_prediction['disease']
        confidence = model_prediction['confidence']
        
        # Configure retrieval based on SOP — create a copy to avoid mutating shared retriever
        retrieval_k = state['sop'].disease_explainer_k
        original_search_kwargs = dict(self.retriever.search_kwargs)
        self.retriever.search_kwargs = {**original_search_kwargs, 'k': retrieval_k}
        
        # Retrieve relevant documents
        print(f"\nRetrieving information about: {disease}")
        print(f"Retrieval k={state['sop'].disease_explainer_k}")
        
        query = f"""What is {disease}? Explain the pathophysiology, diagnostic criteria, 
        and clinical presentation. Focus on mechanisms relevant to blood biomarkers."""
        
        try:
            docs = self.retriever.invoke(query)
        finally:
            # Restore original search_kwargs to avoid side effects
            self.retriever.search_kwargs = original_search_kwargs

        print(f"Retrieved {len(docs)} relevant document chunks")

        if state['sop'].require_pdf_citations and not docs:
            explanation = {
                "pathophysiology": "Insufficient evidence available in the knowledge base to explain this condition.",
                "diagnostic_criteria": "Insufficient evidence available to list diagnostic criteria.",
                "clinical_presentation": "Insufficient evidence available to describe clinical presentation.",
                "summary": "Insufficient evidence available for a detailed explanation."
            }
            citations = []
            output = AgentOutput(
                agent_name="Disease Explainer",
                findings={
                    "disease": disease,
                    "pathophysiology": explanation['pathophysiology'],
                    "diagnostic_criteria": explanation['diagnostic_criteria'],
                    "clinical_presentation": explanation['clinical_presentation'],
                    "mechanism_summary": explanation['summary'],
                    "citations": citations,
                    "confidence": confidence,
                    "retrieval_quality": 0,
                    "citations_missing": True
                }
            )

            print("\nDisease explanation generated")
            print("  - Pathophysiology: insufficient evidence")
            print("  - Citations: 0 sources")
            return {'agent_outputs': [output]}
        
        # Generate explanation
        explanation = self._generate_explanation(disease, docs, confidence)
        
        # Extract citations
        citations = self._extract_citations(docs)
        
        # Create agent output
        output = AgentOutput(
            agent_name="Disease Explainer",
            findings={
                "disease": disease,
                "pathophysiology": explanation['pathophysiology'],
                "diagnostic_criteria": explanation['diagnostic_criteria'],
                "clinical_presentation": explanation['clinical_presentation'],
                "mechanism_summary": explanation['summary'],
                "citations": citations,
                "confidence": confidence,
                "retrieval_quality": len(docs),
                "citations_missing": False
            }
        )
        
        # Update state
        print("\nDisease explanation generated")
        print(f"  - Pathophysiology: {len(explanation['pathophysiology'])} chars")
        print(f"  - Citations: {len(citations)} sources")
        
        return {'agent_outputs': [output]}
    
    def _generate_explanation(self, disease: str, docs: list, confidence: float) -> dict:
        """Generate structured disease explanation using LLM and retrieved docs"""
        
        # Format retrieved context
        context = "\n\n---\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')}\n\n{doc.page_content}"
            for doc in docs
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical expert explaining diseases for patient self-assessment. 
            Based on the provided medical literature, explain the disease in clear, accessible language.
            Structure your response with these sections:
            1. PATHOPHYSIOLOGY: The underlying biological mechanisms
            2. DIAGNOSTIC_CRITERIA: How the disease is diagnosed
            3. CLINICAL_PRESENTATION: Common symptoms and signs
            4. SUMMARY: A 2-3 sentence overview
            
            Be accurate, cite-able, and patient-friendly. Focus on how the disease affects blood biomarkers."""),
            ("human", """Disease: {disease}
            Prediction Confidence: {confidence:.1%}
            
            Medical Literature Context:
            {context}
            
            Please provide a structured explanation.""")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "disease": disease,
                "confidence": confidence,
                "context": context
            })
            
            # Parse structured response
            content = response.content
            explanation = self._parse_explanation(content)
            
        except Exception as e:
            print(f"Warning: LLM explanation generation failed: {e}")
            explanation = {
                "pathophysiology": f"{disease} is a medical condition requiring professional diagnosis.",
                "diagnostic_criteria": "Consult medical guidelines for diagnostic criteria.",
                "clinical_presentation": "Clinical presentation varies by individual.",
                "summary": f"{disease} detected with {confidence:.1%} confidence. Consult healthcare provider."
            }
        
        return explanation
    
    def _parse_explanation(self, content: str) -> dict:
        """Parse LLM response into structured sections"""
        sections = {
            "pathophysiology": "",
            "diagnostic_criteria": "",
            "clinical_presentation": "",
            "summary": ""
        }
        
        # Simple parsing logic
        current_section = None
        lines = content.split('\n')
        
        for line in lines:
            line_upper = line.upper().strip()
            
            if 'PATHOPHYSIOLOGY' in line_upper:
                current_section = 'pathophysiology'
            elif 'DIAGNOSTIC' in line_upper:
                current_section = 'diagnostic_criteria'
            elif 'CLINICAL' in line_upper or 'PRESENTATION' in line_upper:
                current_section = 'clinical_presentation'
            elif 'SUMMARY' in line_upper:
                current_section = 'summary'
            elif current_section and line.strip():
                sections[current_section] += line + "\n"
        
        # If parsing failed, use full content as summary
        if not any(sections.values()):
            sections['summary'] = content[:500]
        
        return sections
    
    def _extract_citations(self, docs: list) -> list:
        """Extract citations from retrieved documents"""
        citations = []
        
        for doc in docs:
            source = doc.metadata.get('source', 'Unknown')
            page = doc.metadata.get('page', 'N/A')
            
            # Clean up source path
            if '\\' in source or '/' in source:
                source = Path(source).name
            
            citation = f"{source}"
            if page != 'N/A':
                citation += f" (Page {page})"
            
            citations.append(citation)
        
        return citations


def create_disease_explainer_agent(retriever):
    """Factory function to create agent with retriever"""
    return DiseaseExplainerAgent(retriever)
