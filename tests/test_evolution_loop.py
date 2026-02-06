"""
Test Evolution Loop (Phase 3)
Complete validation of self-improvement system
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow import create_guild
from src.pdf_processor import get_all_retrievers
from src.config import BASELINE_SOP
from src.state import PatientInput, GuildState
from src.evaluation.evaluators import run_full_evaluation
from src.evolution.director import SOPGenePool, run_evolution_cycle
from src.evolution.pareto import (
    identify_pareto_front,
    visualize_pareto_frontier,
    print_pareto_summary,
    analyze_improvements
)
from datetime import datetime
from typing import Dict, Any


def create_test_patient() -> PatientInput:
    """Create diabetes patient for testing"""
    biomarkers = {
        "Glucose": 185.0,
        "HbA1c": 8.2,
        "Cholesterol": 235.0,
        "Triglycerides": 210.0,
        "HDL": 38.0,
        "LDL": 155.0,
        "VLDL": 42.0,
        "Total_Protein": 6.8,
        "Albumin": 4.2,
        "Globulin": 2.6,
        "AG_Ratio": 1.6,
        "Bilirubin_Total": 0.9,
        "Bilirubin_Direct": 0.2,
        "ALT": 35.0,
        "AST": 28.0,
        "ALP": 95.0,
        "Creatinine": 1.1,
        "BUN": 18.0,
        "BUN_Creatinine_Ratio": 16.4,
        "Sodium": 138.0,
        "Potassium": 4.2,
        "Chloride": 102.0,
        "Bicarbonate": 24.0
    }
    
    model_prediction: Dict[str, Any] = {
        'disease': 'Type 2 Diabetes',
        'confidence': 0.92,
        'probabilities': {
            'Type 2 Diabetes': 0.92,
            'Prediabetes': 0.05,
            'Healthy': 0.03
        },
        'prediction_timestamp': '2025-01-01T10:00:00'
    }
    
    patient_context = {
        'patient_id': 'TEST-001',
        'age': 55,
        'gender': 'male',
        'symptoms': ["Increased thirst", "Frequent urination", "Fatigue"],
        'medical_history': ["Prediabetes diagnosed 2 years ago"],
        'current_medications': ["Metformin 500mg"],
        'query': "My blood sugar has been high lately. What should I do?"
    }
    
    return PatientInput(
        biomarkers=biomarkers,
        model_prediction=model_prediction,
        patient_context=patient_context
    )


def main():
    """Run complete evolution loop test"""
    print("\n" + "=" * 80)
    print("PHASE 3: SELF-IMPROVEMENT LOOP TEST")
    print("=" * 80)
    
    # Setup
    print("\n1. Initializing system...")
    guild = create_guild()
    patient = create_test_patient()
    
    # Initialize gene pool with baseline
    print("\n2. Creating SOP Gene Pool...")
    gene_pool = SOPGenePool()
    
    print("\n3. Evaluating Baseline SOP...")
    # Run workflow with baseline SOP
    
    initial_state: GuildState = {
        'patient_biomarkers': patient.biomarkers,
        'model_prediction': patient.model_prediction,
        'patient_context': patient.patient_context,
        'plan': None,
        'sop': BASELINE_SOP,
        'agent_outputs': [],
        'biomarker_flags': [],
        'safety_alerts': [],
        'final_response': None,
        'processing_timestamp': datetime.now().isoformat(),
        'sop_version': "Baseline"
    }
    
    guild_state = guild.workflow.invoke(initial_state)
    
    baseline_response = guild_state['final_response']
    agent_outputs = guild_state['agent_outputs']
    
    baseline_eval = run_full_evaluation(
        final_response=baseline_response,
        agent_outputs=agent_outputs,
        biomarkers=patient.biomarkers
    )
    
    gene_pool.add(
        sop=BASELINE_SOP,
        evaluation=baseline_eval,
        parent_version=None,
        description="Baseline SOP"
    )
    
    print(f"\n✓ Baseline Average Score: {baseline_eval.average_score():.3f}")
    print(f"  Clinical Accuracy:     {baseline_eval.clinical_accuracy.score:.3f}")
    print(f"  Evidence Grounding:    {baseline_eval.evidence_grounding.score:.3f}")
    print(f"  Actionability:         {baseline_eval.actionability.score:.3f}")
    print(f"  Clarity:               {baseline_eval.clarity.score:.3f}")
    print(f"  Safety & Completeness: {baseline_eval.safety_completeness.score:.3f}")
    
    # Run evolution cycles
    num_cycles = 2
    print(f"\n4. Running {num_cycles} Evolution Cycles...")
    
    for cycle in range(1, num_cycles + 1):
        print(f"\n{'─' * 80}")
        print(f"EVOLUTION CYCLE {cycle}")
        print(f"{'─' * 80}")
        
        try:
            # Create evaluation function for this cycle
            def eval_func(final_response, agent_outputs, biomarkers):
                return run_full_evaluation(
                    final_response=final_response,
                    agent_outputs=agent_outputs,
                    biomarkers=biomarkers
                )
            
            new_entries = run_evolution_cycle(
                gene_pool=gene_pool,
                patient_input=patient,
                workflow_graph=guild.workflow,
                evaluation_func=eval_func
            )
            
            print(f"\n✓ Cycle {cycle} complete: Added {len(new_entries)} new SOPs to gene pool")
            
            for entry in new_entries:
                print(f"\n  SOP v{entry['version']}: {entry['description']}")
                print(f"    Average Score: {entry['evaluation'].average_score():.3f}")
            
        except Exception as e:
            print(f"\n⚠️ Cycle {cycle} encountered error: {e}")
            print("Continuing to next cycle...")
    
    # Show gene pool summary
    print("\n5. Gene Pool Summary:")
    gene_pool.summary()
    
    # Pareto Analysis
    print("\n6. Identifying Pareto Frontier...")
    all_entries = gene_pool.gene_pool
    pareto_front = identify_pareto_front(all_entries)
    
    print(f"\n✓ Pareto frontier contains {len(pareto_front)} non-dominated solutions")
    print_pareto_summary(pareto_front)
    
    # Improvement Analysis
    print("\n7. Analyzing Improvements...")
    analyze_improvements(all_entries)
    
    # Visualizations
    print("\n8. Generating Visualizations...")
    visualize_pareto_frontier(pareto_front)
    
    # Final Summary
    print("\n" + "=" * 80)
    print("EVOLUTION TEST COMPLETE")
    print("=" * 80)
    
    print(f"\n✓ Total SOPs in Gene Pool: {len(all_entries)}")
    print(f"✓ Pareto Optimal SOPs: {len(pareto_front)}")
    
    # Find best average score
    best_sop = max(all_entries, key=lambda e: e['evaluation'].average_score())
    baseline_avg = baseline_eval.average_score()
    best_avg = best_sop['evaluation'].average_score()
    improvement = ((best_avg - baseline_avg) / baseline_avg) * 100
    
    print(f"\nBest SOP: v{best_sop['version']} - {best_sop['description']}")
    print(f"  Average Score: {best_avg:.3f} ({improvement:+.1f}% vs baseline)")
    
    print("\n✓ Visualization saved to: data/pareto_frontier_analysis.png")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
