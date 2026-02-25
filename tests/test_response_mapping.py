import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.services.ragbot import RagBotService


def test_format_response_uses_synthesizer_payload():
    service = RagBotService()
    workflow_result = {
        "final_response": {
            "biomarker_flags": [
                {
                    "name": "Glucose",
                    "value": 120,
                    "unit": "mg/dL",
                    "status": "HIGH",
                    "reference_range": "70-100 mg/dL",
                    "warning": None
                }
            ],
            "safety_alerts": [],
            "key_drivers": [],
            "disease_explanation": {
                "pathophysiology": "",
                "citations": [],
                "retrieved_chunks": None
            },
            "recommendations": {
                "immediate_actions": [],
                "lifestyle_changes": [],
                "monitoring": []
            },
            "confidence_assessment": {
                "prediction_reliability": "LOW",
                "evidence_strength": "WEAK",
                "limitations": []
            },
            "patient_summary": {"narrative": ""}
        },
        "biomarker_flags": [],
        "safety_alerts": []
    }

    response = service._format_response(
        request_id="req_test",
        workflow_result=workflow_result,
        input_biomarkers={"Glucose": 120},
        extracted_biomarkers=None,
        patient_context={},
        model_prediction={"disease": "Diabetes", "confidence": 0.6, "probabilities": {}},
        processing_time_ms=10.0
    )

    assert response.analysis.biomarker_flags[0].name == "Glucose"
