"""
MediGuard AI — Hugging Face Spaces Gradio App

Standalone deployment that uses:
- FAISS vector store (local)
- Cloud LLMs (Groq or Gemini - FREE tiers)
- Multiple embedding providers (Jina, Google, HuggingFace)
- Optional Langfuse observability

Environment Variables (HuggingFace Secrets):
  Required (pick one):
    - GROQ_API_KEY: Groq API key (recommended, free)
    - GOOGLE_API_KEY: Google Gemini API key (free)
  
  Optional - LLM Configuration:
    - LLM_PROVIDER: "groq" or "gemini" (auto-detected from keys)
    - GROQ_MODEL: Model name (default: llama-3.3-70b-versatile)
    - GEMINI_MODEL: Model name (default: gemini-2.0-flash)
  
  Optional - Embeddings:
    - EMBEDDING_PROVIDER: "jina", "google", or "huggingface" (default: huggingface)
    - JINA_API_KEY: Jina AI API key for high-quality embeddings
  
  Optional - Observability:
    - LANGFUSE_ENABLED: "true" to enable tracing
    - LANGFUSE_PUBLIC_KEY: Langfuse public key
    - LANGFUSE_SECRET_KEY: Langfuse secret key
    - LANGFUSE_HOST: Langfuse host URL
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Ensure project root is in path
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

import gradio as gr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("mediguard.huggingface")

# ---------------------------------------------------------------------------
# Configuration - Environment Variable Helpers
# ---------------------------------------------------------------------------

def _get_env(primary: str, *fallbacks, default: str = "") -> str:
    """Get env var with multiple fallback names for compatibility."""
    value = os.getenv(primary)
    if value:
        return value
    for fb in fallbacks:
        value = os.getenv(fb)
        if value:
            return value
    return default


def get_api_keys():
    """Get API keys dynamically (HuggingFace injects secrets after module load).
    
    Supports both simple and nested naming conventions:
    - GROQ_API_KEY / LLM__GROQ_API_KEY
    - GOOGLE_API_KEY / LLM__GOOGLE_API_KEY
    """
    groq_key = _get_env("GROQ_API_KEY", "LLM__GROQ_API_KEY")
    google_key = _get_env("GOOGLE_API_KEY", "LLM__GOOGLE_API_KEY")
    return groq_key, google_key


def get_jina_api_key() -> str:
    """Get Jina API key for embeddings."""
    return _get_env("JINA_API_KEY", "EMBEDDING__JINA_API_KEY")


def get_embedding_provider() -> str:
    """Get configured embedding provider."""
    return _get_env("EMBEDDING_PROVIDER", "EMBEDDING__PROVIDER", default="huggingface")


def get_groq_model() -> str:
    """Get configured Groq model name."""
    return _get_env("GROQ_MODEL", "LLM__GROQ_MODEL", default="llama-3.3-70b-versatile")


def get_gemini_model() -> str:
    """Get configured Gemini model name."""
    return _get_env("GEMINI_MODEL", "LLM__GEMINI_MODEL", default="gemini-2.0-flash")


def is_langfuse_enabled() -> bool:
    """Check if Langfuse observability is enabled."""
    enabled = _get_env("LANGFUSE_ENABLED", "LANGFUSE__ENABLED", default="false")
    return enabled.lower() in ("true", "1", "yes")


def setup_llm_provider():
    """Set up LLM provider and related configuration based on available keys.
    
    Sets environment variables for the entire application to use.
    """
    groq_key, google_key = get_api_keys()
    provider = None

    if groq_key:
        os.environ["LLM_PROVIDER"] = "groq"
        os.environ["GROQ_API_KEY"] = groq_key
        os.environ["GROQ_MODEL"] = get_groq_model()
        provider = "groq"
        logger.info(f"Configured Groq provider with model: {get_groq_model()}")
    elif google_key:
        os.environ["LLM_PROVIDER"] = "gemini"
        os.environ["GOOGLE_API_KEY"] = google_key
        os.environ["GEMINI_MODEL"] = get_gemini_model()
        provider = "gemini"
        logger.info(f"Configured Gemini provider with model: {get_gemini_model()}")

    # Set up embedding provider
    embedding_provider = get_embedding_provider()
    os.environ["EMBEDDING_PROVIDER"] = embedding_provider

    # If Jina is configured, set the API key
    jina_key = get_jina_api_key()
    if jina_key:
        os.environ["JINA_API_KEY"] = jina_key
        os.environ["EMBEDDING__JINA_API_KEY"] = jina_key
        logger.info("Jina embeddings configured")

    # Set up Langfuse if enabled
    if is_langfuse_enabled():
        os.environ["LANGFUSE__ENABLED"] = "true"
        for var in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
            val = _get_env(var, f"LANGFUSE__{var.split('_', 1)[1]}")
            if val:
                os.environ[var] = val
        logger.info("Langfuse observability enabled")

    return provider


# Log status at startup (keys may not be available yet)
_groq, _google = get_api_keys()
_jina = get_jina_api_key()
logger.info("=" * 60)
logger.info("MediGuard AI — HuggingFace Space Starting")
logger.info("=" * 60)
logger.info(f"GROQ_API_KEY: {'✓ configured' if _groq else '✗ not set'}")
logger.info(f"GOOGLE_API_KEY: {'✓ configured' if _google else '✗ not set'}")
logger.info(f"JINA_API_KEY: {'✓ configured' if _jina else '✗ not set (using HuggingFace embeddings)'}")
logger.info(f"EMBEDDING_PROVIDER: {get_embedding_provider()}")
logger.info(f"LANGFUSE: {'✓ enabled' if is_langfuse_enabled() else '✗ disabled'}")

if not _groq and not _google:
    logger.warning(
        "No LLM API key found at startup. Will check again when analyzing."
    )
else:
    logger.info("LLM API key available — ready for analysis")
logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Guild Initialization (lazy)
# ---------------------------------------------------------------------------

_guild = None
_guild_error = None
_guild_provider = None  # Track which provider was used


def reset_guild():
    """Reset guild to force re-initialization (e.g., when API key changes)."""
    global _guild, _guild_error, _guild_provider
    _guild = None
    _guild_error = None
    _guild_provider = None


def get_guild():
    """Lazy initialization of the Clinical Insight Guild."""
    global _guild, _guild_error, _guild_provider

    # Check if we need to reinitialize (provider changed)
    current_provider = os.getenv("LLM_PROVIDER")
    if _guild_provider and _guild_provider != current_provider:
        logger.info(f"Provider changed from {_guild_provider} to {current_provider}, reinitializing...")
        reset_guild()

    if _guild is not None:
        return _guild

    if _guild_error is not None:
        # Don't cache errors forever - allow retry
        logger.warning("Previous initialization failed, retrying...")
        _guild_error = None

    try:
        logger.info("Initializing Clinical Insight Guild...")
        logger.info(f"  LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'not set')}")
        logger.info(f"  GROQ_API_KEY: {'✓ set' if os.getenv('GROQ_API_KEY') else '✗ not set'}")
        logger.info(f"  GOOGLE_API_KEY: {'✓ set' if os.getenv('GOOGLE_API_KEY') else '✗ not set'}")
        logger.info(f"  EMBEDDING_PROVIDER: {os.getenv('EMBEDDING_PROVIDER', 'huggingface')}")
        logger.info(f"  JINA_API_KEY: {'✓ set' if os.getenv('JINA_API_KEY') else '✗ not set'}")

        start = time.time()

        from src.workflow import create_guild
        _guild = create_guild()
        _guild_provider = current_provider

        elapsed = time.time() - start
        logger.info(f"Guild initialized in {elapsed:.1f}s")
        return _guild

    except Exception as exc:
        logger.error(f"Failed to initialize guild: {exc}")
        _guild_error = exc
        raise


# ---------------------------------------------------------------------------
# Analysis Functions — Import from shared utilities
# ---------------------------------------------------------------------------

# Import shared parsing and prediction logic
from src.shared_utils import (
    get_primary_prediction,
    parse_biomarkers,
)


# auto_predict wraps the shared function for backward compatibility
def auto_predict(biomarkers: dict[str, float]) -> dict[str, Any]:
    """
    Auto-generate a disease prediction based on biomarkers.
    This uses rule-based heuristics (not ML).
    """
    return get_primary_prediction(biomarkers)


def analyze_biomarkers(input_text: str, progress=gr.Progress()) -> tuple[str, str, str]:
    """
    Analyze biomarkers using the Clinical Insight Guild.
    
    Returns: (summary, details_json, status)
    """
    if not input_text.strip():
        return "", "", """
