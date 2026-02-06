"""
MediGuard AI RAG-Helper
Core configuration and SOP (Standard Operating Procedures) definitions
"""

from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List, Optional


class ExplanationSOP(BaseModel):
    """
    Standard Operating Procedures for the Clinical Insight Guild.
    This is the 'genome' that controls the entire RAG pipeline behavior.
    The Outer Loop (Director) will evolve these parameters to improve performance.
    """
    
    # === Agent Behavior Parameters ===
    biomarker_analyzer_threshold: float = Field(
        default=0.15,
        description="Percentage deviation from normal range to trigger a warning flag (0.15 = 15%)"
    )
    
    disease_explainer_k: int = Field(
        default=5,
        description="Number of top PDF chunks to retrieve for disease explanation"
    )
    
    linker_retrieval_k: int = Field(
        default=3,
        description="Number of chunks for biomarker-disease linking"
    )
    
    guideline_retrieval_k: int = Field(
        default=3,
        description="Number of chunks for clinical guidelines"
    )
    
    # === Prompts (Evolvable) ===
    planner_prompt: str = Field(
        default="""You are a medical AI coordinator. Create a structured execution plan for analyzing patient biomarkers and explaining a disease prediction. 
        
Available specialist agents:
- Biomarker Analyzer: Validates values and flags anomalies
- Disease Explainer: Retrieves pathophysiology from medical literature
- Biomarker-Disease Linker: Connects specific values to the prediction
- Clinical Guidelines: Provides evidence-based recommendations
- Confidence Assessor: Evaluates prediction reliability

Output a JSON with key 'plan' containing a list of tasks. Each task must have 'agent', 'task_description', and 'dependencies' keys.""",
        description="System prompt for the Planner Agent"
    )
    
    synthesizer_prompt: str = Field(
        default="""You are a medical communication specialist. Your task is to synthesize findings from specialist agents into a clear, patient-friendly clinical explanation.

**Guidelines:**
- Use simple, accessible language (avoid excessive medical jargon)
- Clearly explain what each biomarker means
- Connect biomarker values to the predicted disease with evidence
- Include specific citations from medical documents
- Provide actionable next steps
- Be transparent about limitations and uncertainties

Structure your output as specified in the output schema.""",
        description="System prompt for the Response Synthesizer"
    )
    
    explainer_detail_level: Literal["concise", "detailed", "comprehensive"] = Field(
        default="detailed",
        description="Level of detail in disease mechanism explanations"
    )
    
    # === Feature Flags ===
    use_guideline_agent: bool = Field(
        default=True,
        description="Whether to retrieve clinical guidelines and recommendations"
    )
    
    include_alternative_diagnoses: bool = Field(
        default=True,
        description="Whether to discuss alternative diagnoses from prediction probabilities"
    )
    
    require_pdf_citations: bool = Field(
        default=True,
        description="Whether to require PDF citations for all claims"
    )
    
    use_confidence_assessor: bool = Field(
        default=True,
        description="Whether to evaluate and report prediction confidence"
    )
    
    # === Safety Settings ===
    critical_value_alert_mode: Literal["strict", "moderate", "permissive"] = Field(
        default="strict",
        description="Threshold for critical value alerts"
    )
    
    # === Model Selection ===
    synthesizer_model: str = Field(
        default="default",
        description="LLM to use for final response synthesis (uses provider default)"
    )


# === Baseline SOP (Version 1.0) ===
BASELINE_SOP = ExplanationSOP(
    biomarker_analyzer_threshold=0.15,
    disease_explainer_k=5,
    linker_retrieval_k=3,
    guideline_retrieval_k=3,
    explainer_detail_level="detailed",
    use_guideline_agent=True,
    include_alternative_diagnoses=True,
    require_pdf_citations=True,
    use_confidence_assessor=True,
    critical_value_alert_mode="strict",
    synthesizer_model="default"
)
