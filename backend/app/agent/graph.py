"""Agent orchestrator — hand-rolled async state machine with SSE-friendly events.

EN:
    This module implements `LaborAgent`, the brain of the backend. Design goals:
    1. **Streaming first** — `stream()` yields typed dicts (`phase`, `tool_call`,
       `token`, `done`, …) so FastAPI can forward them as Server-Sent Events.
    2. **Two product versions** — `v1` is a deliberately weak baseline (web
       only, single iteration) for A/B metrics; `v2` is production (classifier,
       all tools, confidence gating, source recovery).
    3. **Dual planning paths** — OpenAI-compatible providers that support native
       `tool_calls` use the SDK path; Groq/Llama uses a JSON plan suffix
       (`GROQ_JSON_PLAN_SUFFIX_*`) because models hallucinate XML tools.
    4. **Deterministic tools** — numeric payroll never comes from free-form LLM
       math; it always goes through `calculate`.

    v2 high-level pipeline:
        classify → (maybe early out_of_scope) → plan/tool loop → optional
        `_recover_sources` → final answer stream → `_score_confidence` →
        maybe `_compose_refusal`.

    State is a typed `AgentState` dict; `_serializable` converts Pydantic
    models to plain dicts for JSON.

PT:
    Este módulo implementa o `LaborAgent`, o cérebro do backend. Objectivos:
    1. **Streaming primeiro** — `stream()` produz dicts tipados para SSE.
    2. **Duas versões** — `v1` baseline fraco (só web); `v2` produção completa.
    3. **Dois caminhos de plano** — `tool_calls` nativos (OpenAI) vs plano JSON
       (Groq/Llama) por fiabilidade.
    4. **Ferramentas determinísticas** — números de salário vêm sempre de
       `calculate`, nunca de aritmética livre do LLM.

    Pipeline v2:
        classificar → (talvez `out_of_scope`) → loop ferramentas →
        `_recover_sources` opcional → resposta final em stream → scoring →
        recusa opcional.

    O estado é um `AgentState`; `_serializable` prepara JSON.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

import httpx

from app.agent.prompts import (
    CLASSIFIER_PROMPT,
    GROQ_JSON_PLAN_SUFFIX_V1,
    GROQ_JSON_PLAN_SUFFIX_V2,
    LANGUAGE_HINT_EN,
    REFUSAL_INSTRUCTION,
    SYSTEM_V1,
    SYSTEM_V2,
)
from app.agent.state import AgentState, QuestionCategory, Source, ToolCallTrace
from app.agent.tools.calculator import calculate as calc_tool
from app.agent.tools.doc_fetcher import fetch_and_parse
from app.agent.tools.labor_index import search_labor_code
from app.agent.tools.web_search import web_search
from app.config import settings
from app.llm_client import get_llm_client
from app.logging_config import logger


# EN: Mirrors `QuestionCategory` in state.py — classifier must output one of these.
# PT: Espelha `QuestionCategory` em state.py — o classificador deve devolver uma.
_VALID_CATEGORIES: tuple[QuestionCategory, ...] = (
    "tax",
    "social_security",
    "labor_code",
    "salary_calc",
    "edge_case",
    "out_of_scope",
)


# EN: OpenAI function-calling JSON schemas — only used on the native tool path.
# PT: Esquemas JSON para function-calling OpenAI — só no caminho nativo de tools.
# ----- Tool schemas exposed to OpenAI for function calling ----- #

V2_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Pesquisa fontes oficiais portuguesas (ACT, Portal das Finanças, "
                "DRE, CITE). Usar quando precisas de leis, taxas ou informação atual."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Pesquisa em português."},
                    "category": {
                        "type": "string",
                        "enum": list(_VALID_CATEGORIES),
                        "description": "Categoria da pergunta para escolher domínios.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Descarrega e extrai o texto de uma URL oficial portuguesa.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_labor_code",
            "description": "Pesquisa semântica sobre o Código do Trabalho português (índice local). Devolve artigos relevantes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Calculadora salarial determinística. NUNCA faças aritmética — "
                "chama esta ferramenta para qualquer cálculo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "tsu",
                            "irs",
                            "holiday_subsidy",
                            "christmas_subsidy",
                            "net_salary",
                        ],
                    },
                    "gross_monthly": {"type": "number"},
                    "monthly_gross": {"type": "number"},
                    "months_worked_in_year": {"type": "integer"},
                    "marital_status": {
                        "type": "string",
                        "enum": ["single", "married_single_holder", "married_two_holders"],
                    },
                    "dependents": {"type": "integer"},
                },
                "required": ["action"],
            },
        },
    },
]

V1_TOOLS = [V2_TOOLS[0]]  # EN: v1 exposes search_web only — PT: v1 só search_web

V1_TOOL_NAMES = frozenset({"search_web"})
V2_TOOL_NAMES = frozenset({"search_web", "fetch_url", "search_labor_code", "calculate"})


class LaborAgent:
    # EN: Orchestrator class — one instance per HTTP request in chat routes.
    # PT: Classe orquestradora — uma instância por pedido HTTP nas rotas de chat.
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        version: str | None = None,
        locale: str | None = None,
    ) -> None:
        self.version = (version or settings.agent_version).lower()
        self.locale = "en" if (locale or "pt").strip().lower() == "en" else "pt"
        self.http = http_client
        llm = get_llm_client()
        self.client = llm.client
        self.model = llm.model
        self.provider = llm.provider
        self.system_prompt = SYSTEM_V1 if self.version == "v1" else SYSTEM_V2
        self.tools = V1_TOOLS if self.version == "v1" else V2_TOOLS
        self.max_iterations = 1 if self.version == "v1" else settings.max_tool_iterations

    def _build_system_messages(self) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        if self.locale == "en":
            msgs.append({"role": "system", "content": LANGUAGE_HINT_EN})
        return msgs

    def _must_use_json_tool_plan(self) -> bool:
        """Native OpenAI-style tool_calls often break on Groq (Llama emits <function=...>).

        Use JSON planner whenever provider is groq OR the HTTP client targets groq.com
        (covers mis-set LLM_PROVIDER while still pointing at Groq).
        """
        if settings.llm_provider == "groq":
            return True
        try:
            base = str(getattr(self.client, "base_url", "") or "").lower()
        except Exception:
            base = ""
        return "groq.com" in base

    # ---------- Public API ---------- #

    async def run(
        self,
        user_query: str,
        history: list[dict[str, Any]] | None = None,
        conversation_id: str = "",
    ) -> AgentState:
        events: list[dict] = []
        state: AgentState = {
            "user_query": user_query,
            "conversation_id": conversation_id,
            "messages": list(history or []),
            "sources": [],
            "tool_traces": [],
            "iterations": 0,
            "agent_version": "v1" if self.version == "v1" else "v2",
        }
        async for ev in self.stream(user_query, history=history, conversation_id=conversation_id):
            events.append(ev)
            if ev.get("type") == "done":
                state.update(ev["state"])  # type: ignore[arg-type]
        return state

    async def stream(
        self,
        user_query: str,
        history: list[dict[str, Any]] | None = None,
        conversation_id: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        state: AgentState = {
            "user_query": user_query,
            "conversation_id": conversation_id,
            "messages": list(history or []),
            "sources": [],
            "tool_traces": [],
            "iterations": 0,
            "agent_version": "v1" if self.version == "v1" else "v2",
        }

        # EN: v2 runs a tiny LLM classifier before spending tokens on tools.
        # PT: v2 corre um classificador LLM pequeno antes de gastar tokens em tools.
        # ----- Phase: classify (v2 only) ----- #
        if self.version == "v2":
            yield {"type": "phase", "phase": "classify", "message": "A classificar a pergunta…"}
            try:
                category = await self._classify(user_query)
            except Exception as exc:
                logger.warning("Classifier failed: {}", exc)
                category = "edge_case"
            state["category"] = category
            yield {"type": "category", "category": category}

            if category == "out_of_scope":
                refusal = (
                    "Esta pergunta está fora do âmbito do agente, que cobre "
                    "exclusivamente direito laboral e processamento salarial em "
                    "Portugal. Reformule, por favor, ou consulte um especialista "
                    "na área específica."
                )
                state["final_answer"] = refusal
                state["refused"] = True
                state["confidence"] = 1.0
                yield {"type": "token", "delta": refusal}
                yield {"type": "done", "state": _serializable(state)}
                return

        # EN: Build chat messages: system + optional history + current user turn.
        # PT: Monta mensagens: system + histórico opcional + pergunta atual.
        # ----- Phase: plan + tool loop ----- #
        messages: list[dict[str, Any]] = self._build_system_messages()
        for m in (history or []):
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_query})

        for iteration in range(self.max_iterations):
            state["iterations"] = iteration + 1
            yield {
                "type": "phase",
                "phase": "plan",
                "message": f"A planear ferramentas (iteração {iteration + 1})…",
            }

            if iteration == 0:
                logger.info(
                    "Agent tool routing: json_planner={} llm_provider={} client_base={}",
                    self._must_use_json_tool_plan(),
                    settings.llm_provider,
                    getattr(self.client, "base_url", "?"),
                )

            # EN: Groq path: model returns JSON with `tool_calls` array, not SDK tool_calls.
            # PT: Caminho Groq: modelo devolve JSON com array `tool_calls`, não tool_calls SDK.
            if self._must_use_json_tool_plan():
                plan_messages = self._groq_plan_messages(messages)
                try:
                    completion = await self.client.chat.completions.create(
                        model=self.model,
                        temperature=settings.llm_temperature,
                        messages=plan_messages,
                        response_format={"type": "json_object"},
                    )
                except Exception as exc:
                    logger.warning(
                        "Groq plan with json_object failed ({}); retrying without response_format",
                        exc,
                    )
                    try:
                        completion = await self.client.chat.completions.create(
                            model=self.model,
                            temperature=settings.llm_temperature,
                            messages=plan_messages,
                        )
                    except Exception as exc2:
                        logger.exception("Groq planning call failed: {}", exc2)
                        yield {"type": "error", "message": str(exc2)}
                        state["final_answer"] = "Ocorreu um erro ao contactar o modelo."
                        state["confidence"] = 0.0
                        state["refused"] = True
                        yield {"type": "done", "state": _serializable(state)}
                        return

                raw = (completion.choices[0].message.content or "{}").strip()
                try:
                    plan = _parse_json_loose(raw)
                except json.JSONDecodeError:
                    logger.warning("Groq devolveu JSON de plano inválido: {}", raw[:400])
                    yield {
                        "type": "error",
                        "message": f"O modelo não devolveu um plano JSON válido. Primeiros caracteres: {raw[:120]}…",
                    }
                    break

                tool_specs = plan.get("tool_calls")
                if not isinstance(tool_specs, list):
                    tool_specs = []
                allowed = V1_TOOL_NAMES if self.version == "v1" else V2_TOOL_NAMES
                tool_specs = [
                    t
                    for t in tool_specs
                    if isinstance(t, dict) and str(t.get("name", "")) in allowed
                ]

                messages.append({"role": "assistant", "content": raw})

                if not tool_specs:
                    break

                result_blocks: list[str] = []
                for i, spec in enumerate(tool_specs):
                    name = str(spec.get("name", ""))
                    args_raw = spec.get("arguments")
                    args_d: dict[str, Any] = (
                        args_raw if isinstance(args_raw, dict) else {}
                    )
                    trace, tool_msg, sources = await self._execute_tool_named(
                        name, args_d, f"groq-{iteration}-{i}"
                    )
                    state["tool_traces"].append(trace)
                    state["sources"].extend(sources)
                    yield {
                        "type": "tool_call",
                        "tool": trace.tool_name,
                        "args": trace.args,
                        "summary": trace.output_summary,
                        "duration_ms": trace.duration_ms,
                        "success": trace.success,
                        "error": trace.error,
                    }
                    result_blocks.append(f"**{name}**\n{tool_msg}")

                yield {
                    "type": "sources",
                    "sources": [s.model_dump() for s in state["sources"]],
                }

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Resultados das ferramentas:\n\n"
                            + "\n\n".join(result_blocks)
                            + '\n\nSe precisares de mais dados, responde de novo só com JSON '
                            '{"tool_calls":[...]}. Se já podes responder ao utilizador, '
                            'devolve {"tool_calls":[]}.'
                        ),
                    }
                )
                continue

            # EN: Branch: Chat Completions with `tools=` — works on OpenAI & compatible.
            # PT: Ramo: Chat Completions com `tools=` — funciona na OpenAI e compatíveis.
            # ---- OpenAI (native tool calling) ---- #
            try:
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    temperature=settings.llm_temperature,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
            except Exception as exc:
                logger.exception("OpenAI planning call failed: {}", exc)
                yield {"type": "error", "message": str(exc)}
                state["final_answer"] = "Ocorreu um erro ao contactar o modelo."
                state["confidence"] = 0.0
                state["refused"] = True
                yield {"type": "done", "state": _serializable(state)}
                return

            msg = completion.choices[0].message
            tool_calls = msg.tool_calls or []

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ]
                    if tool_calls
                    else None,
                }
            )

            if not tool_calls:
                if msg.content:
                    state["final_answer"] = msg.content
                break

            results = await asyncio.gather(
                *[self._execute_tool(tc) for tc in tool_calls],
                return_exceptions=False,
            )

            for tc, (trace, tool_msg, sources) in zip(tool_calls, results):
                state["tool_traces"].append(trace)
                state["sources"].extend(sources)
                yield {
                    "type": "tool_call",
                    "tool": trace.tool_name,
                    "args": trace.args,
                    "summary": trace.output_summary,
                    "duration_ms": trace.duration_ms,
                    "success": trace.success,
                    "error": trace.error,
                }
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_msg,
                    }
                )

            yield {"type": "sources", "sources": [s.model_dump() for s in state["sources"]]}

        # EN: Second-chance retrieval when the first loop returned zero sources
        #     (e.g. Tavily hiccup, empty Chroma). Skips `out_of_scope`.
        # PT: Segunda tentativa de recuperação quando o primeiro loop não trouxe
        #     fontes (ex.: falha Tavily, Chroma vazio). Ignora `out_of_scope`.
        # ----- Phase: source recovery (v2 only) ----- #
        # If the tool loop ended without any sources for a respondable
        # question, try one extra deterministic recovery before we generate
        # the answer. This dramatically reduces "sometimes refuses, sometimes
        # answers" flakiness caused by intermittent web search failures.
        if (
            self.version == "v2"
            and not state.get("sources")
            and state.get("category") not in {"out_of_scope"}
        ):
            async for ev in self._recover_sources(state, messages):
                yield ev

        # ----- Phase: generate (final answer with streaming) ----- #
        # If the loop terminated naturally with `final_answer`, stream nothing
        # because the LLM already produced text. Otherwise, force a final
        # answer using accumulated tool outputs.
        if not state.get("final_answer"):
            yield {"type": "phase", "phase": "generate", "message": "A redigir a resposta…"}
            final_instruction = (
                "Based on the tools executed, write the final answer in English, "
                "citing the sources. Keep all legal references and source titles "
                "verbatim in Portuguese (e.g. 'Art. 238.º CT', 'Lei 110/2009')."
                if self.locale == "en"
                else (
                    "Com base nas ferramentas executadas, escreve a resposta "
                    "final em português europeu, citando as fontes."
                )
            )
            messages.append(
                {
                    "role": "user",
                    "content": final_instruction,
                }
            )
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    temperature=settings.llm_temperature,
                    messages=messages,
                    stream=True,
                )
                buf: list[str] = []
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        buf.append(delta)
                        yield {"type": "token", "delta": delta}
                state["final_answer"] = "".join(buf)
            except Exception as exc:
                logger.exception("Final answer generation failed: {}", exc)
                state["final_answer"] = "Não foi possível gerar a resposta final."
                state["confidence"] = 0.0
                state["refused"] = True

        else:
            # Stream the already-produced answer in chunks for UX consistency.
            for chunk in _chunkize(state["final_answer"]):
                yield {"type": "token", "delta": chunk}

        # EN: Heuristic + optional LLM score; may replace answer with refusal only
        #     if `_should_refuse` agrees (no evidence).
        # PT: Heurística + LLM opcional; substitui por recusa só se `_should_refuse`.
        # ----- Phase: score confidence (v2 only) ----- #
        if self.version == "v2":
            yield {"type": "phase", "phase": "score", "message": "A avaliar confiança…"}
            confidence = await self._score_confidence(state)
            state["confidence"] = confidence
            yield {"type": "confidence", "score": confidence}

            if (
                confidence < settings.confidence_threshold
                and not state.get("refused")
                and self._should_refuse(state)
            ):
                yield {"type": "phase", "phase": "refuse", "message": "Confiança baixa — a recusar graciosamente…"}
                refusal = await self._compose_refusal(state)
                state["final_answer"] = refusal
                state["refused"] = True
                state["refusal_reason"] = "low_confidence"
                yield {"type": "refusal", "answer": refusal}
        else:
            state["confidence"] = 0.5
            state["refused"] = False

        yield {"type": "done", "state": _serializable(state)}

    # ---------- Phases ---------- #

    async def _classify(self, query: str) -> QuestionCategory:
        completion = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            max_tokens=10,
            messages=[
                {"role": "system", "content": "És um classificador de perguntas."},
                {"role": "user", "content": CLASSIFIER_PROMPT.format(query=query)},
            ],
        )
        raw = (completion.choices[0].message.content or "").strip().lower()
        for cat in _VALID_CATEGORIES:
            if cat in raw:
                return cat  # type: ignore[return-value]
        return "edge_case"

    def _groq_plan_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        suffix = (
            GROQ_JSON_PLAN_SUFFIX_V1
            if self.version == "v1"
            else GROQ_JSON_PLAN_SUFFIX_V2
        )
        out: list[dict[str, Any]] = []
        for m in messages:
            out.append(dict(m))
        if not out:
            return [{"role": "user", "content": suffix.strip()}]
        last = out[-1]
        if last.get("role") == "user":
            base = last.get("content") or ""
            out[-1] = {**last, "content": base + "\n\n" + suffix}
        else:
            out.append({"role": "user", "content": suffix})
        return out

    async def _execute_tool(
        self, tc: Any
    ) -> tuple[ToolCallTrace, str, list[Source]]:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        call_id = getattr(tc, "id", None) or "openai"
        return await self._execute_tool_named(tc.function.name, args, call_id)

    async def _execute_tool_named(
        self,
        name: str,
        args: dict[str, Any],
        call_id: str,
    ) -> tuple[ToolCallTrace, str, list[Source]]:
        args = dict(args)
        trace_args = dict(args)

        t0 = time.perf_counter()
        try:
            if name == "search_web":
                category = args.get("category") or "edge_case"
                res = await web_search(args.get("query", ""), category=str(category))
            elif name == "fetch_url":
                res = await fetch_and_parse(args.get("url", ""), self.http)
            elif name == "search_labor_code":
                res = await asyncio.to_thread(
                    search_labor_code, args.get("query", ""), int(args.get("k", 5))
                )
            elif name == "calculate":
                action = str(args.pop("action", "") or "")
                if "monthly_gross" in args and "gross_monthly" not in args:
                    args["gross_monthly"] = args.pop("monthly_gross")
                if action in {"holiday_subsidy", "christmas_subsidy"} and "gross_monthly" in args:
                    args["monthly_gross"] = args.pop("gross_monthly")
                res = await asyncio.to_thread(calc_tool, action, **args)
            else:
                res = {"ok": False, "error": f"Unknown tool: {name}", "summary": "", "sources": []}
        except Exception as exc:
            logger.exception("Tool {} failed: {}", name, exc)
            res = {"ok": False, "error": str(exc), "summary": "", "sources": []}

        duration_ms = int((time.perf_counter() - t0) * 1000)
        sources = res.get("sources", []) or []
        summary = res.get("summary", "") or ""
        ok = bool(res.get("ok", False))
        err = res.get("error")

        trace = ToolCallTrace(
            tool_name=name,
            args=trace_args,
            output_summary=(summary[:600] if summary else (err or ""))[:600],
            duration_ms=duration_ms,
            success=ok,
            error=err,
        )
        # Tool message content sent back to OpenAI (compact JSON-ish)
        tool_msg = json.dumps(
            {
                "ok": ok,
                "error": err,
                "summary": summary,
                "sources": [
                    {"url": s.url, "title": s.title, "domain": s.domain}
                    for s in sources
                ],
            },
            ensure_ascii=False,
        )[:6000]
        return trace, tool_msg, list(sources)

    async def _score_confidence(self, state: AgentState) -> float:
        """Heuristic confidence with optional LLM cross-check.

        The score is intentionally generous when there is real evidence to keep
        the agent consistent across runs: a citation is recognised by URL,
        domain or title — not only by literal URL match. We also treat the LLM
        side-score as an *upper bound* (never as an additional veto), since
        Llama judges occasionally output 0.4–0.5 even on solid grounded
        answers, which used to flip a respondable answer into a refusal on
        retries.
        """
        sources = state.get("sources", [])
        answer = state.get("final_answer", "")
        if not answer:
            return 0.0

        answer_low = answer.lower()

        source_score = 0.0
        if sources:
            cited_count = 0
            for s in sources:
                url = (getattr(s, "url", "") or "").lower()
                domain = (getattr(s, "domain", "") or "").lower()
                title = (getattr(s, "title", "") or "").lower()
                if url and url in answer_low:
                    cited_count += 1
                    continue
                if domain and domain in answer_low:
                    cited_count += 1
                    continue
                if title and len(title) > 6 and title in answer_low:
                    cited_count += 1
            base = 0.45 if cited_count > 0 else 0.30
            source_score = min(1.0, base + 0.12 * cited_count + 0.04 * len(sources))

        # Specificity heuristic: legal references, numbers, official entities.
        specificity = 0.0
        signals = (
            "Art.", "art.",
            "%", "€", "EUR",
            "Lei n.", "Lei n.º",
            "Decreto-Lei", "Despacho", "Portaria",
            "Código do Trabalho", "CT",
            "ACT", "DRE", "CITE",
            "Segurança Social", "Portal das Finanças",
            "/2024", "/2025", "/2026",
        )
        for sig in signals:
            if sig in answer:
                specificity += 0.04
        specificity = min(0.3, specificity)

        length_score = 0.1 if 200 < len(answer) < 4000 else 0.0
        heuristic = round(min(1.0, source_score + specificity + length_score), 3)

        # Optional LLM-side confidence as a *cross-check*: we average it in,
        # but never let it drag the score below the heuristic floor when the
        # answer already has cited official sources.
        try:
            from app.agent.prompts import CONFIDENCE_PROMPT

            src_lines = "\n".join(
                f"- {s.title} ({s.url})" for s in sources[:6]
            )
            completion = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                max_tokens=8,
                messages=[
                    {
                        "role": "user",
                        "content": CONFIDENCE_PROMPT.format(
                            query=state.get("user_query", ""),
                            answer=answer[:2000],
                            sources=src_lines or "(nenhuma)",
                        ),
                    }
                ],
            )
            raw = (completion.choices[0].message.content or "0.5").strip()
            try:
                llm_score = max(0.0, min(1.0, float(raw.split()[0].replace(",", "."))))
            except (ValueError, IndexError):
                llm_score = 0.5
            blended = (heuristic + llm_score) / 2.0
            # Floor: if we have at least one official source AND the heuristic
            # already passes the threshold, we don't let a stochastic LLM
            # judge knock the answer below it.
            if sources and heuristic >= settings.confidence_threshold:
                blended = max(blended, settings.confidence_threshold)
            return round(min(1.0, blended), 3)
        except Exception:
            return heuristic

    async def _recover_sources(
        self,
        state: AgentState,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        """Best-effort second pass to obtain at least one official source.

        Strategy by category:
        - labor_code / edge_case: search_labor_code first, then search_web.
        - tax / social_security / salary_calc: search_web with category hint.
        - everything else: a single search_web with a generic hint.

        Each attempt that succeeds with sources is appended to the agent
        state and the tool result is also fed back into `messages` so the
        generation step can cite it.
        """
        category = state.get("category") or "edge_case"
        query = state.get("user_query", "")
        if not query:
            return

        attempts: list[tuple[str, dict[str, Any]]] = []
        if category in {"labor_code", "edge_case"}:
            attempts.append(("search_labor_code", {"query": query, "k": 5}))
            attempts.append(("search_web", {"query": query, "category": category}))
        elif category in {"tax", "social_security", "salary_calc"}:
            attempts.append(("search_web", {"query": query, "category": category}))
        else:
            attempts.append(("search_web", {"query": query, "category": "edge_case"}))

        yield {
            "type": "phase",
            "phase": "recover",
            "message": "A tentar recuperar fontes oficiais…",
        }

        for i, (name, args) in enumerate(attempts):
            trace, tool_msg, sources = await self._execute_tool_named(
                name, args, f"recover-{i}"
            )
            state["tool_traces"].append(trace)
            state["sources"].extend(sources)
            yield {
                "type": "tool_call",
                "tool": trace.tool_name,
                "args": trace.args,
                "summary": trace.output_summary,
                "duration_ms": trace.duration_ms,
                "success": trace.success,
                "error": trace.error,
            }
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"[Recuperação automática] Resultados de {name}:\n{tool_msg}"
                    ),
                }
            )
            if sources:
                break

        if state.get("sources"):
            yield {
                "type": "sources",
                "sources": [s.model_dump() for s in state["sources"]],
            }

    def _should_refuse(self, state: AgentState) -> bool:
        """Decide whether a low-confidence answer should be *replaced* by a
        graceful refusal, or kept (possibly with a hedging note).

        We refuse only when there is no real evidence behind the answer:
        - empty / placeholder answer, or
        - no sources at all, or
        - all tool calls failed and the answer is short/generic.

        For partially-supported answers (some official sources, substantive
        content) we keep the answer to avoid the flaky behaviour where the
        same question would sometimes refuse and sometimes respond.
        """
        answer = (state.get("final_answer") or "").strip()
        if not answer or len(answer) < 40:
            return True

        sources = state.get("sources", []) or []
        traces = state.get("tool_traces", []) or []

        official_domains = {
            "act.gov.pt",
            "portal.act.gov.pt",
            "info.portaldasfinancas.gov.pt",
            "portaldasfinancas.gov.pt",
            "diariodarepublica.pt",
            "dre.pt",
            "cite.gov.pt",
            "seg-social.pt",
            "www.seg-social.pt",
        }
        has_official_source = any(
            (getattr(s, "domain", "") or "").lower() in official_domains
            or any(d in (getattr(s, "url", "") or "").lower() for d in official_domains)
            for s in sources
        )
        if has_official_source:
            return False

        if not sources:
            return True

        all_tools_failed = bool(traces) and all(
            not getattr(t, "success", False) for t in traces
        )
        if all_tools_failed:
            return True

        return False

    async def _compose_refusal(self, state: AgentState) -> str:
        msg_history = (
            f"Pergunta: {state.get('user_query', '')}\n"
            f"Pesquisas tentadas: {len(state.get('tool_traces', []))}\n"
            f"Fontes encontradas: {len(state.get('sources', []))}\n"
            f"Resposta gerada (potencialmente fraca): {state.get('final_answer', '')[:600]}"
        )
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": REFUSAL_INSTRUCTION},
                    {"role": "user", "content": msg_history},
                ],
            )
            return (completion.choices[0].message.content or "").strip() or (
                "Não consegui responder com confiança a esta pergunta com base "
                "em fontes oficiais. Recomendo consulta direta a ACT, Segurança "
                "Social, Portal das Finanças ou advogado."
            )
        except Exception:
            return (
                "Não consegui responder com confiança a esta pergunta com base "
                "em fontes oficiais. Recomendo consulta direta a ACT, Segurança "
                "Social, Portal das Finanças ou advogado."
            )


# EN: Pure functions for JSON repair and SSE chunking — no I/O.
# PT: Funções puras para reparar JSON e fatiar texto para SSE — sem I/O.
# ----- Helpers ----- #


def _parse_json_loose(raw: str) -> dict[str, Any]:
    """EN: Strip fences / chatter so Groq JSON tool plans still parse.
    PT: Remove cercas ``` e texto extra para o JSON do Groq ser parseável."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


def _chunkize(text: str, size: int = 32) -> list[str]:
    # EN: Fake streaming for answers already fully known (early-exit path).
    # PT: Simula stream para respostas já completas (caminho de saída antecipada).
    return [text[i : i + size] for i in range(0, len(text), size)]


def _serializable(state: AgentState) -> dict[str, Any]:
    # EN: Pydantic models → dict for JSON serialization in SSE `done` event.
    # PT: Modelos Pydantic → dict para serializar JSON no evento SSE `done`.
    return {
        "user_query": state.get("user_query", ""),
        "conversation_id": state.get("conversation_id", ""),
        "category": state.get("category"),
        "final_answer": state.get("final_answer", ""),
        "confidence": state.get("confidence", 0.0),
        "refused": bool(state.get("refused", False)),
        "refusal_reason": state.get("refusal_reason"),
        "iterations": state.get("iterations", 0),
        "sources": [
            s.model_dump() if isinstance(s, Source) else s
            for s in state.get("sources", [])
        ],
        "tool_traces": [
            t.model_dump() if isinstance(t, ToolCallTrace) else t
            for t in state.get("tool_traces", [])
        ],
        "agent_version": state.get("agent_version", "v2"),
    }
