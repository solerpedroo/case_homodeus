import { cn } from "@/lib/utils";

interface Props {
  score: number;
  refused?: boolean;
  className?: string;
}

export function ConfidenceBadge({ score, refused, className }: Props) {
  if (refused) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-2 font-mono text-[11px] tracking-marker uppercase",
          "text-warning",
          className
        )}
      >
        <span className="marker !text-warning">refused</span>
        <span className="text-ink-dim normal-case tracking-normal">
          recusa graciosa · low confidence
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
      <span className="marker">conf</span>
      <span className={cn("tabular", tierColor)}>
        {arrow} {(score * 100).toFixed(0)}%
      </span>
    </span>
  );
}
