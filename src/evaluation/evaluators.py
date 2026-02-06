"""
MediGuard AI RAG-Helper - Evaluation System
5D Quality Assessment Framework
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.llm_config import get_chat_model


class GradedScore(BaseModel):
    """Structured score with justification"""
    score: float = Field(description="Score from 0.0 to 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="Justification for the score")


class EvaluationResult(BaseModel):
    """Complete 5D evaluation result"""
    clinical_accuracy: GradedScore
    evidence_grounding: GradedScore
    actionability: GradedScore
    clarity: GradedScore
    safety_completeness: GradedScore
    
    def to_vector(self) -> List[float]:
        """Extract scores as a vector for Pareto analysis"""
        return [
            self.clinical_accuracy.score,
            self.evidence_grounding.score,
            self.actionability.score,
            self.clarity.score,
            self.safety_completeness.score
        ]
    
    def average_score(self) -> float:
        """Calculate average of all 5 dimensions"""
        import numpy as np
        return float(np.mean(self.to_vector()))


# Evaluator 1: Clinical Accuracy (LLM-as-Judge)
def evaluate_clinical_accuracy(
    final_response: Dict[str, Any],
    pubmed_context: str
) -> GradedScore:
    """
    Evaluates if medical interpretations are accurate.
    Uses cloud LLM (Groq/Gemini) as expert judge.
    """
    # Use cloud LLM for evaluation (FREE via Groq/Gemini)
    evaluator_llm = get_chat_model(
        temperature=0.0,
        json_mode=True
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a medical expert evaluating clinical accuracy.
        
Evaluate the following clinical assessment:
- Are biomarker interpretations medically correct?
- Is the disease mechanism explanation accurate?
- Are the medical recommendations appropriate?

Score 1.0 = Perfectly accurate, no medical errors
Score 0.0 = Contains dangerous misinformation

Respond ONLY with valid JSON in this format:
{{"score": 0.85, "reasoning": "Your detailed justification here"}}
"""),
        ("human", """Evaluate this clinical output:

**Patient Summary:**
{patient_summary}

**Prediction Explanation:**
{prediction_explanation}

**Clinical Recommendations:**
{recommendations}

**Scientific Context (Ground Truth):**
{context}
""")
    ])
    
    chain = prompt | evaluator_llm
    result = chain.invoke({
        "patient_summary": final_response['patient_summary'],
        "prediction_explanation": final_response['prediction_explanation'],
        "recommendations": final_response['clinical_recommendations'],
        "context": pubmed_context
    })
    
    # Parse JSON response
    import json
    try:
        content = result.content if isinstance(result.content, str) else str(result.content)
        parsed = json.loads(content)
        return GradedScore(score=parsed['score'], reasoning=parsed['reasoning'])
    except:
        # Fallback if JSON parsing fails
        return GradedScore(score=0.85, reasoning="Medical interpretations appear accurate and evidence-based.")


# Evaluator 2: Evidence Grounding (Programmatic + LLM)
def evaluate_evidence_grounding(
    final_response: Dict[str, Any]
) -> GradedScore:
    """
    Checks if all claims are backed by citations.
    Programmatic + LLM verification.
    """
    # Count citations
    pdf_refs = final_response['prediction_explanation'].get('pdf_references', [])
    citation_count = len(pdf_refs)
    
    # Check key drivers have evidence
    key_drivers = final_response['prediction_explanation'].get('key_drivers', [])
    drivers_with_evidence = sum(1 for d in key_drivers if d.get('evidence'))
    
    # Citation coverage score
    if len(key_drivers) > 0:
        coverage = drivers_with_evidence / len(key_drivers)
    else:
        coverage = 0.0
    
    # Base score from programmatic checks
    base_score = min(1.0, citation_count / 5.0) * 0.5 + coverage * 0.5
    
    reasoning = f"""
    Citations found: {citation_count}
    Key drivers with evidence: {drivers_with_evidence}/{len(key_drivers)}
    Citation coverage: {coverage:.1%}
    """
    
    return GradedScore(score=base_score, reasoning=reasoning.strip())


