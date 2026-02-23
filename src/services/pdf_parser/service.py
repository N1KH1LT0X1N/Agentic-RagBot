"""
MediGuard AI — PDF Parser Service

Production PDF parsing with Docling (preferred) falling back to PyPDF.
Returns structured text with section metadata.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    """One logical section extracted from a PDF."""

    title: str
    text: str
    page_numbers: List[int] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Result of parsing a single PDF."""

    filename: str
    content_hash: str
    full_text: str
    sections: List[ParsedSection] = field(default_factory=list)
    page_count: int = 0
    error: Optional[str] = None


class PDFParserService:
    """Unified PDF parsing with Docling → PyPDF fallback."""

    def __init__(self) -> None:
        self._has_docling = self._check_docling()

    @staticmethod
    def _check_docling() -> bool:
        try:
            import docling  # noqa: F401
            return True
        except ImportError:
            logger.info("Docling not installed — using PyPDF fallback")
            return False

    def parse(self, path: Path) -> ParsedDocument:
        """Parse a PDF file and return structured text."""
        if not path.exists():
            return ParsedDocument(
                filename=path.name,
                content_hash="",
                full_text="",
                error=f"File not found: {path}",
            )

        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        if self._has_docling:
            return self._parse_with_docling(path, content_hash)
        return self._parse_with_pypdf(path, content_hash)

    # ------------------------------------------------------------------ #
    # Docling (preferred)
    # ------------------------------------------------------------------ #

    def _parse_with_docling(self, path: Path, content_hash: str) -> ParsedDocument:
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(path))
            doc = result.document

            sections: list[ParsedSection] = []
            full_parts: list[str] = []

            for element in doc.iterate_items():
                text = element.text if hasattr(element, "text") else str(element)
                if text.strip():
                    full_parts.append(text.strip())
                    sections.append(
                        ParsedSection(
                            title=getattr(element, "label", ""),
                            text=text.strip(),
                        )
                    )

            full_text = "\n\n".join(full_parts)
            return ParsedDocument(
                filename=path.name,
                content_hash=content_hash,
                full_text=full_text,
                sections=sections,
                page_count=getattr(doc, "num_pages", 0),
            )
        except Exception as exc:
            logger.warning("Docling failed for %s — falling back to PyPDF: %s", path.name, exc)
            return self._parse_with_pypdf(path, content_hash)

    # ------------------------------------------------------------------ #
    # PyPDF fallback
    # ------------------------------------------------------------------ #

    def _parse_with_pypdf(self, path: Path, content_hash: str) -> ParsedDocument:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages_text: list[str] = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(text.strip())

            full_text = "\n\n".join(pages_text)
            sections = [
                ParsedSection(title=f"Page {i + 1}", text=t, page_numbers=[i + 1])
                for i, t in enumerate(pages_text)
            ]

            return ParsedDocument(
                filename=path.name,
                content_hash=content_hash,
                full_text=full_text,
                sections=sections,
                page_count=len(reader.pages),
            )
        except Exception as exc:
            logger.error("PyPDF failed for %s: %s", path.name, exc)
            return ParsedDocument(
                filename=path.name,
                content_hash=content_hash,
                full_text="",
                error=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Batch
    # ------------------------------------------------------------------ #

    def parse_directory(self, directory: Path) -> List[ParsedDocument]:
        """Parse all PDFs in a directory."""
        results: list[ParsedDocument] = []
        for pdf_path in sorted(directory.glob("*.pdf")):
            logger.info("Parsing %s …", pdf_path.name)
            results.append(self.parse(pdf_path))
        return results


@lru_cache(maxsize=1)
def make_pdf_parser_service() -> PDFParserService:
    return PDFParserService()
