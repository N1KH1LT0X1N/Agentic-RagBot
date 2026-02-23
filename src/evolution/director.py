"""
MediGuard AI RAG-Helper - Evolution Engine
Outer Loop Director for SOP Evolution
"""

import json
from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from src.config import ExplanationSOP
from src.evaluation.evaluators import EvaluationResult


class SOPGenePool:
    """Manages version control for evolving SOPs"""
    
    def __init__(self):
        self.pool: List[Dict[str, Any]] = []
        self.gene_pool: List[Dict[str, Any]] = []  # Alias for compatibility
        self.version_counter = 0
    
    def add(
        self,
        sop: ExplanationSOP,
        evaluation: EvaluationResult,
        parent_version: Optional[int] = None,
        description: str = ""
    ):
        """Add a new SOP to the gene pool"""
        self.version_counter += 1
        entry = {
            "version": self.version_counter,
            "sop": sop,
            "evaluation": evaluation,
            "parent": parent_version,
            "description": description
        }
        self.pool.append(entry)
        self.gene_pool = self.pool  # Keep in sync
        print(f"✓ Added SOP v{self.version_counter} to gene pool: {description}")
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent SOP"""
        return self.pool[-1] if self.pool else None
    
    def get_by_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Retrieve specific SOP version"""
        for entry in self.pool:
            if entry['version'] == version:
                return entry
        return None
    
    def get_best_by_metric(self, metric: str) -> Optional[Dict[str, Any]]:
        """Get SOP with highest score on specific metric"""
        if not self.pool:
            return None
        
        best = max(
            self.pool,
            key=lambda x: getattr(x['evaluation'], metric).score
        )
        return best
    
    def summary(self):
        """Print summary of all SOPs in pool"""
        print("\n" + "=" * 80)
        print("SOP GENE POOL SUMMARY")
        print("=" * 80)
        
        for entry in self.pool:
            v = entry['version']
            p = entry['parent']
            desc = entry['description']
            e = entry['evaluation']
            
            parent_str = "(Baseline)" if p is None else f"(Child of v{p})"
            
            print(f"\nSOP v{v} {parent_str}: {desc}")
            print(f"  Clinical Accuracy:     {e.clinical_accuracy.score:.2f}")
            print(f"  Evidence Grounding:    {e.evidence_grounding.score:.2f}")
            print(f"  Actionability:         {e.actionability.score:.2f}")
            print(f"  Clarity:               {e.clarity.score:.2f}")
            print(f"  Safety & Completeness: {e.safety_completeness.score:.2f}")
        
        print("\n" + "=" * 80)


class Diagnosis(BaseModel):
    """Structured diagnosis from Performance Diagnostician"""
    primary_weakness: Literal[
        'clinical_accuracy',
        'evidence_grounding',
        'actionability',
        'clarity',
        'safety_completeness'
    ]
    root_cause_analysis: str = Field(
        description="Detailed analysis of why weakness occurred"
    )
    recommendation: str = Field(
        description="High-level recommendation to fix the problem"
    )


class SOPMutation(BaseModel):
    """Single mutated SOP with description"""
    description: str = Field(description="Brief description of mutation strategy")
    # SOP fields from ExplanationSOP
    biomarker_analyzer_threshold: float = 0.15
    disease_explainer_k: int = 5
    linker_retrieval_k: int = 3
    guideline_retrieval_k: int = 3
    explainer_detail_level: Literal["concise", "detailed", "comprehensive"] = "detailed"
    use_guideline_agent: bool = True
    include_alternative_diagnoses: bool = True
    require_pdf_citations: bool = True
    use_confidence_assessor: bool = True
    critical_value_alert_mode: Literal["strict", "moderate", "permissive"] = "strict"


class EvolvedSOPs(BaseModel):
    """Container for mutated SOPs from Architect"""
    mutations: List[SOPMutation]


