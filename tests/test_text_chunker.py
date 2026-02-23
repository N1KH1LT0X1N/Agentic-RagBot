"""
Tests for src/services/indexing/text_chunker.py — medical text chunking.
"""

import pytest

from src.services.indexing.text_chunker import MedicalChunk, MedicalTextChunker


@pytest.fixture
def chunker():
    return MedicalTextChunker(target_words=30, overlap_words=5, min_words=5)


def test_basic_chunking(chunker: MedicalTextChunker):
    """Should split text into chunks."""
    # Generate enough words to require multiple chunks (target_words=30)
    words = [f"word{i}" for i in range(200)]
    text = " ".join(words)
    chunks = chunker.chunk_text(text)
    assert len(chunks) > 1
    for c in chunks:
        assert isinstance(c, MedicalChunk)
        assert c.text.strip()


def test_section_aware(chunker: MedicalTextChunker):
    """Should detect section headers."""
    text = (
        "Introduction\nThis study examines diabetes.\n\n"
        "Methods\nWe collected blood samples.\n\n"
        "Results\nGlucose levels were elevated."
    )
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 1


def test_biomarker_detection(chunker: MedicalTextChunker):
    """Should detect biomarkers in chunks."""
    text = (
        "The patient's HbA1c was 8.2% indicating poor glycemic control. "
        "Fasting glucose was 185 mg/dL and total cholesterol was elevated at 240."
    )
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 1
    # At least one chunk should have biomarkers detected
    all_biomarkers = set()
    for c in chunks:
        all_biomarkers.update(c.biomarkers_mentioned)
    assert len(all_biomarkers) > 0


def test_condition_tagging(chunker: MedicalTextChunker):
    """Should tag chunks with relevant conditions."""
    text = (
        "Diabetes mellitus is characterised by insulin resistance and elevated blood glucose. "
        "Cardiovascular disease risk increases with uncontrolled hypertension."
    )
    chunks = chunker.chunk_text(text)
    all_tags = set()
    for c in chunks:
        all_tags.update(c.condition_tags)
    assert "diabetes" in all_tags or "heart_disease" in all_tags


def test_empty_text(chunker: MedicalTextChunker):
    """Empty text should return empty list."""
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   ") == []