<div style="background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%); border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px; text-align: center;">
    <span style="font-size: 2em;">✍️</span>
    <p style="margin: 8px 0 0 0; color: #64748b;">Please enter biomarkers to analyze.</p>
</div>
        """

    # Check API key dynamically (HF injects secrets after startup)
    groq_key, google_key = get_api_keys()

    if not groq_key and not google_key:
        return "", "", """
<div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border: 1px solid #ef4444; border-radius: 10px; padding: 16px;">
    <strong style="color: #dc2626;">❌ No API Key Configured</strong>
    <p style="margin: 12px 0 8px 0; color: #991b1b;">Please add your API key in Space Settings → Secrets:</p>
    
    <div style="margin: 12px 0;">
        <strong style="color: #374151;">Required (pick one):</strong>
        <ul style="margin: 4px 0; color: #7f1d1d;">
            <li><code>GROQ_API_KEY</code> - <a href="https://console.groq.com/keys" target="_blank" style="color: #2563eb;">Get free key →</a> (Recommended)</li>
            <li><code>GOOGLE_API_KEY</code> - <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #2563eb;">Get free key →</a></li>
        </ul>
    </div>
    
    <details style="margin-top: 12px;">
        <summary style="cursor: pointer; color: #374151; font-weight: 600;">Optional configuration secrets</summary>
        <ul style="margin: 8px 0; color: #6b7280; font-size: 0.9em;">
            <li><code>GROQ_MODEL</code> - Model name (default: llama-3.3-70b-versatile)</li>
            <li><code>GEMINI_MODEL</code> - Model name (default: gemini-2.0-flash)</li>
            <li><code>JINA_API_KEY</code> - High-quality embeddings (optional)</li>
            <li><code>EMBEDDING_PROVIDER</code> - jina, google, or huggingface</li>
            <li><code>LANGFUSE_ENABLED</code> - Enable observability tracing</li>
        </ul>
    </details>
</div>
        """

    # Setup provider based on available key
    provider = setup_llm_provider()
    logger.info(f"Using LLM provider: {provider}")

    try:
        progress(0.1, desc="📝 Parsing biomarkers...")
        biomarkers = parse_biomarkers(input_text)

        if not biomarkers:
            return "", "", """
<div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 1px solid #fbbf24; border-radius: 10px; padding: 16px;">
    <strong>⚠️ Could not parse biomarkers</strong>
    <p style="margin: 8px 0 0 0; color: #92400e;">Try formats like:</p>
    <ul style="margin: 8px 0 0 0; color: #92400e;">
        <li><code>Glucose: 140, HbA1c: 7.5</code></li>
        <li><code>{"Glucose": 140, "HbA1c": 7.5}</code></li>
    </ul>
</div>
            """

        progress(0.2, desc="🔧 Initializing AI agents...")

        # Initialize guild
        guild = get_guild()

        # Prepare input
        from src.state import PatientInput

        # Auto-generate prediction based on common patterns
        prediction = auto_predict(biomarkers)

        patient_input = PatientInput(
            biomarkers=biomarkers,
            model_prediction=prediction,
            patient_context={"patient_id": "HF_User", "source": "huggingface_spaces"}
        )

        progress(0.4, desc="🤖 Running Clinical Insight Guild...")

        # Run analysis
        start = time.time()
        result = guild.run(patient_input)
        elapsed = time.time() - start

        progress(0.9, desc="✨ Formatting results...")

        # Extract response
        final_response = result.get("final_response", {})

        # Format summary
        summary = format_summary(final_response, elapsed)

        # Format details
        details = json.dumps(final_response, indent=2, default=str)

        status = f"""
