"""Agent orchestrator — LangGraph-style state machine implemented as an
async pipeline that emits structured events.

Two versions:
- v1 (baseline): single `web_search` tool, basic ReAct, no calculators, no
  vector index, no confidence-based refusal.
- v2 (production): full pipeline below.

v2 pipeline:
    classify  →  plan  →  execute_tools  →  (loop ≤ N)  →  generate  →  score → done

Why a hand-rolled state machine vs raw LangGraph? Streaming token-level output
through LangGraph's runtime is awkward; orchestrating a few well-typed async
steps keeps the code small (~300 LOC) and easy to read in <30 minutes.

All state mutations go through `AgentState` so there's a single source of truth
for serialization and tracing.
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


_VALID_CATEGORIES: tuple[QuestionCategory, ...] = (
    "tax",
    "social_security",
    "labor_code",
    "salary_calc",
    "edge_case",
    "out_of_scope",
)


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

V1_TOOLS = [V2_TOOLS[0]]  # only basic web search

V1_TOOL_NAMES = frozenset({"search_web"})
V2_TOOL_NAMES = frozenset({"search_web", "fetch_url", "search_labor_code", "calculate"})


class LaborAgent:
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

        # ----- Phase: score confidence (v2 only) ----- #
        if self.version == "v2":
            yield {"type": "phase", "phase": "score", "message": "A avaliar confiança…"}
            confidence = await self._score_confidence(state)
            state["confidence"] = confidence
            yield {"type": "confidence", "score": confidence}

            if confidence < settings.confidence_threshold and not state.get("refused"):
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
        sources = state.get("sources", [])
        answer = state.get("final_answer", "")
        if not answer:
            return 0.0

        source_score = 0.0
        if sources:
            cited_count = sum(1 for s in sources if s.url and s.url in answer)
            source_score = min(1.0, 0.4 + 0.15 * cited_count + 0.05 * len(sources))

        # Specificity heuristic: presence of article numbers, percentages, EUR values
        specificity = 0.0
        signals = ["Art.", "art.", "%", "€", "EUR", "Lei n.", "Despacho", "/2024", "/2025"]
        for sig in signals:
            if sig in answer:
                specificity += 0.05
        specificity = min(0.3, specificity)

        length_score = 0.1 if 200 < len(answer) < 4000 else 0.0
        heuristic = round(min(1.0, source_score + specificity + length_score), 3)

        # Optional LLM-side confidence as cross-check (cheap call).
        try:
            from app.agent.prompts import CONFIDENCE_PROMPT

            src_lines = "\n".join(f"- {s.title} ({s.url})" for s in sources[:6])
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
            return round((heuristic + llm_score) / 2.0, 3)
        except Exception:
            return heuristic

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


# ----- Helpers ----- #


def _parse_json_loose(raw: str) -> dict[str, Any]:
    """Strip markdown fences / prefix text so Groq JSON plans still parse."""
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
    return [text[i : i + size] for i in range(0, len(text), size)]


def _serializable(state: AgentState) -> dict[str, Any]:
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
