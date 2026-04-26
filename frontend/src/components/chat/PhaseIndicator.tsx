import { cn } from "@/lib/utils";

const PHASE_LABELS: Record<string, string> = {
  classify: "A classificar a pergunta",
  plan: "A planear ferramentas",
  generate: "A redigir a resposta",
  score: "A avaliar confiança",
  refuse: "A preparar recusa graciosa",
};

interface Props {
  phase: string;
  className?: string;
}

export function PhaseIndicator({ phase, className }: Props) {
  const label = PHASE_LABELS[phase] || phase;
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 text-xs text-ink-muted",
        className
      )}
    >
      <span className="shimmer-text">{label}</span>
      <span className="inline-flex">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
    </div>
  );
}