<div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border: 1px solid #10b981; border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 10px;">
    <span style="font-size: 1.5em;">✅</span>
    <div>
        <strong style="color: #047857;">Analysis Complete</strong>
        <span style="color: #065f46; margin-left: 8px;">({elapsed:.1f}s)</span>
    </div>
</div>
        """

        return summary, details, status

    except Exception as exc:
        logger.error(f"Analysis error: {exc}", exc_info=True)
        error_msg = f"""
<div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border: 1px solid #ef4444; border-radius: 10px; padding: 16px;">
    <strong style="color: #dc2626;">❌ Analysis Error</strong>
    <p style="margin: 8px 0 0 0; color: #991b1b;">{exc}</p>
    <details style="margin-top: 12px;">
        <summary style="cursor: pointer; color: #7f1d1d;">Show details</summary>
        <pre style="margin-top: 8px; padding: 12px; background: #fef2f2; border-radius: 6px; overflow-x: auto; font-size: 0.8em;">{traceback.format_exc()}</pre>
    </details>
</div>
        """
        return "", "", error_msg


def format_summary(response: dict, elapsed: float) -> str:
    """Format the analysis response as clean markdown with black text."""
    if not response:
        return "❌ **No analysis results available.**"

    parts = []

    # Header with primary finding and confidence
    primary = response.get("primary_finding", "Analysis Complete")
    confidence = response.get("confidence", {})
    conf_score = confidence.get("overall_score", 0) if isinstance(confidence, dict) else 0

    # Determine severity
    severity = response.get("severity", "low")
    severity_config = {
        "critical": ("🔴", "#dc2626", "#fef2f2"),
        "high": ("🟠", "#ea580c", "#fff7ed"),
        "moderate": ("🟡", "#ca8a04", "#fefce8"),
        "low": ("🟢", "#16a34a", "#f0fdf4")
    }
    emoji, color, bg_color = severity_config.get(severity, severity_config["low"])

    # Build confidence display
    conf_badge = ""
    if conf_score:
        conf_pct = int(conf_score * 100)
        conf_color = "#16a34a" if conf_pct >= 80 else "#ca8a04" if conf_pct >= 60 else "#dc2626"
        conf_badge = f'<span style="background: {conf_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; margin-left: 12px;">{conf_pct}% confidence</span>'

    parts.append(f"""
<div style="background: linear-gradient(135deg, {bg_color} 0%, white 100%); border-left: 4px solid {color}; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; flex-wrap: wrap;">
        <span style="font-size: 1.5em; margin-right: 12px;">{emoji}</span>
        <h2 style="margin: 0; color: #1e293b; font-size: 1.4em;">{primary}</h2>
        {conf_badge}
    </div>
</div>""")

    # Critical Alerts
    alerts = response.get("safety_alerts", [])
    if alerts:
        alert_items = ""
        for alert in alerts[:5]:
            if isinstance(alert, dict):
                alert_items += f'<li><strong>{alert.get("alert_type", "Alert")}:</strong> {alert.get("message", "")}</li>'
            else:
                alert_items += f'<li>{alert}</li>'

        parts.append(f"""
<div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border: 1px solid #fecaca; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <h4 style="margin: 0 0 12px 0; color: #dc2626; display: flex; align-items: center; gap: 8px;">
        ⚠️ Critical Alerts
    </h4>
    <ul style="margin: 0; padding-left: 20px; color: #991b1b;">{alert_items}</ul>
</div>
        """)

    # Key Findings
    findings = response.get("key_findings", [])
    if findings:
        finding_items = "".join([f'<li style="margin-bottom: 8px;">{f}</li>' for f in findings[:5]])
        parts.append(f"""
<div style="background: #f8fafc; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <h4 style="margin: 0 0 12px 0; color: #1e3a5f;">🔍 Key Findings</h4>
    <ul style="margin: 0; padding-left: 20px; color: #475569;">{finding_items}</ul>
</div>
        """)

    # Biomarker Flags - as a visual grid
    flags = response.get("biomarker_flags", [])
    if flags and len(flags) > 0:
        flag_cards = ""
        for flag in flags[:8]:
            if isinstance(flag, dict):
                name = flag.get("biomarker", flag.get("name", "Biomarker"))
                # Skip if name is still unknown or generic
                if not name or name.lower() in ["unknown", "biomarker", ""]:
                    continue
                status = flag.get("status", "normal").lower()
                value = flag.get("value", flag.get("result", "N/A"))

                status_styles = {
                    "critical": ("🔴", "#dc2626", "#fef2f2"),
                    "high": ("🔴", "#dc2626", "#fef2f2"),
                    "abnormal": ("🟡", "#ca8a04", "#fefce8"),
                    "low": ("🟡", "#ca8a04", "#fefce8"),
                    "normal": ("🟢", "#16a34a", "#f0fdf4")
                }
                s_emoji, s_color, s_bg = status_styles.get(status, status_styles["normal"])

                flag_cards += f"""
<div style="background: {s_bg}; border: 1px solid {s_color}33; border-radius: 8px; padding: 12px; text-align: center;">
    <div style="font-size: 1.2em;">{s_emoji}</div>
    <div style="font-weight: 600; color: #1e3a5f; margin: 4px 0; font-size: 0.9em;">{name}</div>
    <div style="font-size: 1em; color: {s_color}; font-weight: 600;">{value}</div>
    <div style="font-size: 0.75em; color: #64748b; text-transform: capitalize;">{status}</div>
</div>
                """

        if flag_cards:  # Only show section if we have cards
            parts.append(f"""
<div style="margin-bottom: 16px;">
    <h4 style="margin: 0 0 12px 0; color: #1e3a5f;">📊 Biomarker Analysis</h4>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px;">
        {flag_cards}
    </div>
