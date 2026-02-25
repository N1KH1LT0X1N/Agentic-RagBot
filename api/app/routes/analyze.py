"""
Analysis Endpoints
Natural language and structured biomarker analysis
"""

import os

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import AnalysisResponse, NaturalAnalysisRequest, StructuredAnalysisRequest
from app.services.extraction import extract_biomarkers, predict_disease_simple
from app.services.ragbot import get_ragbot_service

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/analyze/natural", response_model=AnalysisResponse)
async def analyze_natural(request: NaturalAnalysisRequest):
    """
    Analyze biomarkers from natural language input.
    
    **Flow:**
    1. Extract biomarkers from natural language using LLM
    2. Predict disease using rule-based or ML model
    3. Run complete RAG workflow analysis
    4. Return comprehensive results
    
    **Example request:**
    ```json
    {
      "message": "My glucose is 185, HbA1c is 8.2 and cholesterol is 210",
      "patient_context": {
        "age": 52,
        "gender": "male",
        "bmi": 31.2
      }
    }
    ```
    
    Returns full detailed analysis with all agent outputs, citations, recommendations.
    """

    # Get services
    ragbot_service = get_ragbot_service()

    if not ragbot_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RagBot service not initialized. Please try again in a moment."
        )

    # Extract biomarkers from natural language
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    biomarkers, extracted_context, error = extract_biomarkers(
        request.message,
        ollama_base_url=ollama_base_url
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "EXTRACTION_FAILED",
                "message": error,
                "input_received": request.message[:100],
                "suggestion": "Try: 'My glucose is 140 and HbA1c is 7.5'"
            }
        )

    if not biomarkers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "NO_BIOMARKERS_FOUND",
                "message": "Could not extract any biomarkers from your message",
                "input_received": request.message[:100],
                "suggestion": "Include specific biomarker values like 'glucose is 140'"
            }
        )

    # Merge extracted context with request context
    patient_context = request.patient_context.model_dump() if request.patient_context else {}
    patient_context.update(extracted_context)

    # Predict disease (simple rule-based for now)
    model_prediction = predict_disease_simple(biomarkers)

    try:
        # Run full analysis
        response = ragbot_service.analyze(
            biomarkers=biomarkers,
            patient_context=patient_context,
            model_prediction=model_prediction,
            extracted_biomarkers=biomarkers  # Keep original extraction
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "ANALYSIS_FAILED",
                "message": f"Analysis workflow failed: {e!s}",
                "biomarkers_received": biomarkers
            }
        )


@router.post("/analyze/structured", response_model=AnalysisResponse)
async def analyze_structured(request: StructuredAnalysisRequest):
    """
    Analyze biomarkers from structured input (skip extraction).
    
    **Flow:**
    1. Use provided biomarker dictionary directly
    2. Predict disease using rule-based or ML model
    3. Run complete RAG workflow analysis
    4. Return comprehensive results
    
    **Example request:**
    ```json
    {
      "biomarkers": {
        "Glucose": 185.0,
        "HbA1c": 8.2,
        "Cholesterol": 210.0,
        "Triglycerides": 210.0,
        "HDL": 38.0
      },
      "patient_context": {
        "age": 52,
        "gender": "male",
        "bmi": 31.2
      }
    }
    ```
    
    Use this endpoint when you already have structured biomarker data.
    Returns full detailed analysis with all agent outputs, citations, recommendations.
    """

    # Get services
    ragbot_service = get_ragbot_service()

    if not ragbot_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RagBot service not initialized. Please try again in a moment."
        )

    # Validate biomarkers
    if not request.biomarkers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "NO_BIOMARKERS",
                "message": "Biomarkers dictionary cannot be empty",
                "suggestion": "Provide at least one biomarker with a numeric value"
            }
        )

    # Patient context
    patient_context = request.patient_context.model_dump() if request.patient_context else {}

    # Predict disease
    model_prediction = predict_disease_simple(request.biomarkers)

    try:
        # Run full analysis
        response = ragbot_service.analyze(
            biomarkers=request.biomarkers,
            patient_context=patient_context,
            model_prediction=model_prediction,
            extracted_biomarkers=None  # No extraction for structured input
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "ANALYSIS_FAILED",
                "message": f"Analysis workflow failed: {e!s}",
                "biomarkers_received": request.biomarkers
            }
        )


@router.get("/example", response_model=AnalysisResponse)
async def get_example():
    """
    Get example diabetes case analysis.
    
    **Pre-run example case:**
    - 52-year-old male patient
    - Elevated glucose and HbA1c
    - Type 2 Diabetes prediction
    
    Useful for:
    - Testing API integration
    - Understanding response format
    - Demo purposes
    
    Same as CLI chatbot 'example' command.
    """

    # Get services
    ragbot_service = get_ragbot_service()

    if not ragbot_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RagBot service not initialized. Please try again in a moment."
        )

    # Example biomarkers (Type 2 Diabetes patient)
    biomarkers = {
        "Glucose": 185.0,
        "HbA1c": 8.2,
        "Hemoglobin": 13.5,
        "Platelets": 220000.0,
        "Cholesterol": 235.0,
        "Triglycerides": 210.0,
        "HDL Cholesterol": 38.0,
        "LDL Cholesterol": 165.0,
        "BMI": 31.2,
        "Systolic Blood Pressure": 142.0,
        "Diastolic Blood Pressure": 88.0
    }

    patient_context = {
        "age": 52,
        "gender": "male",
        "bmi": 31.2,
        "patient_id": "EXAMPLE-001"
    }

    model_prediction = {
        "disease": "Diabetes",
        "confidence": 0.87,
        "probabilities": {
            "Diabetes": 0.87,
            "Heart Disease": 0.08,
            "Anemia": 0.03,
            "Thalassemia": 0.01,
            "Thrombocytopenia": 0.01
        }
    }

    try:
        # Run analysis
        response = ragbot_service.analyze(
            biomarkers=biomarkers,
            patient_context=patient_context,
            model_prediction=model_prediction,
            extracted_biomarkers=None
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "EXAMPLE_FAILED",
                "message": f"Example analysis failed: {e!s}"
            }
        )
