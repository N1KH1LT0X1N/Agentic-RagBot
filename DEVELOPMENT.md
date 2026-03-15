# Development Guide

## Overview

MediGuard AI is a medical biomarker analysis system that uses agentic RAG (Retrieval-Augmented Generation) and multi-agent workflows to provide clinical insights.

## Project Structure

```
Agentic-RagBot/
├── src/
│   ├── agents/           # Agent implementations (biomarker_analyzer, disease_explainer, etc.)
│   ├── services/         # Core services (retrieval, embeddings, opensearch, etc.)
│   ├── routers/          # FastAPI route handlers
│   ├── models/           # Data models
│   ├── schemas/          # Pydantic schemas
│   ├── state.py          # State management
│   ├── workflow.py       # Workflow orchestration
│   ├── main.py           # FastAPI application factory
│   └── settings.py       # Configuration management
├── tests/                # Test suite
├── data/                 # Data files (vector stores, etc.)
└── docs/                 # Documentation
```

## Development Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables**:
   - Copy `.env.example` to `.env` and configure
   - Key variables:
     - `API__HOST`: Server host (default: 127.0.0.1)
     - `API__PORT`: Server port (default: 8000)
     - `GRADIO_SERVER_NAME`: Gradio host (default: 127.0.0.1)
     - `GRADIO_PORT`: Gradio port (default: 7860)

3. **Running the application**:
   ```bash
   # FastAPI server
   python -m src.main
   
   # Gradio interface
   python -m src.gradio_app
   ```

## Code Quality

### Linting
```bash
# Check code quality
ruff check src/

# Auto-fix issues
ruff check src/ --fix
```

### Security
```bash
# Run security scan
bandit -r src/
```

### Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_agents.py -v
```

## Testing Guidelines

1. **Test structure**:
   - Unit tests for individual components
   - Integration tests for workflows
   - Mock external dependencies (LLMs, databases)

2. **Test coverage**:
   - Current coverage: 58%
   - Target: 70%+
   - Focus on critical paths and business logic

3. **Best practices**:
   - Use descriptive test names
   - Mock external services
   - Test both success and failure cases
   - Keep tests isolated and independent

## Architecture

### Multi-Agent Workflow

The system uses a multi-agent architecture with the following agents:

1. **BiomarkerAnalyzer**: Validates and analyzes biomarker values
2. **DiseaseExplainer**: Provides disease pathophysiology explanations
3. **BiomarkerLinker**: Connects biomarkers to disease predictions
4. **ClinicalGuidelines**: Provides evidence-based recommendations
5. **ConfidenceAssessor**: Evaluates prediction reliability
6. **ResponseSynthesizer**: Compiles final response

### State Management

- `GuildState`: Shared state between agents
- `PatientInput`: Input data structure
- `ExplanationSOP`: Standard operating procedures

## Configuration

Settings are managed via Pydantic with environment variable support:

```python
from src.settings import get_settings

settings = get_settings()
print(settings.api.host)
```

## Deployment

### Production Considerations

1. **Security**:
   - Bind to specific interfaces (not 0.0.0.0)
   - Use HTTPS in production
   - Configure proper CORS origins

2. **Performance**:
   - Use multiple workers
   - Configure connection pooling
   - Monitor memory usage

3. **Monitoring**:
   - Enable health checks
   - Configure logging
   - Set up metrics collection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Tests failing with import errors**:
   - Check PYTHONPATH includes project root
   - Ensure all dependencies installed

2. **Vector store errors**:
   - Check data/vector_stores directory exists
   - Verify embedding model is accessible

3. **LLM connection issues**:
   - Check Ollama is running
   - Verify model is downloaded

## Performance Optimization

1. **Caching**: Redis for frequently accessed data
2. **Async**: Use async/await for I/O operations
3. **Batching**: Process multiple items when possible
4. **Lazy loading**: Load resources only when needed

## Security Best Practices

1. Never commit secrets or API keys
2. Use environment variables for configuration
3. Validate all inputs
4. Implement proper error handling
5. Regular security scans with Bandit
