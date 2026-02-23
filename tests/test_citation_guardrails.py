from src.agents.disease_explainer import create_disease_explainer_agent


class EmptyRetriever:
    def __init__(self):
        self.search_kwargs = {"k": 3}

    def invoke(self, query):
        return []


class StubSOP:
    disease_explainer_k = 3
    require_pdf_citations = True


def test_disease_explainer_requires_citations():
    agent = create_disease_explainer_agent(EmptyRetriever())
    state = {
        "model_prediction": {"disease": "Diabetes", "confidence": 0.6},
        "sop": StubSOP()
    }
    result = agent.explain(state)
    findings = result["agent_outputs"][0].findings
    assert findings["citations"] == []
    assert "insufficient" in findings["pathophysiology"].lower()
