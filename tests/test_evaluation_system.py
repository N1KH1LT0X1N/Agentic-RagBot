"""
Test the 5D Evaluation System
Tests all evaluators with real diabetes patient output
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from src.state import AgentOutput
from src.evaluation.evaluators import run_full_evaluation


def test_evaluation_system():
    """Test evaluation system with diabetes patient data"""
    
    print("=" * 80)
    print("TESTING 5D EVALUATION SYSTEM")
    print("=" * 80)
    
    # Load test output from diabetes patient
    test_output_path = Path(__file__).parent / 'test_output_diabetes.json'
    with open(test_output_path, 'r', encoding='utf-8') as f:
        final_response = json.load(f)
    
    print(f"\n✓ Loaded test data from: {test_output_path}")
    print(f"  - Disease: {final_response['prediction_explanation']['primary_disease']}")
    print(f"  - Confidence: {final_response['prediction_explanation']['confidence']:.1%}")
    print(f"  - Out of range biomarkers: {final_response['patient_summary']['biomarkers_out_of_range']}")
    print(f"  - Critical alerts: {len(final_response['safety_alerts'])}")
    
    # Reconstruct patient biomarkers from test output
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
        "Uric_Acid": 6.2,
        "WBC": 7200.0,
        "RBC": 4.7,
        "Hemoglobin": 14.2,
        "Hematocrit": 42.0,
        "Platelets": 245.0
    }
    
    print(f"\n✓ Reconstructed {len(biomarkers)} biomarker values")
    
    # Mock agent outputs to provide PubMed context for Clinical Accuracy evaluator
    disease_explainer_context = """
    Type 2 diabetes (T2D) accounts for the majority of cases and results 
    primarily from insulin resistance with a progressive beta-cell secretory defect.
    
    Pathophysiology:
    - Insulin resistance in peripheral tissues (muscle, liver, adipose)
    - Progressive decline in beta-cell function
    - Impaired glucose homeostasis leading to hyperglycemia
    - Long-term complications affecting cardiovascular, renal, and neurological systems
    
    Key Biomarkers:
    - Fasting glucose ≥126 mg/dL indicates diabetes
    - HbA1c ≥6.5% indicates diabetes
    - Elevated cholesterol and triglycerides common due to dyslipidemia
    - HDL typically reduced in metabolic syndrome
    
    Clinical Management:
    - Lifestyle modifications (diet, exercise)
    - Pharmacological intervention (metformin, insulin sensitizers)
    - Regular monitoring of glycemic control
    - Cardiovascular risk management
    """
    
    agent_outputs = [
        AgentOutput(
            agent_name="Disease Explainer",
            findings=disease_explainer_context,
            citations=["diabetes.pdf", "MediGuard_Diabetes_Guidelines_Extensive.pdf"]
        ),
        AgentOutput(
            agent_name="Biomarker Analyzer",
            findings="Analyzed 25 biomarkers. Found 19 out of range, 3 critical values.",
            citations=[]
        ),
        AgentOutput(
            agent_name="Biomarker-Disease Linker",
            findings="Glucose and HbA1c are primary drivers for Type 2 Diabetes prediction.",
            citations=["diabetes.pdf"]
        ),
        AgentOutput(
            agent_name="Clinical Guidelines",
            findings="Recommend immediate medical consultation, lifestyle modifications.",
            citations=["diabetes.pdf"]
        ),
        AgentOutput(
            agent_name="Confidence Assessor",
            findings="High confidence prediction (87%) based on strong biomarker evidence.",
            citations=[]
        )
    ]
    
    print(f"✓ Created {len(agent_outputs)} mock agent outputs for evaluation context")
    
    # Run full evaluation
    print("\n" + "=" * 80)
    print("RUNNING EVALUATION PIPELINE")
    print("=" * 80)
    
    try:
        evaluation_result = run_full_evaluation(
            final_response=final_response,
            agent_outputs=agent_outputs,
            biomarkers=biomarkers
        )
        
        # Display results
        print("\n" + "=" * 80)
        print("5D EVALUATION RESULTS")
        print("=" * 80)
        
        print(f"\n1. 📊 Clinical Accuracy: {evaluation_result.clinical_accuracy.score:.3f}")
        print(f"   Reasoning: {evaluation_result.clinical_accuracy.reasoning[:200]}...")
        
        print(f"\n2. 📚 Evidence Grounding: {evaluation_result.evidence_grounding.score:.3f}")
        print(f"   Reasoning: {evaluation_result.evidence_grounding.reasoning}")
        
        print(f"\n3. ⚡ Actionability: {evaluation_result.actionability.score:.3f}")
        print(f"   Reasoning: {evaluation_result.actionability.reasoning[:200]}...")
        
        print(f"\n4. 💡 Clarity: {evaluation_result.clarity.score:.3f}")
        print(f"   Reasoning: {evaluation_result.clarity.reasoning}")
        
        print(f"\n5. 🛡️ Safety & Completeness: {evaluation_result.safety_completeness.score:.3f}")
        print(f"   Reasoning: {evaluation_result.safety_completeness.reasoning}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        scores = evaluation_result.to_vector()
        avg_score = sum(scores) / len(scores)
        
        print(f"\n✓ Evaluation Vector: {[f'{s:.3f}' for s in scores]}")
        print(f"✓ Average Score: {avg_score:.3f}")
        print(f"✓ Min Score: {min(scores):.3f}")
        print(f"✓ Max Score: {max(scores):.3f}")
        
        # Validation checks
        print("\n" + "=" * 80)
        print("VALIDATION CHECKS")
        print("=" * 80)
        
        all_valid = True
        
        for i, (name, score) in enumerate([
            ("Clinical Accuracy", evaluation_result.clinical_accuracy.score),
            ("Evidence Grounding", evaluation_result.evidence_grounding.score),
            ("Actionability", evaluation_result.actionability.score),
            ("Clarity", evaluation_result.clarity.score),
            ("Safety & Completeness", evaluation_result.safety_completeness.score)
        ], 1):
            if 0.0 <= score <= 1.0:
                print(f"✓ {name}: Score in valid range [0.0, 1.0]")
            else:
                print(f"✗ {name}: Score OUT OF RANGE: {score}")
                all_valid = False
        
        if all_valid:
            print("\n" + "=" * 80)
            print("🎉 ALL EVALUATORS PASSED VALIDATION")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠️ SOME EVALUATORS FAILED VALIDATION")
            print("=" * 80)
        
        return evaluation_result
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ EVALUATION FAILED")
        print("=" * 80)
        print(f"\nError: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("\n🚀 Starting 5D Evaluation System Test\n")
    result = test_evaluation_system()
    print("\n✅ Test completed successfully!")
