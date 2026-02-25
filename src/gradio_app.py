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


def ask_stream(question: str, history: list, model: str):
    """Call the /ask/stream endpoint."""
    history = history or []
    if not question.strip():
        yield "", history
        return

    history.append((question, ""))

    try:
        with httpx.stream("POST", f"{API_BASE}/ask/stream", json={"question": question}, timeout=60.0) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    content = line[6:]
                    if content == "[DONE]":
                        break
                    try:
                        data = json.loads(content)
                        current_bot_msg = history[-1][1] + data.get("text", "")
                        history[-1] = (question, current_bot_msg)
                        yield "", history
                    except Exception as trace_exc:
                        logger.debug("Failed to parse streaming chunk: %s", trace_exc)
    except Exception as exc:
        history[-1] = (question, f"Error: {exc}")
        yield "", history


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


def launch_gradio(share: bool = False, server_port: int = 7860) -> None:
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
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(label="Medical Q&A History", height=400)
                    question_input = gr.Textbox(
                        label="Medical Question",
                        placeholder="e.g., What does a high HbA1c level indicate?",
                        lines=2,
                    )
                    with gr.Row():
                        ask_btn = gr.Button("Ask (Streaming)", variant="primary")
                        clear_btn = gr.Button("Clear History")

                with gr.Column(scale=1):
                    model_selector = gr.Dropdown(
                        choices=["llama-3.3-70b-versatile", "gemini-2.0-flash", "llama3.1:8b"],
                        value="llama-3.3-70b-versatile",
                        label="LLM Provider/Model"
                    )

            ask_btn.click(fn=ask_stream, inputs=[question_input, chatbot, model_selector], outputs=[question_input, chatbot])
            clear_btn.click(fn=lambda: ([], ""), outputs=[chatbot, question_input])

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
            search_output = gr.Textbox(label="Results", lines=15, interactive=False)

            def _call_search(query: str, mode: str) -> str:
                try:
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.post(
                            f"{API_BASE}/search",
                            json={"query": query, "top_k": 5, "mode": mode},
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

            search_btn.click(fn=_call_search, inputs=[search_input, search_mode], outputs=search_output)

    demo.launch(server_name="0.0.0.0", server_port=server_port, share=share)


if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_PORT", 7860))
    launch_gradio(server_port=port)
