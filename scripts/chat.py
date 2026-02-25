"""
MediGuard AI RAG-Helper - Interactive CLI Chatbot
Enables natural language conversation with the RAG system
"""

import json
import logging
import os
import sys
import warnings

# ── Silence HuggingFace / transformers noise BEFORE any ML library is loaded ──
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*class.*HuggingFaceEmbeddings.*was deprecated.*")
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime
from pathlib import Path
from typing import Any

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    os.system('chcp 65001 > nul 2>&1')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.prompts import ChatPromptTemplate

from src.biomarker_normalization import normalize_biomarker_name
from src.llm_config import get_chat_model
from src.state import PatientInput
from src.workflow import create_guild

# ============================================================================
# BIOMARKER EXTRACTION PROMPT
# ============================================================================

BIOMARKER_EXTRACTION_PROMPT = """You are a medical data extraction assistant. 
Extract biomarker values from the user's message.

Known biomarkers (24 total):
Glucose, Cholesterol, Triglycerides, HbA1c, LDL, HDL, Insulin, BMI,
Hemoglobin, Platelets, WBC (White Blood Cells), RBC (Red Blood Cells), 
Hematocrit, MCV, MCH, MCHC, Heart Rate, Systolic BP, Diastolic BP, 
Troponin, C-reactive Protein, ALT, AST, Creatinine

User message: {user_message}

Extract all biomarker names and their values. Return ONLY valid JSON (no other text):
{{
  "biomarkers": {{
    "Glucose": 140,
    "HbA1c": 7.5
  }},
  "patient_context": {{
    "age": null,
    "gender": null,
    "bmi": null
  }}
}}

If you cannot find any biomarkers, return {{"biomarkers": {{}}, "patient_context": {{}}}}.
"""


# ============================================================================
# Component 1: Biomarker Extraction
# ============================================================================

def _parse_llm_json(content: str) -> dict[str, Any]:
    """Parse JSON payload from LLM output with fallback recovery."""
    text = content.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        left = text.find("{")
        right = text.rfind("}")
        if left != -1 and right != -1 and right > left:
            return json.loads(text[left:right + 1])
        raise


