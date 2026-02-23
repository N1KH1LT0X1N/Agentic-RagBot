"""
MediGuard AI RAG-Helper
Main LangGraph Workflow - Clinical Insight Guild Orchestration
"""

from langgraph.graph import StateGraph, END
from src.state import GuildState
from src.pdf_processor import get_all_retrievers


class ClinicalInsightGuild:
    """
    Main workflow orchestrator for MediGuard AI RAG-Helper.
    Coordinates all specialist agents in the Clinical Insight Guild.
    """
    
    def __init__(self):
        """Initialize the guild with all specialist agents"""
        print("\n" + "="*70)
        print("INITIALIZING: Clinical Insight Guild")
        print("="*70)
        
        # Load retrievers
        print("\nLoading RAG retrievers...")
        retrievers = get_all_retrievers()
        
        # Import and initialize all agents
        from src.agents.biomarker_analyzer import biomarker_analyzer_agent
        from src.agents.disease_explainer import create_disease_explainer_agent
        from src.agents.biomarker_linker import create_biomarker_linker_agent
        from src.agents.clinical_guidelines import create_clinical_guidelines_agent
        from src.agents.confidence_assessor import confidence_assessor_agent
        from src.agents.response_synthesizer import response_synthesizer_agent
        
        self.biomarker_analyzer = biomarker_analyzer_agent
        self.disease_explainer = create_disease_explainer_agent(retrievers['disease_explainer'])
        self.biomarker_linker = create_biomarker_linker_agent(retrievers['biomarker_linker'])
        self.clinical_guidelines = create_clinical_guidelines_agent(retrievers['clinical_guidelines'])
        self.confidence_assessor = confidence_assessor_agent
        self.response_synthesizer = response_synthesizer_agent
        
        print("All agents initialized successfully")
        
        # Build workflow graph
        self.workflow = self._build_workflow()
        print("Workflow graph compiled")
        print("="*70 + "\n")
    
    def _build_workflow(self):
        """
        Build the LangGraph workflow.
        
        Execution flow:
        1. Biomarker Analyzer (validates all biomarkers)
        2. Parallel execution:
           - Disease Explainer (RAG for pathophysiology)
           - Biomarker-Disease Linker (connects values to prediction)
           - Clinical Guidelines (RAG for recommendations)
        3. Confidence Assessor (evaluates reliability)
        4. Response Synthesizer (compiles final output)
        """
        
        # Create state graph
        workflow = StateGraph(GuildState)
        
        # Add all agent nodes
        workflow.add_node("biomarker_analyzer", self.biomarker_analyzer.analyze)
        workflow.add_node("disease_explainer", self.disease_explainer.explain)
        workflow.add_node("biomarker_linker", self.biomarker_linker.link)
        workflow.add_node("clinical_guidelines", self.clinical_guidelines.recommend)
        workflow.add_node("confidence_assessor", self.confidence_assessor.assess)
        workflow.add_node("response_synthesizer", self.response_synthesizer.synthesize)
        
        # Define execution flow
        # Start -> Biomarker Analyzer
        workflow.set_entry_point("biomarker_analyzer")
        
        # Biomarker Analyzer -> Parallel specialists
        workflow.add_edge("biomarker_analyzer", "disease_explainer")
        workflow.add_edge("biomarker_analyzer", "biomarker_linker")
        workflow.add_edge("biomarker_analyzer", "clinical_guidelines")
        
        # All parallel specialists -> Confidence Assessor
        workflow.add_edge("disease_explainer", "confidence_assessor")
        workflow.add_edge("biomarker_linker", "confidence_assessor")
        workflow.add_edge("clinical_guidelines", "confidence_assessor")
        
        # Confidence Assessor -> Response Synthesizer
        workflow.add_edge("confidence_assessor", "response_synthesizer")
        
        # Response Synthesizer -> END
        workflow.add_edge("response_synthesizer", END)
        
        # Compile workflow (returns CompiledGraph with invoke method)
        return workflow.compile()
    
    def run(self, patient_input) -> dict:
        """
        Execute the complete Clinical Insight Guild workflow.
        
        Args:
            patient_input: PatientInput object with biomarkers and ML prediction
        
        Returns:
            Complete structured response dictionary
        """
        from src.config import BASELINE_SOP
        from datetime import datetime
        
        print("\n" + "="*70)
        print("STARTING: Clinical Insight Guild Workflow")
        print("="*70)
        print(f"Patient: {patient_input.patient_context.get('patient_id', 'Unknown')}")
        print(f"Predicted Disease: {patient_input.model_prediction['disease']}")
        print(f"Model Confidence: {patient_input.model_prediction['confidence']:.1%}")
        print("="*70 + "\n")
        
        # Initialize state from PatientInput
        initial_state: GuildState = {
            'patient_biomarkers': patient_input.biomarkers,
            'model_prediction': patient_input.model_prediction,
            'patient_context': patient_input.patient_context,
            'plan': None,
            'sop': BASELINE_SOP,
            'agent_outputs': [],
            'biomarker_flags': [],
            'safety_alerts': [],
            'final_response': None,
            'biomarker_analysis': None,
            'processing_timestamp': datetime.now().isoformat(),
            'sop_version': "Baseline"
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print("\n" + "="*70)
        print("COMPLETED: Clinical Insight Guild Workflow")
        print("="*70)
        print(f"Total Agents Executed: {len(final_state.get('agent_outputs', []))}")
        print("Workflow execution successful")
        print("="*70 + "\n")
        
        # Return full state so callers can access agent_outputs,
        # biomarker_flags, safety_alerts, and final_response
        return dict(final_state)


def create_guild() -> ClinicalInsightGuild:
    """Factory function to create and initialize the Clinical Insight Guild"""
    return ClinicalInsightGuild()


if __name__ == "__main__":
    # Test workflow initialization
    print("Testing Clinical Insight Guild initialization...")
    guild = create_guild()
    print("\nGuild initialization successful!")
    print("Ready to process patient inputs.")