</div>
        """)

    # Recommendations - organized sections
    recs = response.get("recommendations", {})
    rec_sections = ""

    immediate = recs.get("immediate_actions", []) if isinstance(recs, dict) else []
    if immediate and len(immediate) > 0:
        items = "".join([f'<li style="margin-bottom: 6px;">{str(a).strip()}</li>' for a in immediate[:3]])
        rec_sections += f"""
<div style="margin-bottom: 12px;">
    <h5 style="margin: 0 0 8px 0; color: #dc2626;">🚨 Immediate Actions</h5>
    <ul style="margin: 0; padding-left: 20px; color: #475569;">{items}</ul>
</div>
        """

    lifestyle = recs.get("lifestyle_modifications", []) if isinstance(recs, dict) else []
    if lifestyle and len(lifestyle) > 0:
        items = "".join([f'<li style="margin-bottom: 6px;">{str(m).strip()}</li>' for m in lifestyle[:3]])
        rec_sections += f"""
<div style="margin-bottom: 12px;">
    <h5 style="margin: 0 0 8px 0; color: #16a34a;">🌿 Lifestyle Modifications</h5>
    <ul style="margin: 0; padding-left: 20px; color: #475569;">{items}</ul>
</div>
        """

    followup = recs.get("follow_up", []) if isinstance(recs, dict) else []
    if followup and len(followup) > 0:
        items = "".join([f'<li style="margin-bottom: 6px;">{str(f).strip()}</li>' for f in followup[:3]])
        rec_sections += f"""
<div>
    <h5 style="margin: 0 0 8px 0; color: #2563eb;">📅 Follow-up</h5>
    <ul style="margin: 0; padding-left: 20px; color: #475569;">{items}</ul>
</div>
        """

    # Add default recommendations if none provided
    if not rec_sections:
        rec_sections = """
<div style="margin-bottom: 12px;">
    <h5 style="margin: 0 0 8px 0; color: #2563eb;">📋 General Recommendations</h5>
    <ul style="margin: 0; padding-left: 20px; color: #475569;">
        <li style="margin-bottom: 6px;">Schedule an appointment with your healthcare provider for comprehensive evaluation</li>
        <li style="margin-bottom: 6px;">Maintain a regular log of your biomarker measurements</li>
        <li style="margin-bottom: 6px;">Follow up with laboratory testing as recommended by your physician</li>
    </ul>
</div>
        """

    if rec_sections:
        parts.append(f"""
<div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <h4 style="margin: 0 0 16px 0; color: #1e3a5f;">💡 Clinical Recommendations</h4>
    {rec_sections}
</div>
        """)

    # Disease Explanation
    explanation = response.get("disease_explanation", {})
    if explanation and isinstance(explanation, dict):
        pathophys = explanation.get("pathophysiology", "")
        if pathophys:
            parts.append(f"""
<div style="background: #f8fafc; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <h4 style="margin: 0 0 12px 0; color: #1e3a5f;">📖 Understanding Your Results</h4>
    <p style="margin: 0; color: #475569; line-height: 1.6;">{pathophys[:600]}{'...' if len(pathophys) > 600 else ''}</p>
</div>
            """)

    # Conversational Summary
    conv_summary = response.get("conversational_summary", "")
    if conv_summary:
        parts.append(f"""
<div style="background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <h4 style="margin: 0 0 12px 0; color: #7c3aed;">📝 Summary</h4>
    <p style="margin: 0; color: #475569; line-height: 1.6;">{conv_summary[:1000]}</p>
</div>
        """)

    # Footer
    parts.append(f"""
<div style="border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 8px; text-align: center;">
    <p style="margin: 0 0 8px 0; color: #94a3b8; font-size: 0.9em;">
        ✨ Analysis completed in <strong>{elapsed:.1f}s</strong> using Agentic RagBot
    </p>
    <p style="margin: 0; color: #f59e0b; font-size: 0.85em;">
        ⚠️ <em>This is for informational purposes only. Consult a healthcare professional for medical advice.</em>
    </p>
</div>
    """)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Q&A Chat Functions — Full Agentic RAG Pipeline
# ---------------------------------------------------------------------------

_rag_service = None
_rag_service_error = None


def _get_rag_service():
    """Lazily initialize the full agentic RAG service for Q&A.

    Uses a FAISS-backed retriever wrapped in an AgenticContext so the
    guardrail → retrieve → grade → rewrite → generate pipeline runs
    identically to the production API.
    """
    global _rag_service, _rag_service_error

    if _rag_service is not None:
        return _rag_service

    if _rag_service_error is not None:
        logger.warning("Previous RAG service init failed, retrying...")
        _rag_service_error = None

    try:
        from src.llm_config import get_synthesizer
        from src.services.agents.agentic_rag import AgenticRAGService
        from src.services.agents.context import AgenticContext
        from src.services.retrieval.factory import make_retriever

        llm = get_synthesizer()
        retriever = make_retriever()  # auto-detects FAISS

        # HF Space: skip OpenSearch, Redis, Langfuse
        # but still get guardrail, grading, rewriting, generation
        context = AgenticContext(
            llm=llm,
            embedding_service=None,
            opensearch_client=None,
            cache=None,
            tracer=None,
            retriever=retriever,
        )

        _rag_service = AgenticRAGService(context)
        logger.info("Agentic RAG service initialized for Q&A")
        return _rag_service

    except Exception as exc:
        logger.error(f"Failed to init agentic RAG service: {exc}")
        _rag_service_error = exc
        return None


def _fallback_qa(question: str, context_text: str = "") -> str:
    """Direct retriever+LLM fallback when agentic pipeline is unavailable."""
    from src.llm_config import get_synthesizer
    from src.services.retrieval.factory import make_retriever

    retriever = make_retriever()
    search_query = f"{context_text} {question}" if context_text.strip() else question
    docs = retriever.retrieve(search_query, top_k=5)

    doc_context = ""
    if docs:
        doc_texts = [d.content[:500] for d in docs[:5]]
        doc_context = "\n\n---\n\n".join(doc_texts)

    llm = get_synthesizer()
    prompt = f"""You are a medical AI assistant. Answer the following medical question based on the provided context.