def performance_diagnostician(evaluation: EvaluationResult) -> Diagnosis:
    """
    Analyzes 5D scores to identify primary weakness.
    Uses programmatic analysis for reliability and speed.
    """
    print("\n" + "=" * 70)
    print("EXECUTING: Performance Diagnostician")
    print("=" * 70)
    
    # Find lowest score programmatically (no LLM needed)
    scores = {
        'clinical_accuracy': evaluation.clinical_accuracy.score,
        'evidence_grounding': evaluation.evidence_grounding.score,
        'actionability': evaluation.actionability.score,
        'clarity': evaluation.clarity.score,
        'safety_completeness': evaluation.safety_completeness.score
    }
    
    reasonings = {
        'clinical_accuracy': evaluation.clinical_accuracy.reasoning,
        'evidence_grounding': evaluation.evidence_grounding.reasoning,
        'actionability': evaluation.actionability.reasoning,
        'clarity': evaluation.clarity.reasoning,
        'safety_completeness': evaluation.safety_completeness.reasoning
    }
    
    primary_weakness = min(scores, key=scores.get)
    weakness_score = scores[primary_weakness]
    weakness_reasoning = reasonings[primary_weakness]
    
    # Generate detailed root cause analysis
    root_cause_map = {
        'clinical_accuracy': f"Clinical accuracy score ({weakness_score:.2f}) indicates potential issues with medical interpretations. {weakness_reasoning[:200]}",
        'evidence_grounding': f"Evidence grounding score ({weakness_score:.2f}) suggests insufficient citations. {weakness_reasoning[:200]}",
        'actionability': f"Actionability score ({weakness_score:.2f}) indicates recommendations lack specificity. {weakness_reasoning[:200]}",
        'clarity': f"Clarity score ({weakness_score:.2f}) suggests readability issues. {weakness_reasoning[:200]}",
        'safety_completeness': f"Safety score ({weakness_score:.2f}) indicates missing risk discussions. {weakness_reasoning[:200]}"
    }
    
    recommendation_map = {
        'clinical_accuracy': "Increase RAG depth to access more authoritative medical sources.",
        'evidence_grounding': "Enforce strict citation requirements and increase RAG depth.",
        'actionability': "Make recommendations more specific with concrete action items.",
        'clarity': "Simplify language and reduce technical jargon for better readability.",
        'safety_completeness': "Add explicit safety warnings and ensure complete risk coverage."
    }
    
    diagnosis = Diagnosis(
        primary_weakness=primary_weakness,
        root_cause_analysis=root_cause_map[primary_weakness],
        recommendation=recommendation_map[primary_weakness]
    )
    
    print(f"\n✓ Diagnosis complete")
    print(f"  Primary weakness: {diagnosis.primary_weakness} ({weakness_score:.3f})")
    print(f"  Recommendation: {diagnosis.recommendation}")
    
    return diagnosis


