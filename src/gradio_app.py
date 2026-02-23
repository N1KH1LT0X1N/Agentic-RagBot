"""
MediGuard AI — Gradio Web UI

Provides a simple chat interface and biomarker analysis panel.
"""

from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

API_BASE = os.getenv("MEDIGUARD_API_URL", "http://localhost:8000")


def _call_ask(question: str) -> str:
    """Call the /ask endpoint."""
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{API_BASE}/ask", json={"question": question})
            resp.raise_for_status()
            return resp.json().get("answer", "No answer returned.")
    except Exception as exc:
        return f"Error: {exc}"


def _call_analyze(biomarkers_json: str) -> str:
    """Call the /analyze/structured endpoint."""
    try:
        biomarkers = json.loads(biomarkers_json)
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{API_BASE}/analyze/structured",
                json={"biomarkers": biomarkers},
            )
            resp.raise_for_status()
            data = resp.json()
            summary = data.get("conversational_summary") or json.dumps(data, indent=2)
            return summary
    except json.JSONDecodeError:
        return "Invalid JSON. Please enter biomarkers as: {\"Glucose\": 185, \"HbA1c\": 8.2}"
    except Exception as exc:
        return f"Error: {exc}"


def launch_gradio(share: bool = False) -> None:
    """Launch the Gradio interface."""
    try:
        import gradio as gr
    except ImportError:
        raise ImportError("gradio is required. Install: pip install gradio")

    with gr.Blocks(title="MediGuard AI", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏥 MediGuard AI — Medical Analysis")
        gr.Markdown(
            "**Disclaimer**: This tool is for informational purposes only and does not "
            "replace professional medical advice."
        )

        with gr.Tab("Ask a Question"):
            question_input = gr.Textbox(
                label="Medical Question",
                placeholder="e.g., What does a high HbA1c level indicate?",
                lines=3,
            )
            ask_btn = gr.Button("Ask", variant="primary")
            answer_output = gr.Textbox(label="Answer", lines=15, interactive=False)
            ask_btn.click(fn=_call_ask, inputs=question_input, outputs=answer_output)

        with gr.Tab("Analyze Biomarkers"):
            bio_input = gr.Textbox(
                label="Biomarkers (JSON)",
                placeholder='{"Glucose": 185, "HbA1c": 8.2, "Cholesterol": 210}',
                lines=5,
            )
            analyze_btn = gr.Button("Analyze", variant="primary")
            analysis_output = gr.Textbox(label="Analysis", lines=20, interactive=False)
            analyze_btn.click(fn=_call_analyze, inputs=bio_input, outputs=analysis_output)

        with gr.Tab("Search Knowledge Base"):
            search_input = gr.Textbox(
                label="Search Query",
                placeholder="e.g., diabetes management guidelines",
                lines=2,
            )
            search_btn = gr.Button("Search", variant="primary")
            search_output = gr.Textbox(label="Results", lines=15, interactive=False)

            def _call_search(query: str) -> str:
                try:
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.post(
                            f"{API_BASE}/search",
                            json={"query": query, "top_k": 5, "mode": "hybrid"},
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        results = data.get("results", [])
                        if not results:
                            return "No results found."
                        parts = []
                        for i, r in enumerate(results, 1):
                            parts.append(
                                f"**[{i}] {r.get('title', 'Untitled')}** (score: {r.get('score', 0):.3f})\n"
                                f"{r.get('text', '')}\n"
                            )
                        return "\n---\n".join(parts)
                except Exception as exc:
                    return f"Error: {exc}"

            search_btn.click(fn=_call_search, inputs=search_input, outputs=search_output)

    demo.launch(server_name="0.0.0.0", server_port=7860, share=share)


if __name__ == "__main__":
    launch_gradio()
