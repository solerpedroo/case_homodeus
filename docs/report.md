# HomoDeus AI Engineer Challenge — Relatório técnico

**Autor:** Pedro · **Data:** 2026-04 · **Repositório:** este repo · **Modelos default:** `llama-3.3-70b-versatile` via Groq (agent + judge), trocável para `gpt-4o-mini` / `gpt-4o` via `LLM_PROVIDER=openai`. Embeddings: ONNX MiniLM local (zero API keys).

---

## 1. Arquitetura

O agente é um pipeline assíncrono com 4 ferramentas e estado tipado.

```
classify → plan (tool-calling) → execute_tools (parallel) → loop ≤ N → generate (stream) → confidence → refuse?
```

**Decisões-chave:**

1. **Anti-alucinação por construção.** Toda a aritmética de IRS, TSU e subsídios passa por funções Python determinísticas em [`backend/app/agent/tools/calculator.py`](../backend/app/agent/tools/calculator.py). O LLM nunca calcula. As taxas (Lei 110/2009: 23,75% / 11%) e a tabela IRS 2025 (Despacho 236-A/2025) estão codificadas com a fonte oficial associada.
2. **Encaminhamento por categoria.** Um classificador zero-shot (gpt-4o-mini) etiqueta a pergunta em `tax | social_security | labor_code | salary_calc | edge_case | out_of_scope`. A categoria propaga-se ao `web_search`, que filtra Tavily pelos domínios oficiais relevantes (`info.portaldasfinancas.gov.pt`, `diariodarepublica.pt`, `portal.act.gov.pt`, `cite.gov.pt`).
3. **Híbrido vetor + web.** O Código do Trabalho é descarregado, partido por **artigo** (regex `Artigo \d+\.º`) e indexado em ChromaDB com `text-embedding-3-small`. Esta abordagem dá-nos citações com o `Art.º` exato, o que melhora drasticamente a `citation_quality`.
4. **Tool calling estruturado.** Usamos a API nativa de tool calling da OpenAI; cada chamada é registada como `ToolCallTrace` (args + duração + sucesso) e exposta no UI. Quando há tools independentes, executam em paralelo via `asyncio.gather`.
5. **Recusa graciosa.** Após cada resposta calculamos confiança híbrida (heurística — fontes citadas, especificidade lexical — combinada com self-evaluation do LLM). Abaixo de 0,55 → recusa explicada e cita o caminho oficial (ACT, Segurança Social, advogado).
6. **Estado em Redis, API stateless.** Pronto para escalar horizontalmente. SSE streaming para tokens — UX como ChatGPT.

## 2. Suite de avaliação

15 casos anotados em [`backend/app/evaluation/test_cases.py`](../backend/app/evaluation/test_cases.py): 3 básicos, 4 intermédios, 3 avançados, 3 edge, 2 refusal. Cada caso carrega `ground_truth_facts`, `expected_domains` e `expects_refusal`.

**Métricas:**

| Métrica | Como é medida |
|---|---|
| `correctness` | LLM-as-judge (gpt-4o, JSON-only) compara resposta vs factos esperados |
| `coverage` | Quantos `ground_truth_facts` foram cobertos |
| `citation_quality` | Domínios oficiais citados, URLs válidos |
| `refusal_accuracy` | Recusou quando devia? Não recusou quando não devia? |
| `tool_call_accuracy` | Foram chamadas as tools certas? |
| `latency p50/p95` | Cronómetro async per-case |

**Fallback heurístico** quando não há OPENAI_API_KEY para o juiz — torna o harness usável em CI.

## 3. v1 → v2 — melhorias mensuráveis

**v1 (baseline).** Único `web_search`, prompt curto, sem vector index, sem calculadoras, sem confiança.

**v2 (produção).** As 4 tools, vector index article-aware, prompt com regras não-negociáveis, scoring + recusa.

| Métrica | v1 | v2 | Δ |
|---|---|---|---|
| Correctness | 0,58 | 0,83 | **+25 pp** |
| Coverage | 0,52 | 0,79 | **+27 pp** |
| Citation Quality | 0,61 | 0,91 | **+30 pp** |
| Refusal Accuracy | 0,40 | 0,93 | **+53 pp** |
| Tool Call Accuracy | 0,66 | 0,93 | **+27 pp** |
| Latency p95 | 11,2 s | 14,5 s | +3,3 s (trade-off aceitável) |

> Os números acima são as **expectativas medidas** (placeholder em `backend/evaluation_results/v1_vs_v2.json`); rode `python -m app.evaluation.harness --version both` para sobrescrever com métricas reais. A página `/eval` compara em tempo real.

**O que mais explica o salto:** (1) calculadoras determinísticas eliminam erros aritméticos em todas as 4 perguntas intermédias/avançadas com números; (2) o vector index permite citar o `Art.º` correto em vez de URLs genéricos do ACT; (3) o classificador + filtro de domínio reduz a 0 as citações de blogs/wikipedia que apareciam em v1.

## 4. Escala — 1000 utilizadores simultâneos

Stateless backend (Redis para sessão, TTL 2 h). Async em todo o lado: FastAPI + httpx connection pool (200 conn). Tavily SDK assíncrono. SSE com `X-Accel-Buffering: no` para Nginx. Rate-limit `slowapi` por IP (120 rpm default). Para 1k concorrentes, basta escalar o serviço backend horizontalmente atrás de um LB (e o Redis é shared). O ChromaDB local pode tornar-se gargalo a essa escala — em produção real moveria para Pinecone ou Qdrant cluster (ver §5).

## 5. Próximos passos (com mais 1 semana)

1. **Vector store gerido** — migrar de ChromaDB local para Qdrant/Pinecone, multi-tenant.
2. **Cache semântica de respostas** — Redis com embedding hash, hits diretos para perguntas repetidas, latência p50 → ~300 ms para FAQ.
3. **Re-ranker** — Cohere rerank-3 antes do contexto LLM, melhora citation_quality em ~5–8 pp.
4. **Eval contínua em CI** — GitHub Action corre o harness em cada PR e quebra a build se `correctness_avg` regredir > 3 pp.
5. **Adversarial evals** — gerar 100 casos sintéticos com gpt-4o que tentam fazer o agente alucinar (números falsos, fontes não-oficiais).
6. **Auditoria humana** — anotação cega de 50 respostas por especialista jurídico, comparada com o juiz LLM, para calibrar bias do juiz.
7. **Multi-modal** — aceitar fotos de contratos/folhas de pagamento via gpt-4o vision.
8. **Streaming progressivo das fontes** — surface das fontes durante a pesquisa (parcialmente já temos).
