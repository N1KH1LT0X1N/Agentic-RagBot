"""
Health Check Endpoint
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.models.schemas import HealthResponse
from app.services.ragbot import get_ragbot_service
from app import __version__


router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API health status.
    
    Verifies:
    - LLM API connection (Groq/Gemini)
    - Vector store loaded
    - Available models
    - Service uptime
    
    Returns health status with component details.
    """
    ragbot_service = get_ragbot_service()
    
    # Check LLM API connection
    llm_status = "disconnected"
    available_models = []
    
    try:
        from src.llm_config import get_chat_model, DEFAULT_LLM_PROVIDER
        
        test_llm = get_chat_model(temperature=0.0)
        
        # Try a simple test
        response = test_llm.invoke("Say OK")
        if response:
            llm_status = "connected"
            if DEFAULT_LLM_PROVIDER == "groq":
                available_models = ["llama-3.3-70b-versatile (Groq)"]
            elif DEFAULT_LLM_PROVIDER == "gemini":
                available_models = ["gemini-2.0-flash (Google)"]
            else:
                available_models = ["llama3.1:8b (Ollama)"]
    
    except Exception as e:
        llm_status = f"error: {str(e)[:100]}"
    
    # Check vector store
    vector_store_loaded = ragbot_service.is_ready()
    
    # Determine overall status
    if llm_status == "connected" and vector_store_loaded:
        overall_status = "healthy"
    elif llm_status == "connected" or vector_store_loaded:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        ollama_status=llm_status,  # Keep field name for backward compatibility
        vector_store_loaded=vector_store_loaded,
        available_models=available_models,
        uptime_seconds=ragbot_service.get_uptime_seconds(),
        version=__version__
    )
