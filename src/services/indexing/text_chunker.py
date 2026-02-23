"""
MediGuard AI — Medical-Aware Text Chunker

Section-aware chunking with biomarker / condition metadata extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# Biomarker names to detect in chunk text
_BIOMARKER_NAMES: Set[str] = {
    "Glucose", "Cholesterol", "Triglycerides", "HbA1c", "LDL", "HDL",
    "Insulin", "BMI", "Hemoglobin", "Platelets", "WBC", "RBC",
    "Hematocrit", "MCV", "MCH", "MCHC", "Heart Rate", "Systolic",
    "Diastolic", "Troponin", "CRP", "C-reactive Protein", "ALT", "AST",
    "Creatinine", "TSH", "T3", "T4", "Sodium", "Potassium", "Calcium",
}

_CONDITION_KEYWORDS: Dict[str, str] = {
    "diabetes": "diabetes",
    "diabetic": "diabetes",
    "hyperglycemia": "diabetes",
    "insulin resistance": "diabetes",
    "anemia": "anemia",
    "anaemia": "anemia",
    "iron deficiency": "anemia",
    "thalassemia": "thalassemia",
    "thalassaemia": "thalassemia",
    "thrombocytopenia": "thrombocytopenia",
    "heart disease": "heart_disease",
    "cardiovascular": "heart_disease",
    "coronary": "heart_disease",
    "hypertension": "heart_disease",
    "atherosclerosis": "heart_disease",
    "hyperlipidemia": "heart_disease",
}

_SECTION_RE = re.compile(
    r"^(?:#+\s*)?("
    r"abstract|introduction|background|methods?|methodology|materials?"
    r"|results?|findings|discussion|conclusion|summary"
    r"|guidelines?|recommendations?|references?|bibliography"
    r"|clinical\s*presentation|pathophysiology|diagnosis|treatment|prognosis"
    r")\b",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class MedicalChunk:
    """A single chunk with medical metadata."""
    text: str
    chunk_index: int
    document_id: str = ""
    title: str = ""
    source_file: str = ""
    page_number: Optional[int] = None
    section_title: str = ""
    biomarkers_mentioned: List[str] = field(default_factory=list)
    condition_tags: List[str] = field(default_factory=list)
    word_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "chunk_text": self.text,
            "chunk_index": self.chunk_index,
            "document_id": self.document_id,
            "title": self.title,
            "source_file": self.source_file,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "biomarkers_mentioned": self.biomarkers_mentioned,
            "condition_tags": self.condition_tags,
        }


class MedicalTextChunker:
    """Section-aware text chunker optimised for medical documents."""

    def __init__(
        self,
        target_words: int = 600,
        overlap_words: int = 100,
        min_words: int = 50,
    ):
        self.target_words = target_words
        self.overlap_words = overlap_words
        self.min_words = min_words

    def chunk_text(
        self,
        text: str,
        *,
        document_id: str = "",
        title: str = "",
        source_file: str = "",
    ) -> List[MedicalChunk]:
        """Split text into enriched medical chunks."""
        sections = self._split_sections(text)
        chunks: List[MedicalChunk] = []
        idx = 0
        for section_title, section_text in sections:
            words = section_text.split()
            if not words:
                continue
            start = 0
            while start < len(words):
                end = min(start + self.target_words, len(words))
                chunk_words = words[start:end]
                if len(chunk_words) < self.min_words and chunks:
                    # merge tiny tail into previous chunk
                    chunks[-1].text += " " + " ".join(chunk_words)
                    chunks[-1].word_count = len(chunks[-1].text.split())
                    break

                chunk_text = " ".join(chunk_words)
                biomarkers = self._detect_biomarkers(chunk_text)
                conditions = self._detect_conditions(chunk_text)

                chunks.append(
                    MedicalChunk(
                        text=chunk_text,
                        chunk_index=idx,
                        document_id=document_id,
                        title=title,
                        source_file=source_file,
                        section_title=section_title,
                        biomarkers_mentioned=biomarkers,
                        condition_tags=conditions,
                        word_count=len(chunk_words),
                    )
                )
                idx += 1
                start = end - self.overlap_words if end < len(words) else len(words)
        return chunks

    # ── internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _split_sections(text: str) -> List[tuple[str, str]]:
        """Split text by detected section headers."""
        matches = list(_SECTION_RE.finditer(text))
        if not matches:
            return [("", text)]
        sections: List[tuple[str, str]] = []
        # text before first section header
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.append(("", preamble))
        for i, match in enumerate(matches):
            header = match.group(1).strip().title()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            # Skip reference/bibliography sections
            if header.lower() in ("references", "bibliography"):
                continue
            if body:
                sections.append((header, body))
        return sections or [("", text)]

    @staticmethod
    def _detect_biomarkers(text: str) -> List[str]:
        text_lower = text.lower()
        return sorted(
            {name for name in _BIOMARKER_NAMES if name.lower() in text_lower}
        )

    @staticmethod
    def _detect_conditions(text: str) -> List[str]:
        text_lower = text.lower()
        return sorted(
            {tag for kw, tag in _CONDITION_KEYWORDS.items() if kw in text_lower}
        )
