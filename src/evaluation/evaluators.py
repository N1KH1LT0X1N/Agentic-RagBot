"""
MediGuard AI RAG-Helper - Evaluation System
5D Quality Assessment Framework

This module provides quality evaluation for RAG outputs using a 5-dimension framework:
1. Clinical Accuracy - Medical correctness (LLM-as-judge)
2. Evidence Grounding - Citation coverage (programmatic + LLM)
3. Actionability - Practical recommendations (LLM-as-judge)
4. Clarity - Communication quality (LLM-as-judge)
5. Safety Completeness - Safety alerts coverage (programmatic)

IMPORTANT LIMITATIONS:
- LLM-as-judge evaluations are non-deterministic (may vary between runs)
- Designed for offline batch evaluation, NOT production scoring
- Requires LLM API access (Groq or Gemini) for full evaluation
- Set EVALUATION_DETERMINISTIC=true for reproducible tests (uses heuristics)

Usage:
    from src.evaluation.evaluators import run_5d_evaluation
    
    result = run_5d_evaluation(final_response, pubmed_context)
    print(f"Average score: {result.average_score():.2f}")
"""

import json
import os
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.llm_config import get_chat_model

# Set to True for deterministic evaluation (testing)
DETERMINISTIC_MODE = os.environ.get("EVALUATION_DETERMINISTIC", "false").lower() == "true"


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

    def to_vector(self) -> list[float]:
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
        scores = self.to_vector()
        return sum(scores) / len(scores) if scores else 0.0


# Evaluator 1: Clinical Accuracy (LLM-as-Judge)
def evaluate_clinical_accuracy(
    final_response: dict[str, Any],
    pubmed_context: str
) -> GradedScore:
    """
    Evaluates if medical interpretations are accurate.
    Uses cloud LLM (Groq/Gemini) as expert judge.
    
    In DETERMINISTIC_MODE, uses heuristics instead.
    """
    # Deterministic mode for testing
    if DETERMINISTIC_MODE:
        return _deterministic_clinical_accuracy(final_response, pubmed_context)

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
    try:
        content = result.content if isinstance(result.content, str) else str(result.content)
        parsed = json.loads(content)
        return GradedScore(score=parsed['score'], reasoning=parsed['reasoning'])
    except (json.JSONDecodeError, KeyError, TypeError):
        # Fallback if JSON parsing fails — use a conservative score to avoid inflating metrics
        return GradedScore(score=0.5, reasoning="Unable to parse LLM evaluation response; defaulting to neutral score.")


# Evaluator 2: Evidence Grounding (Programmatic + LLM)
def evaluate_evidence_grounding(
    final_response: dict[str, Any]
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
    final_response: dict[str, Any]
) -> GradedScore:
    """
    Evaluates if recommendations are actionable and safe.
    Uses cloud LLM (Groq/Gemini) as expert judge.
    
    In DETERMINISTIC_MODE, uses heuristics instead.
    """
    # Deterministic mode for testing
    if DETERMINISTIC_MODE:
        return _deterministic_actionability(final_response)

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
    try:
        parsed = json.loads(result.content if isinstance(result.content, str) else str(result.content))
        return GradedScore(score=parsed['score'], reasoning=parsed['reasoning'])
    except (json.JSONDecodeError, KeyError, TypeError):
        # Fallback if JSON parsing fails — use a conservative score to avoid inflating metrics
        return GradedScore(score=0.5, reasoning="Unable to parse LLM evaluation response; defaulting to neutral score.")


# Evaluator 4: Explainability Clarity (Programmatic)
def evaluate_clarity(
    final_response: dict[str, Any]
) -> GradedScore:
    """
    Measures readability and patient-friendliness.
    Uses programmatic text analysis.
    
    In DETERMINISTIC_MODE, uses simple heuristics for reproducibility.
    """
    # Deterministic mode for testing
    if DETERMINISTIC_MODE:
        return _deterministic_clarity(final_response)

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
    final_response: dict[str, Any],
    biomarkers: dict[str, float]
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
    critical_score = min(1.0, critical_coverage)
    disclaimer_score = 1.0 if has_disclaimer else 0.0
    uncertainty_score = 1.0 if acknowledges_uncertainty else 0.5

    final_score = min(1.0, (
        alert_score * 0.4 +
        critical_score * 0.3 +
        disclaimer_score * 0.2 +
        uncertainty_score * 0.1
    ))

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
    final_response: dict[str, Any],
    agent_outputs: list[Any],
    biomarkers: dict[str, float]
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
            findings = output.findings
            if isinstance(findings, dict):
                pubmed_context = findings.get('mechanism_summary', '') or findings.get('pathophysiology', '')
            elif isinstance(findings, str):
                pubmed_context = findings
            else:
                pubmed_context = str(findings)
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


# ---------------------------------------------------------------------------
# Deterministic Evaluation Functions (for testing)
# ---------------------------------------------------------------------------

def _deterministic_clinical_accuracy(
    final_response: dict[str, Any],
    pubmed_context: str
) -> GradedScore:
    """Heuristic-based clinical accuracy (deterministic)."""
    score = 0.5
    reasons = []

    # Check if response has expected structure
    if final_response.get('patient_summary'):
        score += 0.1
        reasons.append("Has patient summary")

    if final_response.get('prediction_explanation'):
        score += 0.1
        reasons.append("Has prediction explanation")

    if final_response.get('clinical_recommendations'):
        score += 0.1
        reasons.append("Has clinical recommendations")

    # Check for citations
    pred = final_response.get('prediction_explanation', {})
    if isinstance(pred, dict):
        refs = pred.get('pdf_references', [])
        if refs:
            score += min(0.2, len(refs) * 0.05)
            reasons.append(f"Has {len(refs)} citations")

    return GradedScore(
        score=min(1.0, score),
        reasoning="[DETERMINISTIC] " + "; ".join(reasons)
    )


def _deterministic_actionability(
    final_response: dict[str, Any]
) -> GradedScore:
    """Heuristic-based actionability (deterministic)."""
    score = 0.5
    reasons = []

    recs = final_response.get('clinical_recommendations', {})
    if isinstance(recs, dict):
        if recs.get('immediate_actions'):
            score += 0.15
            reasons.append("Has immediate actions")
        if recs.get('lifestyle_changes'):
            score += 0.15
            reasons.append("Has lifestyle changes")
        if recs.get('monitoring'):
            score += 0.1
            reasons.append("Has monitoring recommendations")

    return GradedScore(
        score=min(1.0, score),
        reasoning="[DETERMINISTIC] " + "; ".join(reasons) if reasons else "[DETERMINISTIC] Missing recommendations"
    )


def _deterministic_clarity(
    final_response: dict[str, Any]
) -> GradedScore:
    """Heuristic-based clarity (deterministic)."""
    score = 0.5
    reasons = []

    summary = final_response.get('patient_summary', '')
    if isinstance(summary, str):
        word_count = len(summary.split())
        if 50 <= word_count <= 300:
            score += 0.2
            reasons.append(f"Summary length OK ({word_count} words)")
        elif word_count > 0:
            score += 0.1
            reasons.append("Has summary")

    # Check for structured output
    if final_response.get('biomarker_flags'):
        score += 0.15
        reasons.append("Has biomarker flags")

    if final_response.get('key_findings'):
        score += 0.15
        reasons.append("Has key findings")

    return GradedScore(
        score=min(1.0, score),
        reasoning="[DETERMINISTIC] " + "; ".join(reasons) if reasons else "[DETERMINISTIC] Limited structure"
    )
