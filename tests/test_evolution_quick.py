"""
Quick test of Phase 3 components
Tests gene pool, diagnostician, and architect without full workflow
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import BASELINE_SOP
from src.evaluation.evaluators import EvaluationResult, GradedScore
from src.evolution.director import SOPGenePool, performance_diagnostician, sop_architect


def main():
    """Quick test of evolution components"""
    print("\n" + "=" * 80)
    print("QUICK PHASE 3 TEST")
    print("=" * 80)
    
    # Test 1: Gene Pool
    print("\n1. Testing Gene Pool...")
    gene_pool = SOPGenePool()
    
    # Create mock evaluation (baseline with low clarity)
    baseline_eval = EvaluationResult(
        clinical_accuracy=GradedScore(score=0.95, reasoning="Accurate"),
        evidence_grounding=GradedScore(score=1.0, reasoning="Well cited"),
        actionability=GradedScore(score=0.90, reasoning="Clear actions"),
        clarity=GradedScore(score=0.75, reasoning="Could be clearer"),
        safety_completeness=GradedScore(score=1.0, reasoning="Complete")
    )
    
    gene_pool.add(
        sop=BASELINE_SOP,
        evaluation=baseline_eval,
        parent_version=None,
        description="Baseline SOP"
    )
    
    print(f"✓ Gene pool initialized with 1 SOP")
    print(f"  Average score: {baseline_eval.average_score():.3f}")
    
    # Test 2: Performance Diagnostician
    print("\n2. Testing Performance Diagnostician...")
    diagnosis = performance_diagnostician(baseline_eval)
    
    print(f"✓ Diagnosis complete")
    print(f"  Primary weakness: {diagnosis.primary_weakness}")
    print(f"  Root cause: {diagnosis.root_cause_analysis[:100]}...")
    print(f"  Recommendation: {diagnosis.recommendation[:100]}...")
    
    # Test 3: SOP Architect
    print("\n3. Testing SOP Architect...")
    evolved_sops = sop_architect(diagnosis, BASELINE_SOP)
    
    print(f"\n✓ Generated {len(evolved_sops.mutations)} mutations")
    for i, mutation in enumerate(evolved_sops.mutations, 1):
        print(f"\n  Mutation {i}: {mutation.description}")
        print(f"    Disease explainer K: {mutation.disease_explainer_k}")
        print(f"    Detail level: {mutation.explainer_detail_level}")
        print(f"    Citations required: {mutation.require_pdf_citations}")
    
    # Test 4: Gene Pool Summary
    print("\n4. Gene Pool Summary:")
    gene_pool.summary()
    
    # Test 5: Average score method
    print("\n5. Testing average_score method...")
    avg = baseline_eval.average_score()
    print(f"✓ Average score calculation: {avg:.3f}")
    vector = baseline_eval.to_vector()
    print(f"✓ Score vector: {[f'{s:.2f}' for s in vector]}")
    
    print("\n" + "=" * 80)
    print("QUICK TEST COMPLETE")
    print("=" * 80)
    print("\n✓ All Phase 3 components functional")
    print("✓ Ready for full evolution loop test")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
