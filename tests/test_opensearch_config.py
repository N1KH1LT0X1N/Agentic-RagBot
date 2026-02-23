"""
Tests for src/services/opensearch/index_config.py — OpenSearch mapping.
"""

from src.services.opensearch.index_config import MEDICAL_CHUNKS_MAPPING


def test_mapping_has_required_fields():
    """The mapping should define all required fields."""
    props = MEDICAL_CHUNKS_MAPPING["mappings"]["properties"]
    required = ["chunk_text", "title", "embedding", "biomarkers_mentioned", "condition_tags"]
    for field_name in required:
        assert field_name in props, f"Missing field: {field_name}"


def test_knn_vector_config():
    """The embedding field should be configured for KNN."""
    embed = MEDICAL_CHUNKS_MAPPING["mappings"]["properties"]["embedding"]
    assert embed["type"] == "knn_vector"
    assert embed["dimension"] == 1024


def test_synonym_analyzer():
    """Mapping should include a medical synonym analyzer."""
    analyzers = MEDICAL_CHUNKS_MAPPING["settings"]["analysis"]["analyzer"]
    assert "medical_analyzer" in analyzers


def test_knn_enabled():
    """KNN should be enabled in settings."""
    settings = MEDICAL_CHUNKS_MAPPING["settings"]
    assert settings["index"]["knn"] is True
