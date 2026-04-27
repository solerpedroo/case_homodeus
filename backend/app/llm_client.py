"""Provider-agnostic LLM client factory.

EN:
    Groq exposes an OpenAI-compatible Chat Completions API. We use the official
    `openai` Async SDK for both providers: for Groq, `base_url` points to
    `https://api.groq.com/openai/v1`; for OpenAI, the default base URL is used.

    Exports:
    - `get_llm_client()` — model used by the agent (planning, answers).
    - `get_judge_client()` — model used by the evaluation judge (can differ).
    - `is_configured()` / `supports_json_mode()` — cheap capability checks.

    Returning a small `LlmClient` dataclass keeps call sites explicit about
    which model string to pass into `chat.completions.create`.

PT:
    A Groq expõe uma API compatível com OpenAI. Usamos o SDK `openai` async
    nos dois fornecedores: na Groq, `base_url` aponta para o endpoint Groq;
    na OpenAI usa-se o URL por defeito.

    Exporta:
    - `get_llm_client()` — modelo do agente (planeamento, respostas).
    - `get_judge_client()` — modelo do juiz de avaliação (pode diferir).
    - `is_configured()` / `supports_json_mode()` — verificações rápidas.

    O dataclass `LlmClient` deixa explícito qual modelo passar a
    `chat.completions.create`.
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
    # EN: `api_key or "missing"` lets the client construct; actual calls fail
    #     with a clear auth error if the key is empty (see chat route checks).
    # PT: `api_key or "missing"` permite construir o cliente; chamadas falham
    #     com erro de auth claro se a chave estiver vazia (rotas verificam antes).
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
