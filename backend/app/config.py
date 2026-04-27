"""Centralized configuration via pydantic-settings.

EN:
    Single source of truth for environment variables. Pydantic validates types
    at import time so misconfiguration fails fast (wrong port, missing enum).

    - LLM_PROVIDER: `groq` (OpenAI-compatible API at Groq) or `openai`.
    - Keys and model names are separate per provider; `active_*` properties
      pick the right pair for the running provider.
    - EMBEDDINGS_PROVIDER: `local` uses Chroma's bundled MiniLM (no API key);
      `openai` uses paid embeddings if you set OPENAI_API_KEY.
    - Agent knobs: AGENT_VERSION (v1 baseline vs v2 full pipeline),
      CONFIDENCE_THRESHOLD (below which v2 may refuse after scoring),
      MAX_TOOL_ITERATIONS (ReAct loop depth).

PT:
    Configuração centralizada a partir de variáveis de ambiente. O Pydantic
    valida tipos à importação para falhar cedo (porta errada, enum inválido).

    - LLM_PROVIDER: `groq` (API compatível com OpenAI na Groq) ou `openai`.
    - Chaves e nomes de modelo são por fornecedor; as propriedades `active_*`
      escolhem o par correto em tempo de execução.
    - EMBEDDINGS_PROVIDER: `local` usa o MiniLM embutido no Chroma (sem chave);
      `openai` usa embeddings pagos se definir OPENAI_API_KEY.
    - Parâmetros do agente: AGENT_VERSION (v1 base vs v2 completo),
      CONFIDENCE_THRESHOLD (abaixo do qual a v2 pode recusar após scoring),
      MAX_TOOL_ITERATIONS (profundidade do loop ReAct).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LlmProvider = Literal["groq", "openai"]
EmbeddingsProvider = Literal["local", "openai"]


class Settings(BaseSettings):
    # EN: Reads `.env` in the working directory; unknown env vars are ignored
    #     so Docker/K8s can inject extra keys without crashing imports.
    # PT: Lê `.env` no diretório de trabalho; variáveis desconhecidas são
    #     ignoradas para Docker/K8s poderem injetar chaves extra.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Provider selection ---- #
    llm_provider: LlmProvider = Field(default="groq")
    embeddings_provider: EmbeddingsProvider = Field(default="local")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_llm_provider(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("embeddings_provider", mode="before")
    @classmethod
    def _normalize_embeddings_provider(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    # ---- Groq (default) ---- #
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_judge_model: str = Field(default="llama-3.3-70b-versatile")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")

    # ---- OpenAI (alternative) ---- #
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_judge_model: str = Field(default="gpt-4o")

    # ---- LLM common ---- #
    llm_temperature: float = Field(default=0.0)

    # ---- Web search ---- #
    tavily_api_key: str = Field(default="")

    # ---- Redis ---- #
    redis_url: str = Field(default="redis://localhost:6379")
    session_ttl_seconds: int = Field(default=2 * 60 * 60)

    # ---- Server ---- #
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:3000")

    # ---- Agent ---- #
    agent_version: Literal["v1", "v2"] = Field(default="v2")
    confidence_threshold: float = Field(default=0.55)
    max_tool_iterations: int = Field(default=4)

    # ---- Vector store ---- #
    chroma_persist_dir: str = Field(default="./data/chroma")
    labor_code_pdf_url: str = Field(
        default="https://www.act.gov.pt/(pt-PT)/Legislacao/Legislacao_n/Documents/C%C3%B3digo%20do%20Trabalho.pdf"
    )

    # ---- Convenience accessors ---- #

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def active_api_key(self) -> str:
        return self.groq_api_key if self.llm_provider == "groq" else self.openai_api_key

    @property
    def active_base_url(self) -> str | None:
        return self.groq_base_url if self.llm_provider == "groq" else None

    @property
    def active_model(self) -> str:
        return self.groq_model if self.llm_provider == "groq" else self.openai_model

    @property
    def active_judge_model(self) -> str:
        return (
            self.groq_judge_model if self.llm_provider == "groq" else self.openai_judge_model
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # EN: Singleton pattern — one Settings instance per process; tests can
    #     clear the cache if they need to reload env.
    # PT: Padrão singleton — uma instância Settings por processo; testes
    #     podem limpar a cache para recarregar o ambiente.
    return Settings()


# EN: Module-level alias imported across the codebase (`from app.config import settings`).
# PT: Alias ao nível do módulo usado em todo o código (`from app.config import settings`).
settings = get_settings()