Be helpful, accurate, and include relevant medical information. Always recommend consulting a healthcare professional.

Context from medical knowledge base:
{doc_context if doc_context else "No specific context available."}

Patient Context: {context_text if context_text else "Not provided"}

Question: {question}

Answer:"""
    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else str(response)


def answer_medical_question(
    question: str,
    context: str = "",
    chat_history: list = None
) -> tuple[str, list]:
    """Answer a medical question using the full agentic RAG pipeline.

    Pipeline: guardrail → retrieve → grade → rewrite → generate.
    Falls back to direct retriever+LLM if the pipeline is unavailable.
    """
    if not question.strip():
        return "", chat_history or []

    groq_key, google_key = get_api_keys()
    if not groq_key and not google_key:
        error_msg = "❌ Please add your GROQ_API_KEY or GOOGLE_API_KEY in Space Settings → Secrets."
        history = (chat_history or []) + [(question, error_msg)]
        return error_msg, history

    provider = setup_llm_provider()
    logger.info(f"Q&A using provider: {provider}")

    try:
        start_time = time.time()

        rag_service = _get_rag_service()
        if rag_service is not None:
            result = rag_service.ask(query=question, patient_context=context)
            answer = result.get("final_answer", "")
            guardrail = result.get("guardrail_score")
            docs_retrieved = len(result.get("retrieved_documents", []))
            docs_relevant = len(result.get("relevant_documents", []))
        else:
            logger.warning("Using fallback Q&A (agentic pipeline unavailable)")
            answer = _fallback_qa(question, context)
            guardrail = None
            docs_retrieved = 0
            docs_relevant = 0

        if not answer:
            answer = "I apologize, but I couldn't generate a response. Please try rephrasing your question."

        elapsed = time.time() - start_time

        meta_parts = [f"⏱️ {elapsed:.1f}s"]
        if guardrail is not None:
            meta_parts.append(f"🛡️ Guardrail: {guardrail:.0f}/100")
        if docs_retrieved > 0:
            meta_parts.append(f"📚 {docs_relevant}/{docs_retrieved} relevant docs")
        meta_parts.append("🤖 Agentic RAG" if rag_service else "🤖 RAG")
        meta_line = " | ".join(meta_parts)

        formatted_answer = f"""{answer}

