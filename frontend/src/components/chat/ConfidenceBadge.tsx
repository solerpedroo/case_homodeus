"use client";

/**
 * EN: Numeric confidence + refused state styling from agent v2 scoring.
 * PT: Confiança numérica + estado de recusa após scoring v2.
 */

import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

interface Props {
  score: number;
  refused?: boolean;
  className?: string;
}

export function ConfidenceBadge({ score, refused, className }: Props) {
  const t = useT();
  if (refused) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-2 font-mono text-[11px] tracking-marker uppercase",
          "text-warning",
          className
        )}
      >
        <span className="marker !text-warning">{t.confidence.refused}</span>
        <span className="text-ink-dim normal-case tracking-normal">
          {t.confidence.refusedNote}
        </span>
      </span>
    );
  }

  const tier = score >= 0.75 ? "high" : score >= 0.55 ? "medium" : "low";
  const arrow = tier === "high" ? "↑" : tier === "medium" ? "→" : "↓";
  const tierColor = {
    high: "text-success",
    medium: "text-ink-muted",
    low: "text-danger",
  }[tier];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-mono text-[11px]",
        className
      )}
      title={`Confidence: ${score.toFixed(2)}`}
    >
      <span className="marker">{t.confidence.label}</span>
      <span className={cn("tabular", tierColor)}>
        {arrow} {(score * 100).toFixed(0)}%
      </span>
    </span>
  );
}