def sop_architect(
    diagnosis: Diagnosis,
    current_sop: ExplanationSOP
) -> EvolvedSOPs:
    """
    Generates targeted SOP mutations to address diagnosed weakness.
    Uses programmatic generation for reliability.
    """
    print("\n" + "=" * 70)
    print("EXECUTING: SOP Architect")
    print("=" * 70)
    print(f"Target weakness: {diagnosis.primary_weakness}")
    
    weakness = diagnosis.primary_weakness
    
    # Generate mutations based on weakness type
    if weakness == 'clarity':
        mut1 = SOPMutation(
            disease_explainer_k=max(3, current_sop.disease_explainer_k - 1),
            linker_retrieval_k=max(2, current_sop.linker_retrieval_k - 1),
            guideline_retrieval_k=max(2, current_sop.guideline_retrieval_k - 1),
            explainer_detail_level='concise',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=current_sop.use_guideline_agent,
            include_alternative_diagnoses=False,
            require_pdf_citations=current_sop.require_pdf_citations,
            use_confidence_assessor=current_sop.use_confidence_assessor,
            critical_value_alert_mode=current_sop.critical_value_alert_mode,
            description="Reduce retrieval depth and use concise style for clarity"
        )
        mut2 = SOPMutation(
            disease_explainer_k=current_sop.disease_explainer_k,
            linker_retrieval_k=current_sop.linker_retrieval_k,
            guideline_retrieval_k=current_sop.guideline_retrieval_k,
            explainer_detail_level='detailed',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=current_sop.use_guideline_agent,
            include_alternative_diagnoses=True,
            require_pdf_citations=False,
            use_confidence_assessor=current_sop.use_confidence_assessor,
            critical_value_alert_mode=current_sop.critical_value_alert_mode,
            description="Balanced detail with fewer citations for readability"
        )
    
    elif weakness == 'evidence_grounding':
        mut1 = SOPMutation(
            disease_explainer_k=min(10, current_sop.disease_explainer_k + 2),
            linker_retrieval_k=min(5, current_sop.linker_retrieval_k + 1),
            guideline_retrieval_k=min(5, current_sop.guideline_retrieval_k + 1),
            explainer_detail_level='comprehensive',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=True,
            include_alternative_diagnoses=current_sop.include_alternative_diagnoses,
            require_pdf_citations=True,
            use_confidence_assessor=current_sop.use_confidence_assessor,
            critical_value_alert_mode=current_sop.critical_value_alert_mode,
            description="Maximum RAG depth with strict citation requirements"
        )
        mut2 = SOPMutation(
            disease_explainer_k=min(10, current_sop.disease_explainer_k + 1),
            linker_retrieval_k=current_sop.linker_retrieval_k,
            guideline_retrieval_k=current_sop.guideline_retrieval_k,
            explainer_detail_level='detailed',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=True,
            include_alternative_diagnoses=current_sop.include_alternative_diagnoses,
            require_pdf_citations=True,
            use_confidence_assessor=current_sop.use_confidence_assessor,
            critical_value_alert_mode=current_sop.critical_value_alert_mode,
            description="Moderate RAG increase with citation enforcement"
        )
    
    elif weakness == 'actionability':
        mut1 = SOPMutation(
            disease_explainer_k=current_sop.disease_explainer_k,
            linker_retrieval_k=current_sop.linker_retrieval_k,
            guideline_retrieval_k=min(5, current_sop.guideline_retrieval_k + 2),
            explainer_detail_level='comprehensive',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=True,
            include_alternative_diagnoses=current_sop.include_alternative_diagnoses,
            require_pdf_citations=True,
            use_confidence_assessor=current_sop.use_confidence_assessor,
            critical_value_alert_mode='strict',
            description="Increase guideline retrieval for actionable recommendations"
        )
        mut2 = SOPMutation(
            disease_explainer_k=min(10, current_sop.disease_explainer_k + 1),
            linker_retrieval_k=min(5, current_sop.linker_retrieval_k + 1),
            guideline_retrieval_k=min(5, current_sop.guideline_retrieval_k + 1),
            explainer_detail_level='detailed',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=True,
            include_alternative_diagnoses=True,
            require_pdf_citations=True,
            use_confidence_assessor=True,
            critical_value_alert_mode='strict',
            description="Comprehensive approach with all agents enabled"
        )
    
    elif weakness == 'clinical_accuracy':
        mut1 = SOPMutation(
            disease_explainer_k=10,
            linker_retrieval_k=5,
            guideline_retrieval_k=5,
            explainer_detail_level='comprehensive',
            biomarker_analyzer_threshold=max(0.10, current_sop.biomarker_analyzer_threshold - 0.05),
            use_guideline_agent=True,
            include_alternative_diagnoses=True,
            require_pdf_citations=True,
            use_confidence_assessor=True,
            critical_value_alert_mode='strict',
            description="Maximum RAG depth with strict thresholds for accuracy"
        )
        mut2 = SOPMutation(
            disease_explainer_k=min(10, current_sop.disease_explainer_k + 2),
            linker_retrieval_k=min(5, current_sop.linker_retrieval_k + 1),
            guideline_retrieval_k=min(5, current_sop.guideline_retrieval_k + 1),
            explainer_detail_level='comprehensive',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=True,
            include_alternative_diagnoses=True,
            require_pdf_citations=True,
            use_confidence_assessor=True,
            critical_value_alert_mode='strict',
            description="High RAG depth with comprehensive detail"
        )
    
    else:  # safety_completeness
        mut1 = SOPMutation(
            disease_explainer_k=min(10, current_sop.disease_explainer_k + 1),
            linker_retrieval_k=current_sop.linker_retrieval_k,
            guideline_retrieval_k=min(5, current_sop.guideline_retrieval_k + 2),
            explainer_detail_level='comprehensive',
            biomarker_analyzer_threshold=max(0.10, current_sop.biomarker_analyzer_threshold - 0.03),
            use_guideline_agent=True,
            include_alternative_diagnoses=True,
            require_pdf_citations=True,
            use_confidence_assessor=True,
            critical_value_alert_mode='strict',
            description="Strict safety mode with enhanced guidelines"
        )
        mut2 = SOPMutation(
            disease_explainer_k=min(10, current_sop.disease_explainer_k + 2),
            linker_retrieval_k=min(5, current_sop.linker_retrieval_k + 1),
            guideline_retrieval_k=min(5, current_sop.guideline_retrieval_k + 1),
            explainer_detail_level='comprehensive',
            biomarker_analyzer_threshold=current_sop.biomarker_analyzer_threshold,
            use_guideline_agent=True,
            include_alternative_diagnoses=True,
            require_pdf_citations=True,
            use_confidence_assessor=True,
            critical_value_alert_mode='strict',
            description="Maximum coverage with all safety features"
        )
    
    evolved = EvolvedSOPs(mutations=[mut1, mut2])
    
    print(f"\n✓ Generated {len(evolved.mutations)} mutations")
    for i, mut in enumerate(evolved.mutations, 1):
        print(f"  {i}. {mut.description}")
        print(f"     Disease K: {mut.disease_explainer_k}, Detail: {mut.explainer_detail_level}")
    
    return evolved


