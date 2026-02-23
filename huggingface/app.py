"""
MediGuard AI — Hugging Face Spaces Gradio App

Standalone deployment that uses:
- FAISS vector store (local)
- Cloud LLMs (Groq or Gemini - FREE tiers)
- No external services required
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional

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
# Configuration
# ---------------------------------------------------------------------------

def get_api_keys():
    """Get API keys dynamically (HuggingFace injects secrets after module load)."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    google_key = os.getenv("GOOGLE_API_KEY", "")
    return groq_key, google_key


def setup_llm_provider():
    """Set LLM provider based on available keys."""
    groq_key, google_key = get_api_keys()
    
    if groq_key:
        os.environ["LLM_PROVIDER"] = "groq"
        os.environ["GROQ_API_KEY"] = groq_key  # Ensure it's set
        return "groq"
    elif google_key:
        os.environ["LLM_PROVIDER"] = "gemini"
        os.environ["GOOGLE_API_KEY"] = google_key
        return "gemini"
    return None


# Log status at startup (keys may not be available yet)
_groq, _google = get_api_keys()
if not _groq and not _google:
    logger.warning(
        "No LLM API key found at startup. Will check again when analyzing."
    )


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
        logger.info(f"LLM_PROVIDER={os.getenv('LLM_PROVIDER')}")
        logger.info(f"GROQ_API_KEY={'set' if os.getenv('GROQ_API_KEY') else 'NOT SET'}")
        logger.info(f"GOOGLE_API_KEY={'set' if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")
        
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
# Analysis Functions
# ---------------------------------------------------------------------------

def parse_biomarkers(text: str) -> dict[str, float]:
    """
    Parse biomarkers from natural language text.
    
    Supports formats like:
    - "Glucose: 140, HbA1c: 7.5"
    - "glucose 140 hba1c 7.5"
    - {"Glucose": 140, "HbA1c": 7.5}
    """
    text = text.strip()
    
    # Try JSON first
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Parse natural language
    import re
    
    # Common biomarker patterns
    patterns = [
        # "Glucose: 140" or "Glucose = 140"
        r"([A-Za-z0-9_]+)\s*[:=]\s*([\d.]+)",
        # "Glucose 140 mg/dL"
        r"([A-Za-z0-9_]+)\s+([\d.]+)\s*(?:mg/dL|mmol/L|%|g/dL|U/L|mIU/L)?",
    ]
    
    biomarkers = {}
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for name, value in matches:
            try:
                biomarkers[name.strip()] = float(value)
            except ValueError:
                continue
    
    return biomarkers


def analyze_biomarkers(input_text: str, progress=gr.Progress()) -> tuple[str, str, str]:
    """
    Analyze biomarkers using the Clinical Insight Guild.
    
    Returns: (summary, details_json, status)
    """
    if not input_text.strip():
        return "", "", "⚠️ Please enter biomarkers to analyze."
    
    # Check API key dynamically (HF injects secrets after startup)
    groq_key, google_key = get_api_keys()
    
    if not groq_key and not google_key:
        return "", "", (
            "❌ **Error**: No LLM API key configured.\n\n"
            "Please add your API key in Hugging Face Space Settings → Secrets:\n"
            "- `GROQ_API_KEY` (get free at https://console.groq.com/keys)\n"
            "- or `GOOGLE_API_KEY` (get free at https://aistudio.google.com/app/apikey)"
        )
    
    # Setup provider based on available key
    provider = setup_llm_provider()
    logger.info(f"Using LLM provider: {provider}")
    
    try:
        progress(0.1, desc="Parsing biomarkers...")
        biomarkers = parse_biomarkers(input_text)
        
        if not biomarkers:
            return "", "", (
                "⚠️ Could not parse biomarkers. Try formats like:\n"
                "• `Glucose: 140, HbA1c: 7.5`\n"
                "• `{\"Glucose\": 140, \"HbA1c\": 7.5}`"
            )
        
        progress(0.2, desc="Initializing analysis...")
        
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
        
        progress(0.4, desc="Running Clinical Insight Guild...")
        
        # Run analysis
        start = time.time()
        result = guild.run(patient_input)
        elapsed = time.time() - start
        
        progress(0.9, desc="Formatting results...")
        
        # Extract response
        final_response = result.get("final_response", {})
        
        # Format summary
        summary = format_summary(final_response, elapsed)
        
        # Format details
        details = json.dumps(final_response, indent=2, default=str)
        
        status = f"✅ Analysis completed in {elapsed:.1f}s"
        
        return summary, details, status
        
    except Exception as exc:
        logger.error(f"Analysis error: {exc}", exc_info=True)
        return "", "", f"❌ **Error**: {exc}\n\n```\n{traceback.format_exc()}\n```"


