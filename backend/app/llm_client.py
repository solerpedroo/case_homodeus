"""Provider-agnostic LLM client factory.

Both Groq and OpenAI expose the same Chat Completions schema (Groq is
intentionally OpenAI-API-compatible), so we use the official `openai` Python
SDK against either endpoint by overriding `base_url`. This keeps the rest of
the codebase provider-agnostic.

Two helpers are exported:
- `get_llm_client()` — main agent client
- `get_judge_client()` — judge client (may use a different model)

Both return an `AsyncOpenAI` instance plus the model name to send.
"""
from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import settings


@dataclass
class LlmClient:
    client: AsyncOpenAI
    model: str
    provider: str


def _build(api_key: str, base_url: str | None, model: str, provider: str) -> LlmClient:
    kwargs: dict = {"api_key": api_key or "missing"}
    if base_url:
        kwargs["base_url"] = base_url
    return LlmClient(client=AsyncOpenAI(**kwargs), model=model, provider=provider)


def get_llm_client() -> LlmClient:
    if settings.llm_provider == "groq":
        return _build(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_model,
            provider="groq",
        )
    return _build(
        api_key=settings.openai_api_key,
        base_url=None,
        model=settings.openai_model,
        provider="openai",
    )


def get_judge_client() -> LlmClient:
    if settings.llm_provider == "groq":
        return _build(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_judge_model,
            provider="groq",
        )
    return _build(
        api_key=settings.openai_api_key,
        base_url=None,
        model=settings.openai_judge_model,
        provider="openai",
    )


def is_configured() -> bool:
    return bool(settings.active_api_key)


def supports_json_mode() -> bool:
    """Both Groq (Llama 3.x) and OpenAI support response_format=json_object,
    but Groq's support varies by model. We detect by model family.
    """
    if settings.llm_provider == "openai":
        return True
    m = settings.groq_judge_model.lower()
    return "llama-3" in m or "llama3" in m or "mixtral" in m or "qwen" in m
