"""
MediGuard AI — Pydantic Settings (hierarchical, env-driven)

All runtime configuration lives here.  Values are read from environment
variables (with ``env_nested_delimiter="__"``), so ``OPENSEARCH__HOST``
maps to ``settings.opensearch.host``.

Usage::

    from src.settings import get_settings
    settings = get_settings()
    print(settings.opensearch.host)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

# ── Helpers ──────────────────────────────────────────────────────────────────

class _Base(BaseSettings):
    """Shared Settings base with nested-env support."""

    model_config = {
        "env_nested_delimiter": "__",
        "frozen": True,
        "extra": "ignore",
    }


# ── Sub-settings ─────────────────────────────────────────────────────────────

class APISettings(_Base):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 4
    cors_origins: str = "*"
    log_level: str = "INFO"

    model_config = {"env_prefix": "API__"}


class PostgresSettings(_Base):
    database_url: str = "postgresql+psycopg2://mediguard:mediguard@localhost:5432/mediguard_db"

    model_config = {"env_prefix": "POSTGRES__"}


class OpenSearchSettings(_Base):
    host: str = "http://localhost:9200"
    index_name: str = "medical_chunks"
    username: str = ""
    password: str = ""
    verify_certs: bool = False
    timeout: int = 30

    model_config = {"env_prefix": "OPENSEARCH__"}


class RedisSettings(_Base):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    ttl_seconds: int = 21600  # 6 hours default
    enabled: bool = True

    model_config = {"env_prefix": "REDIS__"}


class OllamaSettings(_Base):
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    embedding_model: str = "nomic-embed-text"
    timeout: int = 120
    num_ctx: int = 8192

    model_config = {"env_prefix": "OLLAMA__"}


class LLMSettings(_Base):
    provider: Literal["groq", "gemini", "ollama"] = "groq"
    temperature: float = 0.0
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    model_config = {"env_prefix": "LLM__"}


class EmbeddingSettings(_Base):
    provider: Literal["jina", "google", "huggingface", "ollama"] = "google"
    jina_api_key: str = ""
    jina_model: str = "jina-embeddings-v3"
    dimension: int = 1024
    google_api_key: str = ""
    huggingface_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 64

    model_config = {"env_prefix": "EMBEDDING__"}


class ChunkingSettings(_Base):
    chunk_size: int = 600  # words
    chunk_overlap: int = 100  # words
    min_chunk_size: int = 50
    section_aware: bool = True

    model_config = {"env_prefix": "CHUNKING__"}


class LangfuseSettings(_Base):
    enabled: bool = False
    public_key: str = ""
    secret_key: str = ""
    host: str = "http://localhost:3001"

    model_config = {"env_prefix": "LANGFUSE__"}


class TelegramSettings(_Base):
    enabled: bool = False
    bot_token: str = ""
    allowed_users: str = ""  # comma-separated user IDs

    model_config = {"env_prefix": "TELEGRAM__"}


class BiomarkerSettings(_Base):
    reference_file: str = "config/biomarker_references.json"
    analyzer_threshold: float = 0.15
    critical_alert_mode: Literal["strict", "moderate", "permissive"] = "strict"

    model_config = {"env_prefix": "BIOMARKER__"}


class MedicalPDFSettings(_Base):
    pdf_directory: str = "data/medical_pdfs"
    vector_store_path: str = "data/vector_stores"
    max_file_size_mb: int = 50
    max_pages: int = 500

    model_config = {"env_prefix": "PDF__"}


# ── Root settings ────────────────────────────────────────────────────────────

class Settings(_Base):
    """Root configuration — aggregates all sub-settings."""

    app_name: str = "MediGuard AI"
    app_version: str = "2.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Sub-settings (populated from env with nesting)
    api: APISettings = Field(default_factory=APISettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    opensearch: OpenSearchSettings = Field(default_factory=OpenSearchSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    biomarker: BiomarkerSettings = Field(default_factory=BiomarkerSettings)
    pdf: MedicalPDFSettings = Field(default_factory=MedicalPDFSettings)

    model_config = {
        "env_nested_delimiter": "__",
        "frozen": True,
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached factory — returns a single frozen ``Settings`` instance."""
    return Settings()
