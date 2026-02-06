# RagBot System Architecture

## Overview

RagBot is a Multi-Agent RAG (Retrieval-Augmented Generation) system for medical biomarker analysis. It combines large language models with a specialized medical knowledge base to provide evidence-based insights on patient biomarker readings.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  CLI Chat    │  │  REST API    │  │   Web UI     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼───────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │    Workflow Orchestrator            │
          │        (LangGraph)                  │
          └──────────────┬───────────────────────┘
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
  │  Extraction │  │   Analysis   │  │  Knowledge   │
  │   Agent     │  │   Agents     │  │  Retrieval   │
  └─────────────┘  └──────────────┘  └──────────────┘
      │                  │                  │
      └──────────────────┼──────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │    LLM Provider             │
          │    (Groq - LLaMA 3.3-70B)   │
          └──────────────┬───────────────┘
                         │
          ┌──────────────▼──────────────┐
          │    Medical Knowledge Base   │
          │    (FAISS Vector Store)     │
          │    (750 pages, 2,609 docs)  │
          └─────────────────────────────┘
```

## Core Components

### 1. **Biomarker Extraction & Validation** (`src/biomarker_validator.py`)
- Parses user input for blood test results
- Normalizes biomarker names to standard clinical terms
- Validates values against established reference ranges
- Generates safety alerts for critical values

### 2. **Multi-Agent Workflow** (`src/workflow.py` using LangGraph)
The system processes each patient case through 6 specialist agents:

#### Agent 1: Biomarker Analyzer
- Validates each biomarker against reference ranges
- Identifies out-of-range values
- Generates immediate clinical alerts
- Predicts disease relevance (baseline diagnostic)

#### Agent 2: Disease Explainer (RAG)
- Retrieves medical literature on predicted disease
- Explains pathophysiological mechanisms
- Provides evidence-based disease context
- Sources: medical PDFs (anemia, diabetes, heart disease, thrombocytopenia)

#### Agent 3: Biomarker-Disease Linker (RAG)
- Maps patient biomarkers to disease indicators
- Identifies key drivers of the predicted condition
- Retrieves lab-specific guidelines
- Explains biomarker significance in disease context

#### Agent 4: Clinical Guidelines Agent (RAG)
- Retrieves evidence-based clinical guidelines
- Provides immediate recommendations
- Suggests monitoring parameters
- Offers lifestyle and medication guidance

#### Agent 5: Confidence Assessor
- Evaluates prediction reliability
- Assesses evidence strength
- Identifies limitations in analysis
- Provides confidence score with reasoning

#### Agent 6: Response Synthesizer
- Consolidates findings from all agents
- Generates comprehensive patient summary
- Produces actionable recommendations
- Creates structured final report

### 3. **Knowledge Base** (`src/pdf_processor.py`)
- **Source**: 8 medical PDF documents (750 pages total)
- **Storage**: FAISS vector database (2,609 document chunks)
- **Embeddings**: HuggingFace sentence-transformers (free, local, offline)
- **Format**: Chunked with 1000 char overlap for context preservation

### 4. **LLM Configuration** (`src/llm_config.py`)
- **Primary LLM**: Groq LLaMA 3.3-70B
  - Fast inference (~1-2 sec per agent output)
  - Free API tier available
  - No rate limiting for reasonable usage
- **Embedding Model**: HuggingFace sentence-transformers/all-MiniLM-L6-v2
  - 384-dimensional embeddings
  - Fast similarity search
  - Runs locally (no API dependency)

## Data Flow

```
User Input
    ↓
[Extraction] → Normalized Biomarkers
    ↓
[Prediction] → Disease Hypothesis (85% confidence)
    ↓
[RAG Retrieval] → Medical Literature (5-10 relevant docs)
    ↓
[Analysis] → All 6 Agents Process in Parallel
    ↓
[Synthesis] → Comprehensive Report
    ↓
[Output] → Recommendations + Safety Alerts + Evidence
```

## Key Design Decisions

1. **Local Embeddings**: HuggingFace embeddings avoid API costs and work offline
2. **Groq LLM**: Free, fast inference for real-time interaction
3. **LangGraph**: Manages complex multi-agent workflows with state management
4. **FAISS**: Efficient similarity search on large medical document collection
5. **Modular Agents**: Each agent has clear responsibility, enabling parallel execution
6. **RAG Integration**: Medical knowledge grounds responses in evidence

## Technologies Used

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | LangGraph | Workflow management |
| LLM | Groq API | Fast inference |
| Embeddings | HuggingFace | Vector representations |
| Vector DB | FAISS | Similarity search |
| Data Validation | Pydantic V2 | Type safety & schemas |
| Async | Python asyncio | Parallel processing |
| REST API | FastAPI | Web interface |

## Performance Characteristics

- **Response Time**: 15-25 seconds (6 agents + RAG retrieval)
- **Knowledge Base Size**: 750 pages, 2,609 chunks
- **Embedding Dimensions**: 384
- **Inference Cost**: Free (local embeddings + Groq free tier)
- **Scalability**: Easily extends to more medical domains

## Extensibility

### Adding New Biomarkers
1. Update `config/biomarker_references.json` with reference ranges
2. Add to `scripts/normalize_biomarker_names()` mapping
3. Medical guidelines automatically handle via RAG

### Adding New Medical Domains
1. Add PDF documents to `data/medical_pdfs/`
2. Run `python scripts/setup_embeddings.py`
3. Vector store rebuilds automatically
4. Agents inherit new knowledge through RAG

### Custom Analysis Rules
1. Create new agent in `src/agents/`
2. Register in workflow graph (`src/workflow.py`)
3. Insert into processing pipeline

## Security & Privacy

- All processing runs locally
- No personal data sent to APIs (except LLM inference)
- Vector store derived from public medical PDFs
- Embeddings computed locally or cached
- Can operate completely offline after setup

---

For setup instructions, see [QUICKSTART.md](../QUICKSTART.md)
For API documentation, see [API.md](API.md)
For development guide, see [DEVELOPMENT.md](DEVELOPMENT.md)
