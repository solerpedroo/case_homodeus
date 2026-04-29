"use client";

/**
 * EN: Evaluation page body — loads persisted JSON results, shows MetricCards
 *     and charts, triggers `runEval` POST for v1/v2.
 * PT: Corpo da página /eval — carrega resultados JSON, cartões e gráficos,
 *     dispara `runEval`.
 */

import { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/Header";
import { MetricCard } from "./MetricCard";
import { ComparisonChart } from "./ComparisonChart";
import { DifficultyChart } from "./DifficultyChart";
import { fetchEvalResults, runEval } from "@/lib/api";
import type { AgentVersion, EvalSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

interface Results {
  v1?: { summary: EvalSummary; cases: unknown[] } | null;
  v2?: { summary: EvalSummary; cases: unknown[] } | null;
}

export function EvalDashboard() {
  const t = useT();
  const [version, setVersion] = useState<AgentVersion>("v2");
  const [results, setResults] = useState<Results>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<AgentVersion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missingResults, setMissingResults] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await fetchEvalResults()) as Results;
      const hasV1 = !!data?.v1?.summary;
      const hasV2 = !!data?.v2?.summary;
      setResults(data || {});
      setMissingResults(!hasV1 && !hasV2);
    } catch (e) {
      setResults({});
      setMissingResults(true);
      setError(
        e instanceof Error ? e.message : "error"
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
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setRunning(null);
    }
  };

  const v1 = results.v1?.summary;
  const v2 = results.v2?.summary;

  const chartData = useMemo(
    () => [
      {
        metric: t.eval.metrics.correctness.label,
        v1: v1?.correctness_avg ?? 0,
        v2: v2?.correctness_avg ?? 0,
      },
      {
        metric: t.eval.metrics.coverage.label,
        v1: v1?.coverage_avg ?? 0,
        v2: v2?.coverage_avg ?? 0,
      },
      {
        metric: t.eval.metrics.citation.label,
        v1: v1?.citation_quality_avg ?? 0,
        v2: v2?.citation_quality_avg ?? 0,
      },
      {
        metric: t.eval.metrics.refusal.label,
        v1: v1?.refusal_accuracy ?? 0,
        v2: v2?.refusal_accuracy ?? 0,
      },
      {
        metric: t.eval.metrics.tool.label,
        v1: v1?.tool_call_accuracy ?? 0,
        v2: v2?.tool_call_accuracy ?? 0,
      },
    ],
    [v1, v2, t]
  );

  const difficultyData = useMemo(() => {
    const buckets = Array.from(
      new Set([
        ...Object.keys(v1?.by_difficulty || {}),
        ...Object.keys(v2?.by_difficulty || {}),
      ])
    );
    return buckets.map((b) => ({
      bucket: b,
      v1: v1?.by_difficulty?.[b] ?? 0,
      v2: v2?.by_difficulty?.[b] ?? 0,
    }));
  }, [v1, v2]);

  const headlineDelta = ((v2?.correctness_avg ?? 0) - (v1?.correctness_avg ?? 0)) * 100;

  return (
    <div className="flex flex-col min-h-screen">
      <Header version={version} onVersionChange={setVersion} />
      <main className="flex-1">
        <div className="container max-w-5xl py-12">
          {missingResults && !loading && (
            <div className="mb-12 border border-border-strong bg-bg-panel px-6 py-5">
              <div className="marker mb-2">/00</div>
              <div className="text-ink font-semibold tracking-tight">
                Ainda não existem resultados de avaliação.
              </div>
              <p className="mt-2 text-[13px] text-ink-muted leading-relaxed">
                Clica em <span className="font-mono text-ink">RUN V1</span> ou{" "}
                <span className="font-mono text-ink">RUN V2</span> para correr o harness via API
                e gerar <span className="font-mono">backend/evaluation_results/*.json</span>.
              </p>
            </div>
          )}

          {/* Editorial cover */}
          <header className="mb-16">
            <div className="marker mb-4">{t.eval.coverKicker}</div>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tightest text-ink leading-[1.02]">
              {t.eval.coverTitleA}{" "}
              <span className="text-ink-muted">{t.eval.coverTitleB}</span>
            </h1>
            <p className="mt-6 text-[15px] text-ink-muted max-w-2xl leading-relaxed">
              {t.eval.coverSubtitle(v2?.n ?? 0)}
            </p>

            <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-6 border-t border-border pt-8">
              <Stat
                marker="01"
                label={t.eval.statCorrectnessDelta}
                value={`+${headlineDelta.toFixed(0)}pp`}
              />
              <Stat marker="02" label={t.eval.statTestCases} value={String(v2?.n ?? 0)} />
              <Stat marker="03" label={t.eval.statTools} value="04" />
              <Stat
                marker="04"
                label={t.eval.statRefusal}
                value={`${(((v2?.refusal_accuracy ?? 0) * 100)).toFixed(0)}%`}
              />
            </div>
          </header>

          <section className="mb-12 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
            <div className="marker">{t.eval.runMarker}</div>
            <button
              onClick={() => trigger("v1")}
              disabled={!!running}
              className={cn(
                "font-mono text-[12px] uppercase tracking-marker",
                "text-ink-muted hover:text-ink transition-colors",
                "disabled:opacity-40"
              )}
            >
              {running === "v1" ? t.eval.runV1Loading : t.eval.runV1}
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
              {running === "v2" ? t.eval.runV2Loading : t.eval.runV2}
            </button>
            <span className="text-ink-dim">/</span>
            <button
              onClick={load}
              disabled={loading}
              className="font-mono text-[12px] uppercase tracking-marker text-ink-muted hover:text-ink transition-colors disabled:opacity-40"
            >
              {loading ? t.eval.reloadLoading : t.eval.reload}
            </button>
          </section>

          {(error || missingResults) && (
            <div className="mb-12 border-l-2 border-warning pl-4 py-2 text-[12.5px] text-ink-muted leading-relaxed">
              <span className="marker !text-warning">notice</span>
              <p className="mt-1">
                {error
                  ? error
                  : "Sem resultados persistidos. Corre o harness (botões acima) para gerar métricas reais."}
              </p>
            </div>
          )}

          <section className="mb-16">
            <div className="flex items-baseline gap-3 mb-2">
              <div className="marker">/01</div>
              <h2 className="text-lg font-semibold tracking-tight text-ink">
                {t.eval.metricsTitle}
              </h2>
            </div>

            <div className="grid grid-cols-12 gap-4 mt-4 pb-2 border-b border-border-strong">
              <div className="col-span-12 md:col-span-4 marker">
                {t.eval.colMetric}
              </div>
              <div className="col-span-4 md:col-span-2 marker text-right">
                {t.eval.colV1}
              </div>
              <div className="col-span-4 md:col-span-2 marker text-right">
                {t.eval.colV2}
              </div>
              <div className="col-span-4 md:col-span-4 marker text-right">
                {t.eval.colDelta}
              </div>
            </div>

            {v1 && v2 ? (
              <>
                <MetricCard
                  index={1}
                  label={t.eval.metrics.correctness.label}
                  v1={v1.correctness_avg}
                  v2={v2.correctness_avg}
                  description={t.eval.metrics.correctness.description}
                />
                <MetricCard
                  index={2}
                  label={t.eval.metrics.coverage.label}
                  v1={v1.coverage_avg}
                  v2={v2.coverage_avg}
                  description={t.eval.metrics.coverage.description}
                />
                <MetricCard
                  index={3}
                  label={t.eval.metrics.citation.label}
                  v1={v1.citation_quality_avg}
                  v2={v2.citation_quality_avg}
                  description={t.eval.metrics.citation.description}
                />
                <MetricCard
                  index={4}
                  label={t.eval.metrics.refusal.label}
                  v1={v1.refusal_accuracy}
                  v2={v2.refusal_accuracy}
                  description={t.eval.metrics.refusal.description}
                />
                <MetricCard
                  index={5}
                  label={t.eval.metrics.tool.label}
                  v1={v1.tool_call_accuracy}
                  v2={v2.tool_call_accuracy}
                  description={t.eval.metrics.tool.description}
                />
                <MetricCard
                  index={6}
                  label={t.eval.metrics.latency.label}
                  v1={v1.latency_p95_ms}
                  v2={v2.latency_p95_ms}
                  format="ms"
                  description={t.eval.metrics.latency.description}
                />
              </>
            ) : (
              <div className="py-6 text-[13px] text-ink-muted leading-relaxed">
                Corre o harness para preencher estas métricas (botões acima ou CLI).
              </div>
            )}
          </section>

          {v1 && v2 && (
            <section className="mb-16 grid grid-cols-1 lg:grid-cols-2 gap-x-12 gap-y-12">
              <ComparisonChart data={chartData} />
              <DifficultyChart data={difficultyData} />
            </section>
          )}

          <section className="mb-16">
            <div className="flex items-baseline gap-3 mb-6">
              <div className="marker">/02</div>
              <h2 className="text-lg font-semibold tracking-tight text-ink">
                {t.eval.changesTitle}
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8 border-t border-border pt-8">
              {t.eval.changes.map((c, i) => {
                const id = String(i + 1).padStart(2, "0");
                return (
                  <div key={id} className="grid grid-cols-12 gap-3">
                    <div className="col-span-2 marker tabular pt-1">/{id}</div>
                    <div className="col-span-10">
                      <div className="text-sm font-semibold text-ink tracking-tight mb-1">
                        {c.title}
                      </div>
                      <div className="text-[13px] text-ink-muted leading-relaxed">
                        {c.body}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <footer className="border-t border-border pt-6 flex items-center justify-between text-[11px] font-mono text-ink-dim">
            <span>{t.eval.footerLeft}</span>
            <span>{t.eval.footerRight(v2?.n ?? 0)}</span>
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
