"""
MediGuard AI — Langfuse Observability Tracer

Wraps Langfuse v3 SDK for end-to-end tracing of the RAG pipeline.
Silently no-ops when Langfuse is disabled or unreachable.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Dict, Optional

from src.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from langfuse import Langfuse as _Langfuse
except ImportError:
    _Langfuse = None  # type: ignore[assignment,misc]


class LangfuseTracer:
    """Thin wrapper around Langfuse for MediGuard pipeline tracing."""

    def __init__(self, client: Any | None):
        self._client = client
        self._enabled = client is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def trace(self, name: str, **kwargs: Any):
        """Create a new trace (top-level span)."""
        if not self._enabled:
            return _NullSpan()
        return self._client.trace(name=name, **kwargs)

    @contextmanager
    def span(self, trace, name: str, **kwargs):
        """Context manager for creating a span within a trace."""
        if not self._enabled or trace is None:
            yield _NullSpan()
            return
        s = trace.span(name=name, **kwargs)
        try:
            yield s
        finally:
            s.end()

    def score(self, trace_id: str, name: str, value: float, comment: str = ""):
        """Attach a score to a trace (for evaluation feedback)."""
        if not self._enabled:
            return
        try:
            self._client.score(trace_id=trace_id, name=name, value=value, comment=comment)
        except Exception as exc:
            logger.warning("Langfuse score failed: %s", exc)

    def flush(self):
        if self._enabled:
            try:
                self._client.flush()
            except Exception:
                pass


class _NullSpan:
    """Dummy span object that silently swallows calls."""

    def __getattr__(self, name: str):
        return lambda *a, **kw: _NullSpan()

    def end(self):
        pass


@lru_cache(maxsize=1)
def make_langfuse_tracer() -> LangfuseTracer:
    settings = get_settings()
    if not settings.langfuse.enabled or _Langfuse is None:
        logger.info("Langfuse tracing disabled")
        return LangfuseTracer(None)
    try:
        client = _Langfuse(
            public_key=settings.langfuse.public_key,
            secret_key=settings.langfuse.secret_key,
            host=settings.langfuse.host,
        )
        logger.info("Langfuse connected (%s)", settings.langfuse.host)
        return LangfuseTracer(client)
    except Exception as exc:
        logger.warning("Langfuse unavailable: %s", exc)
        return LangfuseTracer(None)
