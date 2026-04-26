import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn, fmtPct } from "@/lib/utils";

interface Props {
  label: string;
  v1: number;
  v2: number;
  format?: "pct" | "ms" | "raw";
  description?: string;
}

export function MetricCard({ label, v1, v2, format = "pct", description }: Props) {
  const fmt = (n: number) =>
    format === "pct"
      ? fmtPct(n)
      : format === "ms"
      ? `${Math.round(n).toLocaleString()} ms`
      : n.toFixed(2);

  const delta = v2 - v1;
  const deltaPct = format === "pct" ? delta * 100 : delta;
  const positive = delta > 0;
  const neutral = Math.abs(delta) < 0.005;

  return (
    <div className="rounded-xl border border-border bg-bg-panel/60 p-4 hover:border-accent/40 transition">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] uppercase tracking-[0.18em] text-ink-dim">
          {label}
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-1 text-[11px] font-mono px-1.5 py-0.5 rounded",
            neutral
              ? "text-ink-dim bg-bg-elevated"
              : positive
              ? "text-success bg-success-soft"
              : "text-danger bg-danger-soft"
          )}
        >
          {neutral ? (
            <Minus className="w-3 h-3" />
          ) : positive ? (
            <TrendingUp className="w-3 h-3" />
          ) : (
            <TrendingDown className="w-3 h-3" />
          )}
          {format === "pct"
            ? `${positive ? "+" : ""}${deltaPct.toFixed(1)} pp`
            : `${positive ? "+" : ""}${deltaPct.toFixed(0)}`}
        </span>
      </div>
      <div className="flex items-baseline gap-3">
        <div>
          <div className="text-[10px] text-ink-dim font-mono uppercase">v1</div>
          <div className="text-base text-ink-muted font-mono">{fmt(v1)}</div>
        </div>
        <div className="text-ink-dim text-xs">→</div>
        <div>
          <div className="text-[10px] text-accent font-mono uppercase">v2</div>
          <div className="text-2xl font-semibold text-ink font-mono">{fmt(v2)}</div>
        </div>
      </div>
      {description && (
        <div className="mt-2 text-[11px] text-ink-dim leading-relaxed">
          {description}
        </div>
      )}
    </div>
  );
}
