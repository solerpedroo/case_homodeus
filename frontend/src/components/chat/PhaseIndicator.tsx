import { cn } from "@/lib/utils";

const PHASE_LABELS: Record<string, string> = {
  classify: "a classificar a pergunta",
  plan: "a planear ferramentas",
  generate: "a redigir a resposta",
  score: "a avaliar confiança",
  refuse: "a preparar recusa graciosa",
};

interface Props {
  phase: string;
  className?: string;
}

export function PhaseIndicator({ phase, className }: Props) {
  const label = PHASE_LABELS[phase] || phase;
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1 font-mono text-[12.5px] text-ink-muted",
        className
      )}
    >
      <span>{label}</span>
      <span className="text-ink animate-blink select-none">_</span>
    </span>
  );
}
