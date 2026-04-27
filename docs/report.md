# HomoDeus AI Engineer Challenge — Relatório técnico

**Autor:** Pedro Soler · **Repositório:** este projeto · **Modelos default:** `llama-3.3-70b-versatile` via Groq (agente + juiz); alternativa `LLM_PROVIDER=openai` com `gpt-4o-mini` / `gpt-4o`. **Embeddings:** MiniLM local via ChromaDB por defeito (`EMBEDDINGS_PROVIDER=local`); opcional OpenAI `text-embedding-3-small` para ligeiro ganho de recall.

*Documento alinhado ao briefing (PDF): arquitetura, avaliação, próximos passos ≤ 1 semana; máx. ~2 páginas em Markdown.*

---

## 1. Arquitetura

Pipeline assíncrono v2 com estado tipado e eventos SSE:

```
classify → plan (tools) → execute_tools (paralelo, loop ≤ N) → generate (stream) → confidence → recusa opcional
```

**Decisões principais**

1. **Anti-alucinação por construção.** IRS, TSU e subsídios passam por [`calculator.py`](../backend/app/agent/tools/calculator.py). O LLM não faz contas; taxas TSU (Lei 110/2009) e tabela IRS (Despacho 236-A/2025) vêm com `Source` oficial.
2. **Encaminhamento por categoria.** Classificador etiqueta `tax | social_security | labor_code | salary_calc | edge_case | out_of_scope`; o `web_search` filtra domínios Tavily (Finanças, DRE, ACT, CITE, Seg. Social).
3. **Híbrido vetor + web.** O CT é obtido do PDF oficial, partido por **marcadores de artigo** e indexado em ChromaDB com embeddings **locais** (default); isto devolve citações com `Art. N.º` explícito.
4. **Tool calling.** API nativa em fornecedores compatíveis; em Groq usa-se plano JSON estável. Traces expostos na UI (`ToolCallTrace`).
5. **Confiança e recusa (v2).** Score híbrido (heurística + autoavaliação LLM) com limiar configurável; recusa só quando não há evidência suficiente — ver README para recuperação de fontes e testes de consistência.
6. **Estado em Redis** (fallback memória); API preparada para escalar horizontalmente.

---

## 2. Suite de avaliação

Casos anotados em [`test_cases.py`](../backend/app/evaluation/test_cases.py) (perguntas do briefing + edge/refusal). Métricas agregadas pelo harness e, quando há chave, **LLM-as-judge** em JSON; senão, heurística em [`judge.py`](../backend/app/evaluation/judge.py).

| Métrica | Significado |
|---------|-------------|
| `correctness` | Alinhamento factual vs. factos de referência |
| `coverage` | Cobertura dos `ground_truth_facts` |
| `citation_quality` | Uso de domínios/URLs oficiais |
| `refusal_accuracy` | Recusa adequada quando `expects_refusal` |
| `tool_call_accuracy` | Coerência ferramentas ↔ domínios esperados |
| Latência p50/p95 | Por caso |

Correr: `python -m app.evaluation.harness --version both --concurrency 4` (pasta `backend`). Resultados em `backend/evaluation_results/`; UI em `/eval`.

*Os números exemplo em `v1_vs_v2.json` podem ser placeholders — voltar a correr o harness para métricas reais.*

---

## 3. v1 → v2 (melhoria mensurável — bonus do briefing)

- **v1:** só `search_web`, prompt mínimo, sem índice CT dedicado, sem calculadora determinística, sem gating de confiança completo.
- **v2:** quatro ferramentas, índice por artigo, regras de fundamentação, scoring + política de recusa e recuperação de fontes.

Ganhos esperados: menos erros numéricos (calculator), melhor `citation_quality` (artigos CT + DRE/Finanças), melhor `refusal_accuracy` (recusa quando não há base). Trade-off típico: latência ligeiramente maior por mais passos e juiz.

---

## 4. Escala (nota curta)

Backend stateless + Redis partilhado; async end-to-end. Para tráfego muito alto, o Chroma em disco por réplica pode ser substituído por vector store gerido (Qdrant/Pinecone) e cache semântica — ver abaixo.

---

## 5. Próximos passos (com +1 semana)

1. **Vector store gerido** e embeddings centralizados para múltiplas réplicas.
2. **Cache de respostas** (Redis + hash de pergunta normalizada) para FAQ repetidas.
3. **Re-ranker** (ex. Cohere) sobre hits web/vector antes do contexto LLM.
4. **CI:** harness no PR com limiar de regressão em `correctness_avg`.
5. **Casos adversariais** gerados para stressar recusa e citações.
6. **Calibração do juiz** com amostra revista por especialista (opcional).

---

## 6. Conformidade com a submissão (PDF p. 8)

| Entregável | Onde |
|------------|------|
| Repositório + README (< 5 min local) | Raiz: [`README.md`](../README.md) — clone, `.env`, Docker ou local, indexer, URLs. |
| Relatório ≤ 2 páginas | Este ficheiro [`docs/report.md`](report.md). |
