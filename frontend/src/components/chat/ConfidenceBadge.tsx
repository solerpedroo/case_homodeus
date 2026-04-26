import { cn } from "@/lib/utils";
import { ShieldCheck, ShieldAlert, Shield } from "lucide-react";

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
          "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium",
          "bg-warning-soft text-warning border border-warning/30",
          className
        )}
      >
        <ShieldAlert className="w-3 h-3" />
        Recusa graciosa
      </span>
    );
  }

  const tier =
    score >= 0.75 ? "high" : score >= 0.55 ? "medium" : "low";
  const styles = {
    high: {
      cls: "bg-success-soft text-success border-success/30",
      icon: <ShieldCheck className="w-3 h-3" />,
      label: "Alta confiança",
    },
    medium: {
      cls: "bg-warning-soft text-warning border-warning/30",
      icon: <Shield className="w-3 h-3" />,
      label: "Confiança média",
    },
    low: {
      cls: "bg-danger-soft text-danger border-danger/30",
      icon: <ShieldAlert className="w-3 h-3" />,
      label: "Confiança baixa",
    },
  }[tier];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border",
        styles.cls,
        className
      )}
      title={`Confidence: ${score.toFixed(2)}`}
    >
      {styles.icon}
      {styles.label} · {(score * 100).toFixed(0)}%
    </span>
  );
}