def auto_predict(biomarkers: dict[str, float]) -> dict[str, Any]:
    """
    Auto-generate a disease prediction based on biomarkers.
    This simulates what an ML model would provide.
    """
    # Normalize biomarker names for matching
    normalized = {k.lower().replace(" ", ""): v for k, v in biomarkers.items()}
    
    # Check for diabetes indicators
    glucose = normalized.get("glucose", normalized.get("fastingglucose", 0))
    hba1c = normalized.get("hba1c", normalized.get("hemoglobina1c", 0))
    
    if hba1c >= 6.5 or glucose >= 126:
        return {
            "disease": "Diabetes",
            "confidence": min(0.95, 0.7 + (hba1c - 6.5) * 0.1) if hba1c else 0.85,
            "severity": "high" if hba1c >= 8 or glucose >= 200 else "moderate"
        }
    
    # Check for lipid disorders
    cholesterol = normalized.get("cholesterol", normalized.get("totalcholesterol", 0))
    ldl = normalized.get("ldl", normalized.get("ldlcholesterol", 0))
    triglycerides = normalized.get("triglycerides", 0)
    
    if cholesterol >= 240 or ldl >= 160 or triglycerides >= 200:
        return {
            "disease": "Dyslipidemia",
            "confidence": 0.85,
            "severity": "moderate"
        }
    
    # Check for anemia
    hemoglobin = normalized.get("hemoglobin", normalized.get("hgb", normalized.get("hb", 0)))
    
    if hemoglobin and hemoglobin < 12:
        return {
            "disease": "Anemia",
            "confidence": 0.80,
            "severity": "moderate"
        }
    
    # Check for thyroid issues
    tsh = normalized.get("tsh", 0)
    
    if tsh > 4.5:
        return {
            "disease": "Hypothyroidism",
            "confidence": 0.75,
            "severity": "moderate"
        }
    elif tsh and tsh < 0.4:
        return {
            "disease": "Hyperthyroidism",
            "confidence": 0.75,
            "severity": "moderate"
        }
    
    # Default - general health screening
    return {
        "disease": "General Health Screening",
        "confidence": 0.70,
        "severity": "low"
    }


def format_summary(response: dict, elapsed: float) -> str:
    """Format the analysis response as readable markdown."""
    if not response:
        return "No analysis results available."
    
    parts = []
    
    # Header
    primary = response.get("primary_finding", "Analysis")
    confidence = response.get("confidence", {})
    conf_score = confidence.get("overall_score", 0) if isinstance(confidence, dict) else 0
    
    parts.append(f"## 🏥 {primary}")
    if conf_score:
        parts.append(f"**Confidence**: {conf_score:.0%}")
    parts.append("")
    
    # Critical Alerts
    alerts = response.get("safety_alerts", [])
    if alerts:
        parts.append("### ⚠️ Critical Alerts")
        for alert in alerts[:5]:
            if isinstance(alert, dict):
                parts.append(f"- **{alert.get('alert_type', 'Alert')}**: {alert.get('message', '')}")
            else:
                parts.append(f"- {alert}")
        parts.append("")
    
    # Key Findings
    findings = response.get("key_findings", [])
    if findings:
        parts.append("### 🔍 Key Findings")
        for finding in findings[:5]:
            parts.append(f"- {finding}")
        parts.append("")
    
    # Biomarker Flags
    flags = response.get("biomarker_flags", [])
    if flags:
        parts.append("### 📊 Biomarker Analysis")
        for flag in flags[:8]:
            if isinstance(flag, dict):
                name = flag.get("biomarker", "Unknown")
                status = flag.get("status", "normal")
                value = flag.get("value", "N/A")
                emoji = "🔴" if status == "critical" else "🟡" if status == "abnormal" else "🟢"
                parts.append(f"- {emoji} **{name}**: {value} ({status})")
            else:
                parts.append(f"- {flag}")
        parts.append("")
    
    # Recommendations
    recs = response.get("recommendations", {})
    if recs:
        parts.append("### 💡 Recommendations")
        
        immediate = recs.get("immediate_actions", [])
        if immediate:
            parts.append("**Immediate Actions:**")
            for action in immediate[:3]:
                parts.append(f"- {action}")
        
        lifestyle = recs.get("lifestyle_modifications", [])
        if lifestyle:
            parts.append("\n**Lifestyle Modifications:**")
            for mod in lifestyle[:3]:
                parts.append(f"- {mod}")
        
        followup = recs.get("follow_up", [])
        if followup:
            parts.append("\n**Follow-up:**")
            for item in followup[:3]:
                parts.append(f"- {item}")
        parts.append("")
    
    # Disease Explanation
    explanation = response.get("disease_explanation", {})
    if explanation and isinstance(explanation, dict):
        parts.append("### 📖 Understanding Your Results")
        
        pathophys = explanation.get("pathophysiology", "")
        if pathophys:
            parts.append(f"{pathophys[:500]}...")
        parts.append("")
    
    # Conversational Summary
    conv_summary = response.get("conversational_summary", "")
    if conv_summary:
        parts.append("### 📝 Summary")
        parts.append(conv_summary[:1000])
        parts.append("")
    
    # Footer
    parts.append("---")
    parts.append(f"*Analysis completed in {elapsed:.1f}s using MediGuard AI*")
    parts.append("")
    parts.append("**⚠️ Disclaimer**: This is for informational purposes only. "
                 "Consult a healthcare professional for medical advice.")
    
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Gradio Interface
# ---------------------------------------------------------------------------