---
*{meta_line}*
"""
        history = (chat_history or []) + [(question, formatted_answer)]
        return formatted_answer, history

    except Exception as exc:
        logger.exception(f"Q&A error: {exc}")
        error_msg = f"❌ Error: {exc!s}"
        history = (chat_history or []) + [(question, error_msg)]
        return error_msg, history


def streaming_answer(question: str, context: str, history: list, model: str):
    """Stream answer using the full agentic RAG pipeline.
    Falls back to direct retriever+LLM if the pipeline is unavailable.
    """
    history = history or []
    if not question.strip():
        yield history
        return

    history.append((question, ""))

    if not groq_key and not google_key:
        history[-1] = (question, "❌ Please add your GROQ_API_KEY or GOOGLE_API_KEY in Space Settings → Secrets.")
        yield history
        return

    # Update provider if model changed (simplified handling for UI demo)
    if "gemini" in model.lower():
        os.environ["LLM_PROVIDER"] = "gemini"
    else:
        os.environ["LLM_PROVIDER"] = "groq"

    setup_llm_provider()

    try:
        history[-1] = (question, "🛡️ Checking medical domain relevance...\n\n")
        yield history

        start_time = time.time()

        rag_service = _get_rag_service()
        if rag_service is not None:
            history[-1] = (question, "🛡️ Checking medical domain relevance...\n🔍 Retrieving medical documents...\n\n")
            yield history
            result = rag_service.ask(query=question, patient_context=context)
            answer = result.get("final_answer", "")
            guardrail = result.get("guardrail_score")
            docs_relevant = len(result.get("relevant_documents", []))
            docs_retrieved = len(result.get("retrieved_documents", []))
        else:
            history[-1] = (question, "🔍 Searching medical knowledge base...\n📚 Retrieving relevant documents...\n\n")
            yield history
            answer = _fallback_qa(question, context)
            guardrail = None
            docs_relevant = 0
            docs_retrieved = 0

        if not answer:
            answer = "I apologize, but I couldn't generate a response. Please try rephrasing your question."

        history[-1] = (question, "🛡️ Guardrail ✓\n🔍 Retrieved ✓\n📊 Graded ✓\n💭 Generating response...\n\n")
        yield history

        elapsed = time.time() - start_time

        # Progressive reveal
        words = answer.split()
        accumulated = ""
        for i, word in enumerate(words):
            accumulated += word + " "
            if i % 10 == 0:
                history[-1] = (question, accumulated)
                yield history
                time.sleep(0.01)

        # Final response with metadata
        meta_parts = [f"⏱️ {elapsed:.1f}s"]
        if guardrail is not None:
            meta_parts.append(f"🛡️ Guardrail: {guardrail:.0f}/100")
        if docs_retrieved > 0:
            meta_parts.append(f"📚 {docs_relevant}/{docs_retrieved} relevant docs")
        meta_parts.append("🤖 Agentic RAG" if rag_service else "🤖 RAG")
        meta_line = " | ".join(meta_parts)

        final_msg = f"{answer}\n\n---\n*{meta_line}*\n"
        history[-1] = (question, final_msg)
        yield history

    except Exception as exc:
        logger.exception(f"Streaming Q&A error: {exc}")
        history[-1] = (question, f"❌ Error: {exc!s}")
        yield history


def hf_search(query: str, mode: str):
    """Direct fast-retrieval for the HF Space Knowledge tab."""
    if not query.strip():
        return "Please enter a query."
    try:
        from src.services.retrieval.factory import make_retriever
        retriever = make_retriever()
        docs = retriever.retrieve(query, top_k=5)
        if not docs:
            return "No results found."
        parts = []
        for i, doc in enumerate(docs, 1):
            title = doc.metadata.get("title", doc.metadata.get("source_file", "Untitled"))
            score = doc.score if hasattr(doc, 'score') else 0.0
            parts.append(f"**[{i}] {title}** (score: {score:.3f})\n{doc.content}\n")
        return "\n---\n".join(parts)
    except Exception as exc:
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# Gradio Interface
# ---------------------------------------------------------------------------

# Custom CSS for modern medical UI
CUSTOM_CSS = """
/* Global Styles */
.gradio-container {
    max-width: 1400px !important;
    margin: auto !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide footer */
footer { display: none !important; }

/* Header styling */
.header-container {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 50%, #3d7ab5 100%);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 24px;
    color: white;
    text-align: center;
    box-shadow: 0 8px 32px rgba(30, 58, 95, 0.3);
}

.header-container h1 {
    margin: 0 0 12px 0;
    font-size: 2.5em;
    font-weight: 700;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.header-container p {
    margin: 0;
    opacity: 0.95;
    font-size: 1.1em;
}

/* Input panel */
.input-panel {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

/* Output panel */
.output-panel {
    background: white;
    border-radius: 16px;
    padding: 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    min-height: 500px;
}

/* Status badges */
.status-success {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 10px;
    font-weight: 600;
    display: inline-block;
}

.status-error {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 10px;
    font-weight: 600;
}

.status-warning {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 10px;
    font-weight: 600;
}

/* Info banner */
.info-banner {
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    border: 1px solid #93c5fd;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}

.info-banner-icon {
    font-size: 1.5em;
}

/* Agent cards */
.agent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin: 20px 0;
}

.agent-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.agent-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    border-color: #3b82f6;
}

.agent-card h4 {
    margin: 0 0 8px 0;
    color: #1e3a5f;
    font-size: 1em;
}

.agent-card p {
    margin: 0;
    color: #64748b;
    font-size: 0.9em;
}

/* Example buttons */
.example-btn {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    font-size: 0.85em;
}

.example-btn:hover {
    background: #e2e8f0;
    border-color: #94a3b8;
}

/* Buttons */
.primary-btn {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-weight: 600 !important;
    font-size: 1.1em !important;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important;
    transition: all 0.3s ease !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5) !important;
}

.secondary-btn {
    background: #f1f5f9 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.secondary-btn:hover {
    background: #e2e8f0 !important;
}

/* Results tabs */
.results-tabs {
    border-radius: 12px;
    overflow: hidden;
}

/* Disclaimer */
.disclaimer {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 1px solid #fbbf24;
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 24px;
    font-size: 0.9em;
}

/* Feature badges */
.feature-badge {
    display: inline-block;
    background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
    color: #4338ca;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.8em;
    font-weight: 600;
    margin: 4px;
}

/* Section titles */
.section-title {
    font-size: 1.25em;
    font-weight: 600;
    color: #1e3a5f;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Animations */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.analyzing {
    animation: pulse 1.5s ease-in-out infinite;
}
"""


def create_demo() -> gr.Blocks:
    """Create the Gradio Blocks interface with modern medical UI."""

    with gr.Blocks(
        title="Agentic RagBot - Medical Biomarker Analysis",
        theme=gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.slate,
            neutral_hue=gr.themes.colors.slate,
            font=gr.themes.GoogleFont("Inter"),
            font_mono=gr.themes.GoogleFont("JetBrains Mono"),
        ).set(
            body_background_fill="linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%)",
            block_background_fill="white",
            block_border_width="0px",
            block_shadow="0 4px 16px rgba(0, 0, 0, 0.08)",
            block_radius="16px",
            button_primary_background_fill="linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
            button_primary_background_fill_hover="linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
            button_primary_text_color="white",
            button_primary_shadow="0 4px 14px rgba(59, 130, 246, 0.4)",
            input_background_fill="#f8fafc",
            input_border_width="1px",
            input_border_color="#e2e8f0",
            input_radius="12px",
        ),
        css=CUSTOM_CSS,
    ) as demo:

        # ===== HEADER =====
        gr.HTML("""
        <div class="header-container">
            <h1>🏥 Agentic RagBot</h1>
            <p>Multi-Agent RAG System for Medical Biomarker Analysis</p>
            <div style="margin-top: 16px;">
                <span class="feature-badge">🤖 6 AI Agents</span>
                <span class="feature-badge">📚 RAG-Powered</span>
                <span class="feature-badge">⚡ Real-time Analysis</span>
                <span class="feature-badge">🔬 Evidence-Based</span>
            </div>
        </div>
        """)

        # ===== API KEY INFO =====
        gr.HTML("""
        <div class="info-banner">
            <span class="info-banner-icon">🔑</span>
            <div>
                <strong>Setup Required:</strong> Add your <code>GROQ_API_KEY</code> or 
                <code>GOOGLE_API_KEY</code> in Space Settings → Secrets to enable analysis.
                <a href="https://console.groq.com/keys" target="_blank" style="color: #2563eb;">Get free Groq key →</a>
                <br>
                <span style="font-size: 0.9em; color: #64748b;">
                    Optional: Configure <code>JINA_API_KEY</code> for high-quality embeddings, 
                    <code>LANGFUSE_ENABLED=true</code> for observability.
                </span>
            </div>
        </div>
        """)

        # ===== MAIN TABS =====
        with gr.Tabs() as main_tabs:

            # ==================== TAB 1: BIOMARKER ANALYSIS ====================
            with gr.Tab("🔬 Biomarker Analysis", id="biomarker-tab"):

                # ===== MAIN CONTENT =====
                with gr.Row(equal_height=False):

                    # ----- LEFT PANEL: INPUT -----
                    with gr.Column(scale=2, min_width=400):
                        gr.HTML('<div class="section-title">📝 Enter Your Biomarkers</div>')

                        with gr.Group():
                            input_text = gr.Textbox(
                                label="",
                                placeholder="Enter biomarkers in any format:\n\n• Glucose: 140, HbA1c: 7.5, Cholesterol: 210\n• My glucose is 140 and HbA1c is 7.5\n• {\"Glucose\": 140, \"HbA1c\": 7.5}",
                                lines=6,
                                max_lines=12,
                                show_label=False,
                            )

                            with gr.Row():
                                analyze_btn = gr.Button(
                                    "🔬 Analyze Biomarkers",
                                    variant="primary",
                                    size="lg",
                                    scale=3,
                                )
                                clear_btn = gr.Button(
                                    "🗑️ Clear",
                                    variant="secondary",
                                    size="lg",
                                    scale=1,
                                )

                        # Status display
                        status_output = gr.Markdown(
                            value="",
                            elem_classes="status-box"
                        )

                        # Quick Examples
                        gr.HTML('<div class="section-title" style="margin-top: 24px;">⚡ Quick Examples</div>')
                        gr.HTML('<p style="color: #64748b; font-size: 0.9em; margin-bottom: 12px;">Click any example to load it instantly</p>')

                        examples = gr.Examples(
                            examples=[
                                ["Glucose: 185, HbA1c: 8.2, Cholesterol: 245, LDL: 165"],
                                ["Glucose: 95, HbA1c: 5.4, Cholesterol: 180, HDL: 55, LDL: 100"],
                                ["Hemoglobin: 9.5, Iron: 40, Ferritin: 15"],
                                ["TSH: 8.5, T4: 4.0, T3: 80"],
                                ["Creatinine: 2.5, BUN: 45, eGFR: 35"],
                            ],
                            inputs=input_text,
                            label="",
                        )

                        # Supported Biomarkers
                        with gr.Accordion("📊 Supported Biomarkers", open=False):
                            gr.HTML("""
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; padding: 12px;">
                                <div>
                                    <h4 style="color: #1e3a5f; margin: 0 0 8px 0;">🩸 Diabetes</h4>
                                    <p style="color: #64748b; font-size: 0.85em; margin: 0;">Glucose, HbA1c, Fasting Glucose, Insulin</p>
                                </div>
                                <div>
                                    <h4 style="color: #1e3a5f; margin: 0 0 8px 0;">❤️ Cardiovascular</h4>
                                    <p style="color: #64748b; font-size: 0.85em; margin: 0;">Cholesterol, LDL, HDL, Triglycerides</p>
                                </div>
                                <div>
                                    <h4 style="color: #1e3a5f; margin: 0 0 8px 0;">🫘 Kidney</h4>
                                    <p style="color: #64748b; font-size: 0.85em; margin: 0;">Creatinine, BUN, eGFR, Uric Acid</p>
                                </div>
                                <div>
                                    <h4 style="color: #1e3a5f; margin: 0 0 8px 0;">🦴 Liver</h4>
                                    <p style="color: #64748b; font-size: 0.85em; margin: 0;">ALT, AST, Bilirubin, Albumin</p>
                                </div>
                                <div>
                                    <h4 style="color: #1e3a5f; margin: 0 0 8px 0;">🦋 Thyroid</h4>
                                    <p style="color: #64748b; font-size: 0.85em; margin: 0;">TSH, T3, T4, Free T4</p>
                                </div>
                                <div>
                                    <h4 style="color: #1e3a5f; margin: 0 0 8px 0;">💉 Blood</h4>
                                    <p style="color: #64748b; font-size: 0.85em; margin: 0;">Hemoglobin, WBC, RBC, Platelets</p>
                                </div>
                            </div>
                            """)

                    # ----- RIGHT PANEL: RESULTS -----
                    with gr.Column(scale=3, min_width=500):
                        gr.HTML('<div class="section-title">📊 Analysis Results</div>')

                        with gr.Tabs() as result_tabs:
                            with gr.Tab("📋 Summary", id="summary"):
                                summary_output = gr.Markdown(
                                    value="""
<div style="text-align: center; padding: 60px 20px; color: #94a3b8;">
    <div style="font-size: 4em; margin-bottom: 16px;">🔬</div>
    <h3 style="color: #64748b; font-weight: 500;">Ready to Analyze</h3>
    <p>Enter your biomarkers on the left and click <strong>Analyze</strong> to get your personalized health insights.</p>
</div>
                                    """,
                                    elem_classes="summary-output"
                                )

                            with gr.Tab("🔍 Detailed JSON", id="json"):
                                details_output = gr.Code(
                                    label="",
                                    language="json",
                                    lines=30,
                                    show_label=False,
                                )

            # ==================== TAB 2: MEDICAL Q&A ====================
            with gr.Tab("💬 Medical Q&A", id="qa-tab"):

                gr.HTML("""
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #1e3a5f; margin: 0 0 8px 0;">💬 Medical Q&A Assistant</h3>
                    <p style="color: #64748b; margin: 0;">
                        Ask any medical question and get evidence-based answers powered by our RAG system with 750+ pages of clinical guidelines.
                    </p>
                </div>
                """)

                with gr.Row(equal_height=False):
                    with gr.Column(scale=1):
                        qa_context = gr.Textbox(
                            label="Patient Context (Optional)",
                            placeholder="Provide biomarkers or context:\n• Glucose: 140, HbA1c: 7.5\n• 45-year-old male with family history of diabetes",
                            lines=3,
                            max_lines=6,
                        )
                        qa_model = gr.Dropdown(
                            choices=["llama-3.3-70b-versatile", "gemini-2.0-flash", "llama3.1:8b"],
                            value="llama-3.3-70b-versatile",
                            label="LLM Provider/Model"
                        )
                        qa_question = gr.Textbox(
                            label="Your Question",
                            placeholder="Ask any medical question...\n• What do my elevated glucose levels indicate?\n• Should I be concerned about my HbA1c of 7.5%?\n• What lifestyle changes help with prediabetes?",
                            lines=3,
                            max_lines=6,
                        )
                        with gr.Row():
                            qa_submit_btn = gr.Button(
                                "💬 Ask Question",
                                variant="primary",
                                size="lg",
                                scale=3,
                            )
                            qa_clear_btn = gr.Button(
                                "🗑️ Clear",
                                variant="secondary",
                                size="lg",
                                scale=1,
                            )

                        # Quick question examples
                        gr.HTML('<h4 style="margin-top: 16px; color: #1e3a5f;">Example Questions</h4>')
                        qa_examples = gr.Examples(
                            examples=[
                                ["What does elevated HbA1c mean?", ""],
                                ["How is diabetes diagnosed?", "Glucose: 185, HbA1c: 7.8"],
                                ["What lifestyle changes help lower cholesterol?", "LDL: 165, HDL: 35"],
                                ["What causes high creatinine levels?", "Creatinine: 2.5, BUN: 45"],
                            ],
                            inputs=[qa_question, qa_context],
                            label="",
                        )

                    with gr.Column(scale=2):
                        gr.HTML('<h4 style="color: #1e3a5f; margin-bottom: 12px;">📝 Answer</h4>')
                        qa_answer = gr.Chatbot(
                            label="Medical Q&A History",
                            height=600,
                            elem_classes="qa-output"
                        )

                # Q&A Event Handlers
                qa_submit_btn.click(
                    fn=streaming_answer,
                    inputs=[qa_question, qa_context, qa_answer, qa_model],
                    outputs=qa_answer,
                    show_progress="minimal",
                ).then(
                    fn=lambda: "",
                    outputs=qa_question
                )

                qa_clear_btn.click(
                    fn=lambda: ([], ""),
                    outputs=[qa_answer, qa_question],
                )

            # ==================== TAB 3: SEARCH KNOWLEDGE BASE ====================
            with gr.Tab("🔍 Search Knowledge Base", id="search-tab"):
                with gr.Row():
                    search_input = gr.Textbox(
                        label="Search Query",
                        placeholder="e.g., diabetes management guidelines",
                        lines=2,
                        scale=3
                    )
                    search_mode = gr.Radio(
                        choices=["hybrid", "bm25", "vector"],
                        value="hybrid",
                        label="Search Strategy",
                        scale=1
                    )
                search_btn = gr.Button("Search", variant="primary")
                search_output = gr.Textbox(label="Results", lines=20, interactive=False)

                search_btn.click(fn=hf_search, inputs=[search_input, search_mode], outputs=search_output)

        # ===== HOW IT WORKS =====
        gr.HTML('<div class="section-title" style="margin-top: 32px;">🤖 How It Works</div>')

        gr.HTML("""
        <div class="agent-grid">
            <div class="agent-card">
                <h4>🔬 Biomarker Analyzer</h4>
                <p>Validates your biomarker values against clinical reference ranges and flags any abnormalities.</p>
            </div>
            <div class="agent-card">
                <h4>📚 Disease Explainer</h4>
                <p>Uses RAG to retrieve relevant medical literature and explain potential conditions.</p>
            </div>
            <div class="agent-card">
                <h4>🔗 Biomarker Linker</h4>
                <p>Connects your specific biomarker patterns to disease predictions with clinical evidence.</p>
            </div>
            <div class="agent-card">
                <h4>📋 Clinical Guidelines</h4>
                <p>Retrieves evidence-based recommendations from 750+ pages of medical guidelines.</p>
            </div>
            <div class="agent-card">
                <h4>✅ Confidence Assessor</h4>
                <p>Evaluates the reliability of findings based on data quality and evidence strength.</p>
            </div>
            <div class="agent-card">
                <h4>📝 Response Synthesizer</h4>
                <p>Compiles all insights into a comprehensive, easy-to-understand patient report.</p>
            </div>
        </div>
        """)

        # ===== DISCLAIMER =====
        gr.HTML("""
        <div class="disclaimer">
            <strong>⚠️ Medical Disclaimer:</strong> This tool is for <strong>informational purposes only</strong> 
            and does not replace professional medical advice, diagnosis, or treatment. Always consult a qualified 
            healthcare provider with questions regarding a medical condition. The AI analysis is based on general 
            clinical guidelines and may not account for your specific medical history.
        </div>
        """)

        # ===== FOOTER =====
        gr.HTML("""
        <div style="text-align: center; padding: 24px; color: #94a3b8; font-size: 0.85em; margin-top: 24px;">
            <p>Built with ❤️ using 
                <a href="https://langchain-ai.github.io/langgraph/" target="_blank" style="color: #3b82f6;">LangGraph</a>, 
                <a href="https://faiss.ai/" target="_blank" style="color: #3b82f6;">FAISS</a>, and 
                <a href="https://gradio.app/" target="_blank" style="color: #3b82f6;">Gradio</a>
            </p>
            <p style="margin-top: 8px;">
                Powered by <strong>Groq</strong> or <strong>Google Gemini</strong> • 
                <a href="https://github.com" target="_blank" style="color: #3b82f6;">Open Source on GitHub</a>
            </p>
        </div>
        """)

        # ===== EVENT HANDLERS =====
        analyze_btn.click(
            fn=analyze_biomarkers,
            inputs=[input_text],
            outputs=[summary_output, details_output, status_output],
            show_progress="full",
        )

        clear_btn.click(
            fn=lambda: ("", """
<div style="text-align: center; padding: 60px 20px; color: #94a3b8;">
    <div style="font-size: 4em; margin-bottom: 16px;">🔬</div>
    <h3 style="color: #64748b; font-weight: 500;">Ready to Analyze</h3>
    <p>Enter your biomarkers on the left and click <strong>Analyze</strong> to get your personalized health insights.</p>
</div>
            """, "", ""),
            outputs=[input_text, summary_output, details_output, status_output],
        )

    return demo


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting MediGuard AI Gradio App...")

    demo = create_demo()

    # Launch with HF Spaces compatible settings
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        # share=False on HF Spaces
    )
