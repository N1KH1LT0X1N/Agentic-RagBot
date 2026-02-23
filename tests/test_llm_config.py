"""
Tests for Task 7: Model Selection Centralization
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_config import LLMConfig


def test_get_synthesizer_returns_not_none():
    """get_synthesizer should return a model (may need API key — skip if unavailable)"""
    config = LLMConfig(lazy=True)
    try:
        model = config.get_synthesizer()
        assert model is not None
    except (ValueError, ImportError):
        # API keys may not be configured in CI
        import pytest
        pytest.skip("LLM provider not configured, skipping")


def test_get_synthesizer_with_model_name():
    """get_synthesizer with custom model should not raise (validates dispatch)"""
    config = LLMConfig(lazy=True)
    try:
        model = config.get_synthesizer(model_name="llama-3.3-70b-versatile")
        assert model is not None
    except (ValueError, ImportError):
        import pytest
        pytest.skip("LLM provider not configured, skipping")


def test_llm_config_has_synthesizer_property():
    """LLMConfig should expose synthesizer_8b via property"""
    assert hasattr(LLMConfig, "synthesizer_8b")


def test_llm_config_has_all_properties():
    """Verify all expected model properties exist"""
    expected = ["planner", "analyzer", "explainer", "synthesizer_7b", "synthesizer_8b", "director", "embedding_model"]
    for prop_name in expected:
        assert hasattr(LLMConfig, prop_name), f"Missing property: {prop_name}"