def create_demo() -> gr.Blocks:
    """Create the Gradio Blocks interface."""
    
    with gr.Blocks(
        title="MediGuard AI - Medical Biomarker Analysis",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="cyan"),
        css="""
        .gradio-container { max-width: 1200px !important; }
        .status-box { font-size: 14px; }
        footer { display: none !important; }
        """
    ) as demo:
        
        # Header
        gr.Markdown("""
        # 🏥 MediGuard AI — Medical Biomarker Analysis
        
        **Multi-Agent RAG System** powered by 6 specialized AI agents with medical knowledge retrieval.
        
        Enter your biomarkers below and get evidence-based insights in seconds.
        """)
        
        # API Key warning - always show since keys are checked dynamically
        # The actual check happens in analyze_biomarkers()
        gr.Markdown("""
        <div style="background: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0;">
        ℹ️ <b>Note</b>: Make sure you've added <code>GROQ_API_KEY</code> or <code>GOOGLE_API_KEY</code> 
        in Space Settings → Secrets for analysis to work.
        </div>
        """)
        
        with gr.Row():
            # Input column
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Enter Biomarkers")
                
                input_text = gr.Textbox(
                    label="Biomarkers",
                    placeholder=(
                        "Enter biomarkers in any format:\n"
                        "• Glucose: 140, HbA1c: 7.5, Cholesterol: 210\n"
                        "• My glucose is 140 and HbA1c is 7.5\n"
                        '• {"Glucose": 140, "HbA1c": 7.5}'
                    ),
                    lines=5,
                    max_lines=10,
                )
                
                with gr.Row():
                    analyze_btn = gr.Button("🔬 Analyze", variant="primary", size="lg")
                    clear_btn = gr.Button("🗑️ Clear", size="lg")
                
                status_output = gr.Markdown(
                    label="Status",
                    elem_classes="status-box"
                )
                
                # Example inputs
                gr.Markdown("### 📋 Example Inputs")
                
                examples = gr.Examples(
                    examples=[
                        ["Glucose: 185, HbA1c: 8.2, Cholesterol: 245, LDL: 165"],
                        ["Glucose: 95, HbA1c: 5.4, Cholesterol: 180, HDL: 55, LDL: 100"],
                        ["Hemoglobin: 9.5, Iron: 40, Ferritin: 15"],
                        ["TSH: 8.5, T4: 4.0, T3: 80"],
                        ['{"Glucose": 140, "HbA1c": 7.0, "Triglycerides": 250}'],
                    ],
                    inputs=input_text,
                    label="Click an example to load it",
                )
            
            # Output column
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Analysis Results")
                
                with gr.Tabs():
                    with gr.Tab("Summary"):
                        summary_output = gr.Markdown(
                            label="Analysis Summary",
                            value="*Enter biomarkers and click Analyze to see results*"
                        )
                    
                    with gr.Tab("Detailed JSON"):
                        details_output = gr.Code(
                            label="Full Response",
                            language="json",
                            lines=25,
                        )
        
        # Event handlers
        analyze_btn.click(
            fn=analyze_biomarkers,
            inputs=[input_text],
            outputs=[summary_output, details_output, status_output],
            show_progress="full",
        )
        
        clear_btn.click(
            fn=lambda: ("", "", "", ""),
            outputs=[input_text, summary_output, details_output, status_output],
        )
        
        # Footer
        gr.Markdown("""
        ---
        
        ### ℹ️ About MediGuard AI
        
        MediGuard AI uses a **Clinical Insight Guild** of 6 specialized AI agents:
        
        | Agent | Role |
        |-------|------|
        | 🔬 Biomarker Analyzer | Validates and flags abnormal values |
        | 📚 Disease Explainer | RAG-powered pathophysiology explanations |
        | 🔗 Biomarker Linker | Connects biomarkers to disease predictions |
        | 📋 Clinical Guidelines | Evidence-based recommendations from medical literature |
        | ✅ Confidence Assessor | Evaluates reliability of findings |
        | 📝 Response Synthesizer | Compiles comprehensive patient-friendly output |
        
        **Data Sources**: 750+ pages of clinical guidelines (FAISS vector store)
        
        ---
        
        ⚠️ **Medical Disclaimer**: This tool is for **informational purposes only** and does not 
        replace professional medical advice, diagnosis, or treatment. Always consult a qualified 
        healthcare provider with questions regarding a medical condition.
        
        ---
        
        Built with ❤️ using [LangGraph](https://langchain-ai.github.io/langgraph/), 
        [FAISS](https://faiss.ai/), and [Gradio](https://gradio.app/)
        """)
    
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