def extract_biomarkers(user_message: str) -> tuple[dict[str, float], dict[str, Any]]:
    """
    Extract biomarker values from natural language using LLM.
    
    Returns:
        Tuple of (biomarkers_dict, patient_context_dict)
    """
    try:
        llm = get_chat_model(temperature=0.0)
        prompt = ChatPromptTemplate.from_template(BIOMARKER_EXTRACTION_PROMPT)

        chain = prompt | llm
        response = chain.invoke({"user_message": user_message})

        # Parse JSON from LLM response
        content = response.content.strip()

        extracted = _parse_llm_json(content)
        biomarkers = extracted.get("biomarkers", {})
        patient_context = extracted.get("patient_context", {})

        # Normalize biomarker names
        normalized = {}
        for key, value in biomarkers.items():
            try:
                standard_name = normalize_biomarker_name(key)
                normalized[standard_name] = float(value)
            except (ValueError, TypeError) as e:
                print(f"⚠️ Skipping invalid value for {key}: {value} (error: {e})")
                continue

        # Clean up patient context (remove null values)
        patient_context = {k: v for k, v in patient_context.items() if v is not None}

        return normalized, patient_context

    except Exception as e:
        print(f"⚠️ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}


# ============================================================================
# Component 2: Disease Prediction
# ============================================================================

def predict_disease_simple(biomarkers: dict[str, float]) -> dict[str, Any]:
    """
    Simple rule-based disease prediction based on key biomarkers.
    """
    scores = {
        "Diabetes": 0.0,
        "Anemia": 0.0,
        "Heart Disease": 0.0,
        "Thrombocytopenia": 0.0,
        "Thalassemia": 0.0
    }

    # Helper: check both abbreviated and normalized biomarker names
    # Returns None when biomarker is not present (avoids false triggers)
    def _get(name, *alt_names):
        val = biomarkers.get(name)
        if val is not None:
            return val
        for alt in alt_names:
            val = biomarkers.get(alt)
            if val is not None:
                return val
        return None

    # Diabetes indicators
    glucose = _get("Glucose")
    hba1c = _get("HbA1c")
    if glucose is not None and glucose > 126:
        scores["Diabetes"] += 0.4
    if glucose is not None and glucose > 180:
        scores["Diabetes"] += 0.2
    if hba1c is not None and hba1c >= 6.5:
        scores["Diabetes"] += 0.5

    # Anemia indicators
    hemoglobin = _get("Hemoglobin")
    mcv = _get("Mean Corpuscular Volume", "MCV")
    if hemoglobin is not None and hemoglobin < 12.0:
        scores["Anemia"] += 0.6
    if hemoglobin is not None and hemoglobin < 10.0:
        scores["Anemia"] += 0.2
    if mcv is not None and mcv < 80:
        scores["Anemia"] += 0.2

    # Heart disease indicators
    cholesterol = _get("Cholesterol")
    troponin = _get("Troponin")
    ldl = _get("LDL Cholesterol", "LDL")
    if cholesterol is not None and cholesterol > 240:
        scores["Heart Disease"] += 0.3
    if troponin is not None and troponin > 0.04:
        scores["Heart Disease"] += 0.6
    if ldl is not None and ldl > 190:
        scores["Heart Disease"] += 0.2

    # Thrombocytopenia indicators
    platelets = _get("Platelets")
    if platelets is not None and platelets < 150000:
        scores["Thrombocytopenia"] += 0.6
    if platelets is not None and platelets < 50000:
        scores["Thrombocytopenia"] += 0.3

    # Thalassemia indicators (complex, simplified here)
    if mcv is not None and hemoglobin is not None and mcv < 80 and hemoglobin < 12.0:
        scores["Thalassemia"] += 0.4

    # Find top prediction
    top_disease = max(scores, key=scores.get)
    confidence = min(scores[top_disease], 1.0)  # Cap at 1.0 for Pydantic validation

    if confidence == 0.0:
        top_disease = "Undetermined"

    # Normalize probabilities to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        probabilities = {k: v / total for k, v in scores.items()}
    else:
        probabilities = {k: 1.0 / len(scores) for k in scores}

    return {
        "disease": top_disease,
        "confidence": confidence,
        "probabilities": probabilities
    }


def predict_disease_llm(biomarkers: dict[str, float], patient_context: dict) -> dict[str, Any]:
    """
    Use LLM to predict most likely disease based on biomarker pattern.
    Falls back to rule-based if LLM fails.
    """
    try:
        llm = get_chat_model(temperature=0.0)

        prompt = f"""You are a medical AI assistant. Based on these biomarker values, 
predict the most likely disease from: Diabetes, Anemia, Heart Disease, Thrombocytopenia, Thalassemia.

Biomarkers:
{json.dumps(biomarkers, indent=2)}

Patient Context:
{json.dumps(patient_context, indent=2)}

Return ONLY valid JSON (no other text):
{{
  "disease": "Disease Name",
  "confidence": 0.85,
  "probabilities": {{
    "Diabetes": 0.85,
    "Anemia": 0.08,
    "Heart Disease": 0.04,
    "Thrombocytopenia": 0.02,
    "Thalassemia": 0.01
  }}
}}
"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        prediction = _parse_llm_json(content)

        # Validate required fields
        if "disease" in prediction and "confidence" in prediction and "probabilities" in prediction:
            return prediction
        else:
            raise ValueError("Invalid prediction format")

    except Exception as e:
        print(f"⚠️ LLM prediction failed ({e}), using rule-based fallback")
        import traceback
        traceback.print_exc()
        return predict_disease_simple(biomarkers)


# ============================================================================
# Component 3: Conversational Formatter
# ============================================================================

def _coerce_to_dict(obj) -> dict:
    """Convert a Pydantic model or arbitrary object to a plain dict."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return {}


def format_conversational(result: dict[str, Any], user_name: str = "there") -> str:
    """
    Format technical JSON output into conversational response.
    """
    if not isinstance(result, dict):
        result = {}

    # Extract key information
    summary = result.get("patient_summary", {}) or {}
    prediction = result.get("prediction_explanation", {}) or {}
    recommendations = result.get("clinical_recommendations", {}) or {}
    confidence = result.get("confidence_assessment", {}) or {}
    # Normalize: items may be Pydantic SafetyAlert objects or plain dicts
    alerts = [_coerce_to_dict(a) for a in (result.get("safety_alerts") or [])]

    disease = prediction.get("primary_disease", "Unknown")
    conf_score = prediction.get("confidence", 0.0)

    # Build conversational response
    response = []

    # 1. Greeting and main finding
    response.append(f"Hi {user_name}! 👋\n")
    response.append("Based on your biomarkers, I analyzed your results.\n")

    # 2. Primary diagnosis with confidence
    emoji = "🔴" if conf_score >= 0.8 else "🟡" if conf_score >= 0.6 else "🟢"
    response.append(f"{emoji} **Primary Finding:** {disease}")
    response.append(f"   Confidence: {conf_score:.0%}\n")

    # 3. Critical safety alerts (if any)
    critical_alerts = [a for a in alerts if a.get("severity") == "CRITICAL"]
    if critical_alerts:
        response.append("⚠️ **IMPORTANT SAFETY ALERTS:**")
        for alert in critical_alerts[:3]:  # Show top 3
            response.append(f"   • {alert.get('biomarker', 'Unknown')}: {alert.get('message', '')}")
            response.append(f"     → {alert.get('action', 'Consult healthcare provider')}")
        response.append("")

    # 4. Key drivers explanation
    key_drivers = prediction.get("key_drivers", [])
    if key_drivers:
        response.append("🔍 **Why this prediction?**")
        for driver in key_drivers[:3]:  # Top 3 drivers
            biomarker = driver.get("biomarker", "")
            value = driver.get("value", "")
            explanation = driver.get("explanation", "")
            # Truncate long explanations
            if len(explanation) > 150:
                explanation = explanation[:147] + "..."
            response.append(f"   • **{biomarker}** ({value}): {explanation}")
        response.append("")

    # 5. What to do next (immediate actions)
    immediate = recommendations.get("immediate_actions", [])
    if immediate:
        response.append("✅ **What You Should Do:**")
        for i, action in enumerate(immediate[:3], 1):
            response.append(f"   {i}. {action}")
        response.append("")

    # 6. Lifestyle recommendations
    lifestyle = recommendations.get("lifestyle_changes", [])
    if lifestyle:
        response.append("🌱 **Lifestyle Recommendations:**")
        for i, change in enumerate(lifestyle[:3], 1):
            response.append(f"   {i}. {change}")
        response.append("")

    # 7. Disclaimer
    response.append("ℹ️ **Important:** This is an AI-assisted analysis, NOT medical advice.")
    response.append("   Please consult a healthcare professional for proper diagnosis and treatment.\n")

    return "\n".join(response)


# ============================================================================
# Component 4: Helper Functions
# ============================================================================

def print_biomarker_help():
    """Print list of supported biomarkers"""
    print("\n📋 Supported Biomarkers (24 total):")
    print("\n🩸 Blood Cells:")
    print("  • Hemoglobin, Platelets, WBC, RBC, Hematocrit, MCV, MCH, MCHC")
    print("\n🔬 Metabolic:")
    print("  • Glucose, Cholesterol, Triglycerides, HbA1c, LDL, HDL, Insulin, BMI")
    print("\n❤️ Cardiovascular:")
    print("  • Heart Rate, Systolic BP, Diastolic BP, Troponin, C-reactive Protein")
    print("\n🏥 Organ Function:")
    print("  • ALT, AST, Creatinine")
    print("\nExample: 'My glucose is 140, HbA1c is 7.5, cholesterol is 220'\n")


def run_example_case(guild):
    """Run example diabetes patient case"""
    print("\n📋 Running Example: Type 2 Diabetes Patient")
    print("   52-year-old male with elevated glucose and HbA1c\n")

    example_biomarkers = {
        "Glucose": 185.0,
        "HbA1c": 8.2,
        "Cholesterol": 235.0,
        "Triglycerides": 210.0,
        "HDL Cholesterol": 38.0,
        "LDL Cholesterol": 160.0,
        "Hemoglobin": 13.5,
        "Platelets": 220000,
        "White Blood Cells": 7500,
        "Systolic Blood Pressure": 145,
        "Diastolic Blood Pressure": 92
    }

    prediction = {
        "disease": "Diabetes",
        "confidence": 0.87,
        "probabilities": {
            "Diabetes": 0.87,
            "Heart Disease": 0.08,
            "Anemia": 0.03,
            "Thrombocytopenia": 0.01,
            "Thalassemia": 0.01
        }
    }

    patient_input = PatientInput(
        biomarkers=example_biomarkers,
        model_prediction=prediction,
        patient_context={"age": 52, "gender": "male", "bmi": 31.2}
    )

    print("🔄 Running analysis...\n")
    result = guild.run(patient_input)

    response = format_conversational(result.get("final_response", result), "there")
    print("\n" + "="*70)
    print("🤖 RAG-BOT:")
    print("="*70)
    print(response)
    print("="*70 + "\n")


def save_report(result: dict, biomarkers: dict):
    """Save detailed JSON report to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # final_response is already a plain dict built by the synthesizer
    final = result.get("final_response") or {}
    disease = (
        final.get("prediction_explanation", {}).get("primary_disease")
        or result.get("model_prediction", {}).get("disease", "unknown")
    )
    disease_safe = disease.replace(' ', '_').replace('/', '_')
    filename = f"report_{disease_safe}_{timestamp}.json"

    output_dir = Path("data/chat_reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename

    def _to_dict(obj):
        """Recursively convert Pydantic models / non-serializable objects."""
        if isinstance(obj, dict):
            return {k: _to_dict(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_dict(i) for i in obj]
        if hasattr(obj, "model_dump"):          # Pydantic v2
            return _to_dict(obj.model_dump())
        if hasattr(obj, "dict"):                # Pydantic v1
            return _to_dict(obj.dict())
        # Scalars and other primitives are returned as-is
        return obj

    report = {
        "timestamp": timestamp,
        "biomarkers_input": biomarkers,
        "final_response": _to_dict(final),
        "biomarker_flags": _to_dict(result.get("biomarker_flags", [])),
        "safety_alerts": _to_dict(result.get("safety_alerts", [])),
    }

    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✅ Report saved to: {filepath}\n")


# ============================================================================
# Main Chat Interface
# ============================================================================

def chat_interface():
    """
    Main interactive CLI chatbot for MediGuard AI RAG-Helper.
    """
    # Print welcome banner
    print("\n" + "="*70)
    print("🤖 MediGuard AI RAG-Helper - Interactive Chat")
    print("="*70)
    print("\nWelcome! I can help you understand your blood test results.\n")
    print("You can:")
    print("  1. Describe your biomarkers (e.g., 'My glucose is 140, HbA1c is 7.5')")
    print("  2. Type 'example' to see a sample diabetes case")
    print("  3. Type 'help' for biomarker list")
    print("  4. Type 'quit' to exit\n")
    print("="*70 + "\n")

    # Initialize guild (one-time setup)
    print("🔧 Initializing medical knowledge system...")
    try:
        guild = create_guild()
        print("✅ System ready!\n")
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        print("\nMake sure:")
        print("  • API key is set in .env (GROQ_API_KEY or GOOGLE_API_KEY)")
        print("  • Vector store exists (run: python scripts/setup_embeddings.py)")
        print("  • Internet connection is available for cloud LLM")
        return

    # Main conversation loop
    conversation_history = []
    user_name = "there"

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thank you for using MediGuard AI. Stay healthy!")
                break

            if user_input.lower() == 'help':
                print_biomarker_help()
                continue

            if user_input.lower() == 'example':
                run_example_case(guild)
                continue

            # Extract biomarkers from natural language
            print("\n🔍 Analyzing your input...")
            biomarkers, patient_context = extract_biomarkers(user_input)

            if not biomarkers:
                print("❌ I couldn't find any biomarker values in your message.")
                print("   Try: 'My glucose is 140 and HbA1c is 7.5'")
                print("   Or type 'help' to see all biomarkers I can analyze.\n")
                continue

            print(f"✅ Found {len(biomarkers)} biomarker(s): {', '.join(biomarkers.keys())}")

            # Check if we have enough biomarkers (minimum 2)
            if len(biomarkers) < 2:
                print("⚠️ I need at least 2 biomarkers for a reliable analysis.")
                print("   Can you provide more values?\n")
                continue

            # Generate disease prediction
            print("🧠 Predicting likely condition...")
            prediction = predict_disease_llm(biomarkers, patient_context)
            print(f"✅ Predicted: {prediction['disease']} ({prediction['confidence']:.0%} confidence)")

            # Create PatientInput
            patient_input = PatientInput(
                biomarkers=biomarkers,
                model_prediction=prediction,
                patient_context=patient_context if patient_context else {"source": "chat"}
            )

            # Run full RAG workflow
            print("📚 Consulting medical knowledge base...")
            print("   (This may take 15-25 seconds...)\n")

            result = guild.run(patient_input)

            # Format conversational response
            response = format_conversational(result.get("final_response", result), user_name)

            # Display response
            print("\n" + "="*70)
            print("🤖 RAG-BOT:")
            print("="*70)
            print(response)
            print("="*70 + "\n")

            # Save to history
            conversation_history.append({
                "user_input": user_input,
                "biomarkers": biomarkers,
                "prediction": prediction,
                "result": result
            })

            # Ask if user wants to save report
            save_choice = input("💾 Save detailed report to file? (y/n): ").strip().lower()
            if save_choice == 'y':
                save_report(result, biomarkers)

            print("\nYou can:")
            print("  • Enter more biomarkers for a new analysis")
            print("  • Type 'quit' to exit\n")

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Thank you for using MediGuard AI!")
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"\n❌ Analysis failed: {e}")
            print("\nThis might be due to:")
            print("  • API key not configured (check .env file)")
            print("  • Insufficient system memory")
            print("  • Invalid biomarker values")
            print("\nTry again or type 'quit' to exit.\n")
            continue


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    try:
        chat_interface()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("Please check your setup and try again.")
        sys.exit(1)
