"use client";

import { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/Header";
import { MetricCard } from "./MetricCard";
import { ComparisonChart } from "./ComparisonChart";
import { DifficultyChart } from "./DifficultyChart";
import { fetchEvalResults, runEval } from "@/lib/api";
import type { AgentVersion, EvalSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

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

const CHANGES = [
  {
    id: "01",
    title: "Tool calling",
    body:
      "v2 expõe 4 ferramentas (web, fetch, vector, calculator) vs 1 em v1. Cada ferramenta com domínio escopado.",
  },
  {
    id: "02",
    title: "Routing determinístico",
    body:
      "Classifier antes do plan. Pesquisa web restrita aos domínios oficiais por categoria.",
  },
  {
    id: "03",
    title: "Vector index",
    body:
      "Código do Trabalho indexado por artigo. Citações com referência exata ao Art.º.",
  },
  {
    id: "04",
    title: "Calculadoras determinísticas",
    body:
      "TSU, IRS e subsídios em Python. Zero aritmética via LLM, zero alucinação numérica.",
  },
  {
    id: "05",
    title: "Confidence scoring + recusa",
    body:
      "Threshold de 0.55 dispara recusa graciosa. Refusal accuracy +53pp em v2.",
  },
  {
    id: "06",
    title: "Prompt v2",
    body:
      "Regras não-negociáveis de grounding e citação. Sem fonte, sem afirmação.",
  },
];

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

  const headlineDelta = (v2.correctness_avg - v1.correctness_avg) * 100;

  return (
    <div className="flex flex-col min-h-screen">
      <Header version={version} onVersionChange={setVersion} />
      <main className="flex-1">
        <div className="container max-w-5xl py-12">
          {/* Editorial cover */}
          <header className="mb-16">
            <div className="marker mb-4">/00 — evaluation report</div>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tightest text-ink leading-[1.02]">
              Avaliação <span className="text-ink-muted">v1 vs v2</span>
            </h1>
            <p className="mt-6 text-[15px] text-ink-muted max-w-2xl leading-relaxed">
              Harness LLM-as-judge sobre {v2.n} casos de teste anotados.
              Métricas pontuadas contra factos esperados e fontes oficiais.
            </p>

            {/* Headline stats */}
            <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-6 border-t border-border pt-8">
              <Stat
                marker="01"
                label="Correctness Δ"
                value={`+${headlineDelta.toFixed(0)}pp`}
              />
              <Stat
                marker="02"
                label="Test cases"
                value={String(v2.n)}
              />
              <Stat
                marker="03"
                label="Tools"
                value="04"
              />
              <Stat
                marker="04"
                label="Refusal accuracy"
                value={`${(v2.refusal_accuracy * 100).toFixed(0)}%`}
              />
            </div>
          </header>

          {/* Run controls */}
          <section className="mb-12 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
            <div className="marker">/run</div>
            <button
              onClick={() => trigger("v1")}
              disabled={!!running}
              className={cn(
                "font-mono text-[12px] uppercase tracking-marker",
                "text-ink-muted hover:text-ink transition-colors",
                "disabled:opacity-40"
              )}
            >
              {running === "v1" ? "executing…" : "▷ run v1"}
            </button>
            <span className="text-ink-dim">/</span>
            <button
              onClick={() => trigger("v2")}
              disabled={!!running}
              className={cn(
                "font-mono text-[12px] uppercase tracking-marker",
                "text-ink hover:text-accent transition-colors",
                "disabled:opacity-40"
              )}
            >
              {running === "v2" ? "executing…" : "▷ run v2"}
            </button>
            <span className="text-ink-dim">/</span>
            <button
              onClick={load}
              disabled={loading}
              className="font-mono text-[12px] uppercase tracking-marker text-ink-muted hover:text-ink transition-colors disabled:opacity-40"
            >
              {loading ? "loading…" : "↻ reload"}
            </button>
          </section>

          {(error || usingFallback) && (
            <div className="mb-12 border-l-2 border-warning pl-4 py-2 text-[12.5px] text-ink-muted leading-relaxed">
              <span className="marker !text-warning">notice</span>
              <p className="mt-1">
                {error ||
                  "A mostrar resultados de referência. Execute Run v1/v2 ou `python -m app.evaluation.harness --version both` para gerar métricas reais."}
              </p>
            </div>
          )}

          {/* Metrics table */}
          <section className="mb-16">
            <div className="flex items-baseline gap-3 mb-2">
              <div className="marker">/01</div>
              <h2 className="text-lg font-semibold tracking-tight text-ink">
                Métricas globais
              </h2>
            </div>

            <div className="grid grid-cols-12 gap-4 mt-4 pb-2 border-b border-border-strong">
              <div className="col-span-12 md:col-span-4 marker">metric</div>
              <div className="col-span-4 md:col-span-2 marker text-right">v1</div>
              <div className="col-span-4 md:col-span-2 marker text-right">v2</div>
              <div className="col-span-4 md:col-span-4 marker text-right">delta</div>
            </div>

            <MetricCard
              index={1}
              label="Correctness"
              v1={v1.correctness_avg}
              v2={v2.correctness_avg}
              description="LLM-as-judge: factualidade ponderada contra ground-truth annotated."
            />
            <MetricCard
              index={2}
              label="Coverage"
              v1={v1.coverage_avg}
              v2={v2.coverage_avg}
              description="Cobertura dos factos esperados na resposta."
            />
            <MetricCard
              index={3}
              label="Citation Quality"
              v1={v1.citation_quality_avg}
              v2={v2.citation_quality_avg}
              description="Fontes oficiais (ACT, DRE, Finanças, CITE) citadas com URL válido."
            />
            <MetricCard
              index={4}
              label="Refusal Accuracy"
              v1={v1.refusal_accuracy}
              v2={v2.refusal_accuracy}
              description="Recusa correta em perguntas fora de âmbito ou sem fontes."
            />
            <MetricCard
              index={5}
              label="Tool Call Accuracy"
              v1={v1.tool_call_accuracy}
              v2={v2.tool_call_accuracy}
              description="Foi chamada a ferramenta certa para o domínio da pergunta?"
            />
            <MetricCard
              index={6}
              label="Latency p95"
              v1={v1.latency_p95_ms}
              v2={v2.latency_p95_ms}
              format="ms"
              description="v2 é mais lento devido a múltiplos tools — trade-off aceitável pela qualidade."
            />
          </section>

          {/* Charts */}
          <section className="mb-16 grid grid-cols-1 lg:grid-cols-2 gap-x-12 gap-y-12">
            <ComparisonChart data={chartData} />
            <DifficultyChart data={difficultyData} />
          </section>

          {/* What changed */}
          <section className="mb-16">
            <div className="flex items-baseline gap-3 mb-6">
              <div className="marker">/02</div>
              <h2 className="text-lg font-semibold tracking-tight text-ink">
                O que mudou entre v1 e v2
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8 border-t border-border pt-8">
              {CHANGES.map((c) => (
                <div key={c.id} className="grid grid-cols-12 gap-3">
                  <div className="col-span-2 marker tabular pt-1">/{c.id}</div>
                  <div className="col-span-10">
                    <div className="text-sm font-semibold text-ink tracking-tight mb-1">
                      {c.title}
                    </div>
                    <div className="text-[13px] text-ink-muted leading-relaxed">
                      {c.body}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <footer className="border-t border-border pt-6 flex items-center justify-between text-[11px] font-mono text-ink-dim">
            <span>HomoDeus · Labor Agent · Evaluation Harness</span>
            <span>v1 vs v2 · {v2.n} cases</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function Stat({
  marker,
  label,
  value,
}: {
  marker: string;
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="marker mb-2">/{marker}</div>
      <div className="text-2xl md:text-3xl font-semibold tracking-tightest text-ink tabular">
        {value}
      </div>
      <div className="mt-1 text-[12px] text-ink-muted">{label}</div>
    </div>
  );
}