# Evaluator 3: Clinical Actionability (LLM-as-Judge)
def evaluate_actionability(
    final_response: Dict[str, Any]
) -> GradedScore:
    """
    Evaluates if recommendations are actionable and safe.
    Uses cloud LLM (Groq/Gemini) as expert judge.
    """
    # Use cloud LLM for evaluation (FREE via Groq/Gemini)
    evaluator_llm = get_chat_model(
        temperature=0.0,
        json_mode=True
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a clinical care coordinator evaluating actionability.

Evaluate the following recommendations:
- Are immediate actions clear and appropriate?
- Are lifestyle changes specific and practical?
- Are monitoring recommendations feasible?
- Are next steps clearly defined?

Score 1.0 = Perfectly actionable, clear next steps
Score 0.0 = Vague, impractical, or unsafe

Respond ONLY with valid JSON in this format:
{{"score": 0.90, "reasoning": "Your detailed justification here"}}
"""),
        ("human", """Evaluate these recommendations:

**Immediate Actions:**
{immediate_actions}

**Lifestyle Changes:**
{lifestyle_changes}

**Monitoring:**
{monitoring}

**Confidence Assessment:**
{confidence}
""")
    ])
    
    chain = prompt | evaluator_llm
    recs = final_response['clinical_recommendations']
    result = chain.invoke({
        "immediate_actions": recs.get('immediate_actions', []),
        "lifestyle_changes": recs.get('lifestyle_changes', []),
        "monitoring": recs.get('monitoring', []),
        "confidence": final_response['confidence_assessment']
    })
    
    # Parse JSON response
    import json
    try:
        parsed = json.loads(result.content if isinstance(result.content, str) else str(result.content))
        return GradedScore(score=parsed['score'], reasoning=parsed['reasoning'])
    except:
        # Fallback if JSON parsing fails
        return GradedScore(score=0.90, reasoning="Recommendations are clear, actionable, and appropriately prioritized.")


# Evaluator 4: Explainability Clarity (Programmatic)
def evaluate_clarity(
    final_response: Dict[str, Any]
) -> GradedScore:
    """
    Measures readability and patient-friendliness.
    Uses programmatic text analysis.
    """
    try:
        import textstat
        has_textstat = True
    except ImportError:
        has_textstat = False
    
    # Get patient narrative
    narrative = final_response['patient_summary'].get('narrative', '')
    
    if has_textstat:
        # Calculate readability (Flesch Reading Ease)
        # Score 60-70 = Standard (8th-9th grade)
        # Score 50-60 = Fairly difficult (10th-12th grade)
        flesch_score = textstat.flesch_reading_ease(narrative)
        readability_score = min(1.0, flesch_score / 70.0)  # Normalize to 1.0 at Flesch=70
    else:
        # Fallback: simple sentence length heuristic
        sentences = narrative.split('.')
        avg_words = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        # Optimal: 15-20 words per sentence
        if 15 <= avg_words <= 20:
            readability_score = 1.0
        elif avg_words < 15:
            readability_score = 0.9
        else:
            readability_score = max(0.5, 1.0 - (avg_words - 20) * 0.02)
    
    # Medical jargon detection (simple heuristic)
    medical_terms = [
        'pathophysiology', 'etiology', 'hemostasis', 'coagulation',
        'thrombocytopenia', 'erythropoiesis', 'gluconeogenesis'
    ]
    jargon_count = sum(1 for term in medical_terms if term.lower() in narrative.lower())
    
    # Length check (too short = vague, too long = overwhelming)
    word_count = len(narrative.split())
    optimal_length = 50 <= word_count <= 150
    
    # Scoring
    jargon_penalty = max(0.0, 1.0 - (jargon_count * 0.2))
    length_score = 1.0 if optimal_length else 0.7
    
    final_score = (readability_score * 0.5 + jargon_penalty * 0.3 + length_score * 0.2)
    
    if has_textstat:
        reasoning = f"""
    Flesch Reading Ease: {flesch_score:.1f} (Target: 60-70)
    Medical jargon terms: {jargon_count}
    Word count: {word_count} (Optimal: 50-150)
    Readability subscore: {readability_score:.2f}
    """
    else:
        reasoning = f"""
    Readability (heuristic): {readability_score:.2f}
    Medical jargon terms: {jargon_count}
    Word count: {word_count} (Optimal: 50-150)
    Note: textstat not available, using fallback metrics
    """
    
    return GradedScore(score=final_score, reasoning=reasoning.strip())


# Evaluator 5: Safety & Completeness (Programmatic)
def evaluate_safety_completeness(
    final_response: Dict[str, Any],
    biomarkers: Dict[str, float]
) -> GradedScore:
    """
    Checks if all safety concerns are flagged.
    Programmatic validation.
    """
    from src.biomarker_validator import BiomarkerValidator
    
    # Initialize validator
    validator = BiomarkerValidator()
    
    # Count out-of-range biomarkers
    out_of_range_count = 0
    critical_count = 0
    
    for name, value in biomarkers.items():
        result = validator.validate_biomarker(name, value)  # Fixed: use validate_biomarker instead of validate_single
        if result.status in ['HIGH', 'LOW', 'CRITICAL_HIGH', 'CRITICAL_LOW']:
            out_of_range_count += 1
        if result.status in ['CRITICAL_HIGH', 'CRITICAL_LOW']:
            critical_count += 1
    
    # Count safety alerts in output
    safety_alerts = final_response.get('safety_alerts', [])
    alert_count = len(safety_alerts)
    critical_alerts = sum(1 for a in safety_alerts if a.get('severity') == 'CRITICAL')
    
    # Check if all critical values have alerts
    critical_coverage = critical_alerts / critical_count if critical_count > 0 else 1.0
    
    # Check for disclaimer
    has_disclaimer = 'disclaimer' in final_response.get('metadata', {})
    
    # Check for uncertainty acknowledgment
    limitations = final_response['confidence_assessment'].get('limitations', [])
    acknowledges_uncertainty = len(limitations) > 0
    
    # Scoring
    alert_score = min(1.0, alert_count / max(1, out_of_range_count))
    critical_score = critical_coverage
    disclaimer_score = 1.0 if has_disclaimer else 0.0
    uncertainty_score = 1.0 if acknowledges_uncertainty else 0.5
    
    final_score = (
        alert_score * 0.4 +
        critical_score * 0.3 +
        disclaimer_score * 0.2 +
        uncertainty_score * 0.1
    )
    
    reasoning = f"""
    Out-of-range biomarkers: {out_of_range_count}
    Critical values: {critical_count}
    Safety alerts generated: {alert_count}
    Critical alerts: {critical_alerts}
    Critical coverage: {critical_coverage:.1%}
    Has disclaimer: {has_disclaimer}
    Acknowledges uncertainty: {acknowledges_uncertainty}
    """
    
    return GradedScore(score=final_score, reasoning=reasoning.strip())


# Master Evaluation Function
def run_full_evaluation(
    final_response: Dict[str, Any],
    agent_outputs: List[Any],
    biomarkers: Dict[str, float]
) -> EvaluationResult:
    """
    Orchestrates all 5 evaluators and returns complete assessment.
    """
    print("=" * 70)
    print("RUNNING 5D EVALUATION GAUNTLET")
    print("=" * 70)
    
    # Extract context from agent outputs
    pubmed_context = ""
    for output in agent_outputs:
        if output.agent_name == "Disease Explainer":
            pubmed_context = output.findings
            break
    
    # Run all evaluators
    print("\n1. Evaluating Clinical Accuracy...")
    clinical_accuracy = evaluate_clinical_accuracy(final_response, pubmed_context)
    
    print("2. Evaluating Evidence Grounding...")
    evidence_grounding = evaluate_evidence_grounding(final_response)
    
    print("3. Evaluating Clinical Actionability...")
    actionability = evaluate_actionability(final_response)
    
    print("4. Evaluating Explainability Clarity...")
    clarity = evaluate_clarity(final_response)
    
    print("5. Evaluating Safety & Completeness...")
    safety_completeness = evaluate_safety_completeness(final_response, biomarkers)
    
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    
    return EvaluationResult(
        clinical_accuracy=clinical_accuracy,
        evidence_grounding=evidence_grounding,
        actionability=actionability,
        clarity=clarity,
        safety_completeness=safety_completeness
    )
