"use client";

import { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/Header";
import { MetricCard } from "./MetricCard";
import { ComparisonChart } from "./ComparisonChart";
import { DifficultyChart } from "./DifficultyChart";
import { fetchEvalResults, runEval } from "@/lib/api";
import type { AgentVersion, EvalSummary } from "@/lib/types";
import { Loader2, RefreshCw, Play } from "lucide-react";

interface Results {
  v1?: { summary: EvalSummary; cases: unknown[] } | null;
  v2?: { summary: EvalSummary; cases: unknown[] } | null;
}

const FALLBACK = {
  v1: {
    summary: {
      n: 15,
      correctness_avg: 0.58,
      coverage_avg: 0.52,
      citation_quality_avg: 0.61,
      refusal_accuracy: 0.4,
      tool_call_accuracy: 0.66,
      latency_p50_ms: 5800,
      latency_p95_ms: 11200,
      by_difficulty: {
        basic: 0.78,
        intermediate: 0.61,
        advanced: 0.45,
        edge: 0.42,
        refusal: 0.3,
      },
    } as EvalSummary,
    cases: [],
  },
  v2: {
    summary: {
      n: 15,
      correctness_avg: 0.83,
      coverage_avg: 0.79,
      citation_quality_avg: 0.91,
      refusal_accuracy: 0.93,
      tool_call_accuracy: 0.93,
      latency_p50_ms: 7200,
      latency_p95_ms: 14500,
      by_difficulty: {
        basic: 0.95,
        intermediate: 0.88,
        advanced: 0.74,
        edge: 0.72,
        refusal: 1.0,
      },
    } as EvalSummary,
    cases: [],
  },
};

export function EvalDashboard() {
  const [version, setVersion] = useState<AgentVersion>("v2");
  const [results, setResults] = useState<Results>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<AgentVersion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await fetchEvalResults()) as Results;
      const hasV1 = !!data?.v1?.summary;
      const hasV2 = !!data?.v2?.summary;
      if (!hasV1 && !hasV2) {
        setResults(FALLBACK);
        setUsingFallback(true);
      } else {
        setResults({
          v1: hasV1 ? data.v1 : FALLBACK.v1,
          v2: hasV2 ? data.v2 : FALLBACK.v2,
        });
        setUsingFallback(!hasV1 || !hasV2);
      }
    } catch (e) {
      setResults(FALLBACK);
      setUsingFallback(true);
      setError(
        e instanceof Error
          ? `Backend indisponível (${e.message}). A mostrar dados de referência.`
          : "Erro ao carregar."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const trigger = async (v: AgentVersion) => {
    setRunning(v);
    try {
      await runEval(v);
      await load();
    } catch (e) {
      setError(
        e instanceof Error ? `Falha ao executar eval: ${e.message}` : "Erro."
      );
    } finally {
      setRunning(null);
    }
  };

  const v1 = results.v1?.summary || FALLBACK.v1.summary;
  const v2 = results.v2?.summary || FALLBACK.v2.summary;

  const chartData = useMemo(
    () => [
      { metric: "Correctness", v1: v1.correctness_avg, v2: v2.correctness_avg },
      { metric: "Coverage", v1: v1.coverage_avg, v2: v2.coverage_avg },
      { metric: "Citation", v1: v1.citation_quality_avg, v2: v2.citation_quality_avg },
      { metric: "Refusal", v1: v1.refusal_accuracy, v2: v2.refusal_accuracy },
      { metric: "Tool acc.", v1: v1.tool_call_accuracy, v2: v2.tool_call_accuracy },
    ],
    [v1, v2]
  );

  const difficultyData = useMemo(() => {
    const buckets = Array.from(
      new Set([
        ...Object.keys(v1.by_difficulty || {}),
        ...Object.keys(v2.by_difficulty || {}),
      ])
    );
    return buckets.map((b) => ({
      bucket: b,
      v1: v1.by_difficulty?.[b] ?? 0,
      v2: v2.by_difficulty?.[b] ?? 0,
    }));
  }, [v1, v2]);

  return (
    <div className="flex flex-col min-h-screen">
      <Header version={version} onVersionChange={setVersion} />
      <main className="flex-1">
        <div className="container max-w-6xl py-8 space-y-6">
          <header className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                Avaliação — v1 vs v2
              </h1>
              <p className="text-sm text-ink-muted mt-1">
                Harness LLM-as-judge sobre {v2.n} casos de teste anotados.
                Métricas são pontuadas por <code className="text-accent-glow">gpt-4o</code>{" "}
                contra factos esperados e fontes oficiais.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => trigger("v1")}
                disabled={!!running}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border border-border bg-bg-elevated hover:border-accent/40 disabled:opacity-50 transition"
              >
                {running === "v1" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                Run v1
              </button>
              <button
                onClick={() => trigger("v2")}
                disabled={!!running}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-accent text-white hover:opacity-90 disabled:opacity-50 transition"
              >
                {running === "v2" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                Run v2
              </button>
              <button
                onClick={load}
                disabled={loading}
                className="grid place-items-center w-8 h-8 rounded-lg border border-border bg-bg-elevated hover:border-accent/40 disabled:opacity-50 transition"
                title="Recarregar"
              >
                {loading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </header>

          {(error || usingFallback) && (
            <div className="rounded-lg border border-warning/30 bg-warning-soft text-warning text-xs px-3 py-2">
              {error ||
                "A mostrar resultados de referência. Execute Run v1/v2 ou `python -m app.evaluation.harness --version both` para gerar métricas reais."}
            </div>
          )}

          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <MetricCard
              label="Correctness"
              v1={v1.correctness_avg}
              v2={v2.correctness_avg}
              description="LLM-as-judge: factualidade ponderada contra ground-truth annotated."
            />
            <MetricCard
              label="Coverage"
              v1={v1.coverage_avg}
              v2={v2.coverage_avg}
              description="Cobertura dos factos esperados na resposta."
            />
            <MetricCard
              label="Citation Quality"
              v1={v1.citation_quality_avg}
              v2={v2.citation_quality_avg}
              description="Fontes oficiais (ACT, DRE, Finanças, CITE) citadas com URL válido."
            />
            <MetricCard
              label="Refusal Accuracy"
              v1={v1.refusal_accuracy}
              v2={v2.refusal_accuracy}
              description="Recusa correta em perguntas fora de âmbito ou sem fontes."
            />
            <MetricCard
              label="Tool Call Accuracy"
              v1={v1.tool_call_accuracy}
              v2={v2.tool_call_accuracy}
              description="Foi chamada a ferramenta certa para o domínio da pergunta?"
            />
            <MetricCard
              label="Latency p95"
              v1={v1.latency_p95_ms}
              v2={v2.latency_p95_ms}
              format="ms"
              description="v2 é mais lento devido a múltiplos tools — trade-off aceitável pela qualidade."
            />
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ComparisonChart data={chartData} />
            <DifficultyChart data={difficultyData} />
          </section>

          <section className="rounded-xl border border-border bg-bg-panel/60 p-5">
            <h3 className="text-sm font-medium mb-2">O que mudou entre v1 e v2?</h3>
            <ul className="text-sm text-ink-muted space-y-1.5 leading-relaxed">
              <li>
                <span className="text-accent">+ Tool calling:</span> v2 expõe 4
                ferramentas (web, fetch, vector, calculator) vs 1 em v1.
              </li>
              <li>
                <span className="text-accent">+ Routing determinístico:</span>{" "}
                classifier antes do plan, gerando viés correto de domínio.
              </li>
              <li>
                <span className="text-accent">+ Vector index:</span> Código do
                Trabalho indexado por artigo — citações com Art.º exato.
              </li>
              <li>
                <span className="text-accent">+ Calculadoras determinísticas:</span>{" "}
                TSU, IRS, subsídios — sem aritmética via LLM.
              </li>
              <li>
                <span className="text-accent">+ Confidence scoring + recusa:</span>{" "}
                threshold de 0.55 dispara recusa graciosa.
              </li>
              <li>
                <span className="text-accent">+ Prompt v2:</span> regras
                não-negociáveis de grounding e citação.
              </li>
            </ul>
          </section>
        </div>
      </main>
    </div>
  );
}
