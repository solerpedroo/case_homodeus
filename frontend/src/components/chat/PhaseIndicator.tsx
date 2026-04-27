"use client";

/**
 * EN: Shows current pipeline phase label (classify, plan, generate, …).
 * PT: Mostra a fase atual do pipeline (classificar, planear, gerar, …).
 */

import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

interface Props {
  phase: string;
  className?: string;
}

export function PhaseIndicator({ phase, className }: Props) {
  const t = useT();
  const map: Record<string, string> = {
    classify: t.phases.classify,
    plan: t.phases.plan,
    generate: t.phases.generate,
    score: t.phases.score,
    refuse: t.phases.refuse,
  };
  const label = map[phase] || phase;
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
