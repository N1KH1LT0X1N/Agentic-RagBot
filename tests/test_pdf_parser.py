"""
Tests for src/services/pdf_parser/service.py — PDF parsing.
"""

from pathlib import Path

import pytest

from src.services.pdf_parser.service import PDFParserService, ParsedDocument


@pytest.fixture
def parser():
    return PDFParserService()


def test_missing_file(parser: PDFParserService):
    """Should return error for missing files."""
    result = parser.parse(Path("/nonexistent/fake.pdf"))
    assert isinstance(result, ParsedDocument)
    assert result.error is not None
    assert "not found" in result.error.lower()


def test_parse_directory_empty(parser: PDFParserService, tmp_path: Path):
    """Empty directory should return empty list."""
    results = parser.parse_directory(tmp_path)
    assert results == []


def test_parse_directory_with_pdf(parser: PDFParserService, tmp_path: Path):
    """Should parse PDFs found in a directory."""
    # Check if there are any real PDFs in data/medical_pdfs
    pdf_dir = Path("data/medical_pdfs")
    if pdf_dir.exists() and list(pdf_dir.glob("*.pdf")):
        results = parser.parse_directory(pdf_dir)
        assert len(results) > 0
        for doc in results:
            assert isinstance(doc, ParsedDocument)
            assert doc.filename.endswith(".pdf")
    else:
        pytest.skip("No medical PDFs available for testing")
