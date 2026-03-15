# ADR-001: Multi-Agent Architecture

## Status
Accepted

## Context
MediGuard AI needs to analyze complex medical data including biomarkers, patient context, and provide clinical insights. A monolithic approach would be difficult to maintain, test, and extend. We need a system that can:
- Handle different types of medical analysis tasks
- Be easily extensible with new analysis capabilities
- Provide clear separation of concerns
- Allow for independent testing and validation of each component

## Decision
We will implement a multi-agent architecture using LangGraph for orchestration. Each agent will have a specific responsibility:
1. **Biomarker Analyzer** - Analyzes individual biomarker values
2. **Disease Explainer** - Explains disease mechanisms
3. **Biomarker Linker** - Links biomarkers to diseases
4. **Clinical Guidelines** - Provides evidence-based recommendations
5. **Confidence Assessor** - Evaluates confidence in results
6. **Response Synthesizer** - Combines all outputs into a coherent response

## Consequences

### Positive
- **Modularity**: Each agent can be developed, tested, and updated independently
- **Extensibility**: New agents can be added without modifying existing ones
- **Reusability**: Agents can be reused in different workflows
- **Testability**: Each agent can be unit tested in isolation
- **Parallel Processing**: Some agents can run in parallel for better performance

### Negative
- **Complexity**: More complex than a monolithic approach
- **Overhead**: Additional orchestration overhead
- **Debugging**: More difficult to trace issues across multiple agents
- **Resource Usage**: Multiple agents may consume more memory/CPU

## Implementation
```python
class ClinicalInsightGuild:
    def __init__(self):
        self.biomarker_analyzer = biomarker_analyzer_agent
        self.disease_explainer = create_disease_explainer_agent(retrievers["disease_explainer"])
        self.biomarker_linker = create_biomarker_linker_agent(retrievers["biomarker_linker"])
        self.clinical_guidelines = create_clinical_guidelines_agent(retrievers["clinical_guidelines"])
        self.confidence_assessor = confidence_assessor_agent
        self.response_synthesizer = response_synthesizer_agent
        
        self.workflow = self._build_workflow()
```

The workflow is built using LangGraph's StateGraph, defining the flow of data between agents.

## Notes
- Agents communicate through a shared state object (GuildState)
- Each agent receives the full state but only modifies its specific portion
- The workflow ensures proper execution order and handles failures
- Future agents can be added by extending the workflow graph
