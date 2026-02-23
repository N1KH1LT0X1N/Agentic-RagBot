"""
MediGuard AI — Ollama Client

Production-grade wrapper for the Ollama API with health checks,
streaming, and LangChain integration.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional

import httpx

from src.exceptions import OllamaConnectionError, OllamaModelNotFoundError
from src.settings import get_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper around the Ollama REST API."""

    def __init__(self, base_url: str, *, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout)

    # ── Health ───────────────────────────────────────────────────────────

    def ping(self) -> bool:
        try:
            resp = self._http.get("/api/version")
            return resp.status_code == 200
        except Exception:
            return False

    def health(self) -> Dict[str, Any]:
        try:
            resp = self._http.get("/api/version")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise OllamaConnectionError(f"Cannot reach Ollama: {exc}")

    def list_models(self) -> List[str]:
        try:
            resp = self._http.get("/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception as exc:
            logger.warning("Failed to list Ollama models: %s", exc)
            return []

    # ── Generation ───────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: str = "",
        temperature: float = 0.0,
        num_ctx: int = 8192,
    ) -> Dict[str, Any]:
        """Synchronous generation — returns the full response dict."""
        model = model or get_settings().ollama.model
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        if system:
            payload["system"] = system
        try:
            resp = self._http.post("/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise OllamaModelNotFoundError(f"Model '{model}' not found on Ollama server")
            raise OllamaConnectionError(str(exc))
        except Exception as exc:
            raise OllamaConnectionError(str(exc))

    def generate_stream(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: str = "",
        temperature: float = 0.0,
        num_ctx: int = 8192,
    ) -> Iterator[str]:
        """Streaming generation — yields text tokens."""
        model = model or get_settings().ollama.model
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        if system:
            payload["system"] = system
        try:
            with self._http.stream("POST", "/api/generate", json=payload) as resp:
                resp.raise_for_status()
                import json
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
        except Exception as exc:
            raise OllamaConnectionError(str(exc))

    # ── LangChain integration ────────────────────────────────────────────

    def get_langchain_model(
        self,
        *,
        model: Optional[str] = None,
        temperature: float = 0.0,
        json_mode: bool = False,
    ):
        """Return a LangChain ChatOllama instance."""
        model = model or get_settings().ollama.model
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=self.base_url,
            format="json" if json_mode else None,
        )

    def close(self):
        self._http.close()


@lru_cache(maxsize=1)
def make_ollama_client() -> OllamaClient:
    settings = get_settings()
    client = OllamaClient(
        base_url=settings.ollama.host,
        timeout=settings.ollama.timeout,
    )
    if client.ping():
        logger.info("Ollama connected at %s", settings.ollama.host)
    else:
        logger.warning("Ollama not reachable at %s", settings.ollama.host)
    return client
