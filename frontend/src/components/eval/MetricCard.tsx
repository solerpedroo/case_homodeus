/**
 * EN: Single stat tile — compares v1 vs v2 with delta coloring.
 * PT: Cartão de métrica — compara v1 e v2 com cor na variação.
 */
import { cn, fmtPct } from "@/lib/utils";

interface Props {
  label: string;
  v1: number;
  v2: number;
  format?: "pct" | "ms" | "raw";
  description?: string;
  index?: number;
}

export function MetricCard({
  label,
  v1,
  v2,
  format = "pct",
  description,
  index,
}: Props) {
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

  const deltaText = neutral
    ? "—"
    : format === "pct"
    ? `${positive ? "+" : ""}${deltaPct.toFixed(1)}pp`
    : `${positive ? "+" : ""}${deltaPct.toFixed(0)}`;

  // For ms metric, lower is better; invert the success/danger color logic
  const isInverted = format === "ms";
  const goodDelta = isInverted ? !positive : positive;

  return (
    <div className="grid grid-cols-12 gap-4 items-baseline py-4 border-t border-border">
      <div className="col-span-12 md:col-span-4 flex items-baseline gap-3">
        {typeof index === "number" && (
          <span className="marker tabular shrink-0 w-6">
            /{String(index).padStart(2, "0")}
          </span>
        )}
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink tracking-tight">
            {label}
          </div>
          {description && (
            <div className="mt-0.5 text-[12px] text-ink-dim leading-snug">
              {description}
            </div>
          )}
        </div>
      </div>

      <div className="col-span-4 md:col-span-2 text-right">
        <div className="marker mb-1">v1</div>
        <div className="font-mono text-sm text-ink-muted tabular">
          {fmt(v1)}
        </div>
      </div>

      <div className="col-span-4 md:col-span-2 text-right">
        <div className="marker mb-1">v2</div>
        <div className="font-mono text-base text-ink tabular font-semibold">
          {fmt(v2)}
        </div>
      </div>

      <div className="col-span-4 md:col-span-4 text-right">
        <div className="marker mb-1">delta</div>
        <div
          className={cn(
            "font-mono text-sm tabular",
            neutral
              ? "text-ink-dim"
              : goodDelta
              ? "text-success"
              : "text-danger"
          )}
        >
          {deltaText}
        </div>
      </div>
    </div>
  );
}
