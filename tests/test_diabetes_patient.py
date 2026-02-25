"""
MediGuard AI RAG-Helper
Sample Patient Test Case - Type 2 Diabetes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from src.state import PatientInput
from src.workflow import create_guild


def create_sample_diabetes_patient() -> PatientInput:
    """
    Create a realistic test case for Type 2 Diabetes patient.
    
    Clinical Profile:
    - 52-year-old male with elevated glucose and HbA1c
    - Multiple diabetes-related biomarker abnormalities
    - Some cardiovascular risk factors present
    """

    # Biomarker values showing Type 2 Diabetes pattern
    biomarkers = {
        # CRITICAL DIABETES INDICATORS
        "Glucose": 185.0,          # HIGH (normal: 70-100 mg/dL fasting)
        "HbA1c": 8.2,              # HIGH (normal: <5.7%, prediabetes: 5.7-6.4%, diabetes: >=6.5%)

        # INSULIN RESISTANCE MARKERS
        "Insulin": 22.5,           # HIGH (normal: 2.6-24.9 μIU/mL, but elevated for glucose level)

        # LIPID PANEL (Cardiovascular Risk)
        "Cholesterol": 235.0,      # HIGH (normal: <200 mg/dL)
        "Triglycerides": 210.0,    # HIGH (normal: <150 mg/dL)
        "HDL": 38.0,               # LOW (normal for male: >40 mg/dL)
        "LDL": 145.0,              # HIGH (normal: <100 mg/dL)

        # KIDNEY FUNCTION (Diabetes Complication Risk)
        "Creatinine": 1.3,         # Slightly HIGH (normal male: 0.7-1.3 mg/dL, borderline)
        "Urea": 45.0,              # Slightly HIGH (normal: 7-20 mg/dL)

        # LIVER FUNCTION
        "ALT": 42.0,               # Slightly HIGH (normal: 7-56 U/L, upper range)
        "AST": 38.0,               # NORMAL (normal: 10-40 U/L)

        # BLOOD CELLS (Generally Normal)
        "WBC": 7.5,                # NORMAL (4.5-11.0 x10^9/L)
        "RBC": 5.1,                # NORMAL (male: 4.7-6.1 x10^12/L)
        "Hemoglobin": 15.2,        # NORMAL (male: 13.8-17.2 g/dL)
        "Hematocrit": 45.5,        # NORMAL (male: 40.7-50.3%)
        "MCV": 89.0,               # NORMAL (80-96 fL)
        "MCH": 29.8,               # NORMAL (27-31 pg)
        "MCHC": 33.4,              # NORMAL (32-36 g/dL)
        "Platelets": 245.0,        # NORMAL (150-400 x10^9/L)

        # THYROID (Normal)
        "TSH": 2.1,                # NORMAL (0.4-4.0 mIU/L)
        "T3": 115.0,               # NORMAL (80-200 ng/dL)
        "T4": 8.5,                 # NORMAL (5-12 μg/dL)

        # ELECTROLYTES (Normal)
        "Sodium": 140.0,           # NORMAL (136-145 mmol/L)
        "Potassium": 4.2,          # NORMAL (3.5-5.0 mmol/L)
        "Calcium": 9.5,            # NORMAL (8.5-10.2 mg/dL)
    }

    # ML model prediction (simulated)
    model_prediction = {
        "disease": "Type 2 Diabetes",
        "confidence": 0.87,  # High confidence
        "probabilities": {
            "Type 2 Diabetes": 0.87,
            "Heart Disease": 0.08,  # Some cardiovascular markers
            "Anemia": 0.02,
            "Thrombocytopenia": 0.02,
            "Thalassemia": 0.01
        }
    }

    # Patient demographics
    patient_context = {
        "age": 52,
        "gender": "male",
        "bmi": 31.2,
        "patient_id": "TEST_DM_001",
        "test_date": "2024-01-15"
    }

    # Use baseline SOP

    return PatientInput(
        biomarkers=biomarkers,
        model_prediction=model_prediction,
        patient_context=patient_context
    )


def run_test():
    """Run the complete workflow with sample patient"""

    print("\n" + "="*70)
    print("MEDIGUARD AI RAG-HELPER - SYSTEM TEST")
    print("="*70)
    print("\nTest Case: Type 2 Diabetes Patient")
    print("Patient ID: TEST_DM_001")
    print("Age: 52 | Gender: Male")
    print("Key Findings: Elevated Glucose (185), HbA1c (8.2%), High Cholesterol")
    print("="*70 + "\n")

    # Create patient input
    patient = create_sample_diabetes_patient()

    # Initialize guild
    print("Initializing Clinical Insight Guild...")
    guild = create_guild()

    # Run workflow
    print("\nExecuting workflow...\n")
    response = guild.run(patient)

    # Display results
    print("\n" + "="*70)
    print("FINAL RESPONSE")
    print("="*70 + "\n")

    print("PATIENT SUMMARY")
    print("-" * 70)
    print(f"Narrative: {response['patient_summary']['narrative']}")
    print(f"Total Biomarkers: {response['patient_summary']['total_biomarkers_tested']}")
    print(f"Out of Range: {response['patient_summary']['biomarkers_out_of_range']}")
    print(f"Critical Values: {response['patient_summary']['critical_values']}")

    print("\n\nPREDICTION EXPLANATION")
    print("-" * 70)
    print(f"Disease: {response['prediction_explanation']['primary_disease']}")
    print(f"Confidence: {response['prediction_explanation']['confidence']:.1%}")
    print(f"\nMechanism: {response['prediction_explanation']['mechanism_summary'][:300]}...")
    print(f"\nKey Drivers ({len(response['prediction_explanation']['key_drivers'])}):")
    for i, driver in enumerate(response['prediction_explanation']['key_drivers'][:3], 1):
        contribution = driver.get('contribution', 0)
        if isinstance(contribution, str):
            print(f"  {i}. {driver['biomarker']}: {driver['value']} ({contribution} contribution)")
        else:
            print(f"  {i}. {driver['biomarker']}: {driver['value']} ({contribution:.0f}% contribution)")

    print("\n\nCLINICAL RECOMMENDATIONS")
    print("-" * 70)
    print(f"Immediate Actions ({len(response['clinical_recommendations']['immediate_actions'])}):")
    for action in response['clinical_recommendations']['immediate_actions'][:3]:
        print(f"  - {action}")
    print(f"\nLifestyle Changes ({len(response['clinical_recommendations']['lifestyle_changes'])}):")
    for change in response['clinical_recommendations']['lifestyle_changes'][:3]:
        print(f"  - {change}")

    print("\n\nCONFIDENCE ASSESSMENT")
    print("-" * 70)
    print(f"Prediction Reliability: {response['confidence_assessment']['prediction_reliability']}")
    print(f"Evidence Strength: {response['confidence_assessment']['evidence_strength']}")
    print(f"Limitations: {len(response['confidence_assessment']['limitations'])} identified")
    print(f"Recommendation: {response['confidence_assessment']['recommendation']}")

    print("\n\nSAFETY ALERTS")
    print("-" * 70)
    if response['safety_alerts']:
        for alert in response['safety_alerts']:
            if hasattr(alert, 'severity'):
                severity = alert.severity
                biomarker = alert.biomarker or 'General'
                message = alert.message
            else:
                severity = alert.get('severity', alert.get('priority', 'UNKNOWN'))
                biomarker = alert.get('biomarker', 'General')
                message = alert.get('message', str(alert))
            print(f"  [{severity}] {biomarker}: {message}")
    else:
        print("  No safety alerts")

    print("\n\n" + "="*70)
    print("METADATA")
    print("="*70)
    print(f"Timestamp: {response['metadata']['timestamp']}")
    print(f"System: {response['metadata']['system_version']}")
    print(f"Agents: {', '.join(response['metadata']['agents_executed'])}")

    # Save response to file (convert Pydantic objects to dicts for serialization)
    def _to_serializable(obj):
        """Recursively convert Pydantic models and non-serializable objects to dicts."""
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif isinstance(obj, dict):
            return {k: _to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_to_serializable(item) for item in obj]
        return obj

    output_file = Path(__file__).parent / "test_output_diabetes.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(_to_serializable(response), f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✓ Full response saved to: {output_file}")
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_test()
