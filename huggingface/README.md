---
title: MediGuard AI
emoji: 🏥
colorFrom: blue
colorTo: cyan
sdk: docker
pinned: true
license: mit
app_port: 7860
models:
  - meta-llama/Llama-3.3-70B-Versatile
tags:
  - medical
  - biomarker
  - rag
  - healthcare
  - langgraph
  - agents
short_description: Multi-Agent RAG System for Medical Biomarker Analysis
---

# 🏥 MediGuard AI — Medical Biomarker Analysis

A production-ready **Multi-Agent RAG System** that analyzes blood test biomarkers using 6 specialized AI agents with medical knowledge retrieval.

## ✨ Features

- **6 Specialist AI Agents** — Biomarker validation, disease prediction, RAG-powered analysis, confidence assessment
- **Medical Knowledge Base** — 750+ pages of clinical guidelines (FAISS vector store)
- **Evidence-Based** — All recommendations backed by retrieved medical literature
- **Free Cloud LLMs** — Uses Groq (LLaMA 3.3-70B) or Google Gemini

## 🚀 Quick Start

1. **Enter your biomarkers** in any format:
   - `Glucose: 140, HbA1c: 7.5`
   - `My glucose is 140 and HbA1c is 7.5`
   - `{"Glucose": 140, "HbA1c": 7.5}`

2. **Click Analyze** and get:
   - Primary diagnosis with confidence score
   - Critical alerts and safety flags
   - Biomarker analysis with normal ranges
   - Evidence-based recommendations
   - Disease pathophysiology explanation

## 🔧 Configuration

This Space requires an LLM API key. Add one of these secrets in Space Settings:

| Secret | Provider | Get Free Key |
|--------|----------|--------------|
| `GROQ_API_KEY` | Groq (recommended) | [console.groq.com/keys](https://console.groq.com/keys) |
| `GOOGLE_API_KEY` | Google Gemini | [aistudio.google.com](https://aistudio.google.com/app/apikey) |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Clinical Insight Guild                 │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐  │
│  │           1. Biomarker Analyzer                    │  │
│  │     Validates values, flags abnormalities          │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                   │
│         ┌────────────┼────────────┐                     │
│         ▼            ▼            ▼                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │ Disease  │ │Biomarker │ │ Clinical │                │
│  │Explainer │ │ Linker   │ │Guidelines│                │
│  │  (RAG)   │ │          │ │  (RAG)   │                │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘                │
│       │            │            │                       │
│       └────────────┼────────────┘                       │
│                    ▼                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │          4. Confidence Assessor                    │  │
│  │     Evaluates reliability, assigns scores          │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      ▼                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │          5. Response Synthesizer                   │  │
│  │     Compiles patient-friendly summary              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 📊 Supported Biomarkers

| Category | Biomarkers |
|----------|------------|
| **Diabetes** | Glucose, HbA1c, Fasting Glucose, Insulin |
| **Lipids** | Cholesterol, LDL, HDL, Triglycerides |
| **Kidney** | Creatinine, BUN, eGFR |
| **Liver** | ALT, AST, Bilirubin, Albumin |
| **Thyroid** | TSH, T3, T4, Free T4 |
| **Blood** | Hemoglobin, WBC, RBC, Platelets |
| **Cardiac** | Troponin, BNP, CRP |

## ⚠️ Medical Disclaimer

This tool is for **informational purposes only** and does not replace professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider with questions regarding a medical condition.

## 📄 License

MIT License — See [GitHub Repository](https://github.com/yourusername/ragbot) for details.

## 🙏 Acknowledgments

Built with [LangGraph](https://langchain-ai.github.io/langgraph/), [FAISS](https://faiss.ai/), [Gradio](https://gradio.app/), and [Groq](https://groq.com/).