def run_evolution_cycle(
    gene_pool: SOPGenePool,
    patient_input: Any,
    workflow_graph: Any,
    evaluation_func: Callable
) -> List[Dict[str, Any]]:
    """
    Executes one complete evolution cycle:
    1. Diagnose current best SOP
    2. Generate mutations
    3. Test each mutation
    4. Add to gene pool
    
    Returns: List of new entries added to pool
    """
    print("\n" + "=" * 80)
    print("STARTING EVOLUTION CYCLE")
    print("=" * 80)
    
    # Get current best (for simplicity, use latest)
    current_best = gene_pool.get_latest()
    if not current_best:
        raise ValueError("Gene pool is empty. Add baseline SOP first.")
    
    parent_sop = current_best['sop']
    parent_eval = current_best['evaluation']
    parent_version = current_best['version']
    
    print(f"\nImproving upon SOP v{parent_version}")
    
    # Step 1: Diagnose
    diagnosis = performance_diagnostician(parent_eval)
    
    # Step 2: Generate mutations
    evolved_sops = sop_architect(diagnosis, parent_sop)
    
    # Step 3: Test each mutation
    new_entries = []
    for i, mutant_sop_model in enumerate(evolved_sops.mutations, 1):
        print(f"\n{'=' * 70}")
        print(f"TESTING MUTATION {i}/{len(evolved_sops.mutations)}: {mutant_sop_model.description}")
        print("=" * 70)
        
        # Convert SOPMutation to ExplanationSOP
        mutant_sop_dict = mutant_sop_model.model_dump()
        description = mutant_sop_dict.pop('description')
        mutant_sop = ExplanationSOP(**mutant_sop_dict)
        
        # Run workflow with mutated SOP
        from src.state import PatientInput
        graph_input = {
            "patient_biomarkers": patient_input.biomarkers,
            "model_prediction": patient_input.model_prediction,
            "patient_context": patient_input.patient_context,
            "sop": mutant_sop
        }
        
        try:
            final_state = workflow_graph.invoke(graph_input)
            
            # Evaluate output
            evaluation = evaluation_func(
                final_response=final_state['final_response'],
                agent_outputs=final_state['agent_outputs'],
                biomarkers=patient_input.biomarkers
            )
            
            # Add to gene pool
            gene_pool.add(
                sop=mutant_sop,
                evaluation=evaluation,
                parent_version=parent_version,
                description=description
            )
            
            new_entries.append({
                "sop": mutant_sop,
                "evaluation": evaluation,
                "description": description
            })
        except Exception as e:
            print(f"❌ Mutation {i} failed: {e}")
            continue
    
    print("\n" + "=" * 80)
    print("EVOLUTION CYCLE COMPLETE")
    print("=" * 80)
    
    return new_entries
