import Link from "next/link";
import { Sparkles } from "lucide-react";

export function Brand() {
  return (
    <Link
      href="/chat"
      className="flex items-center gap-2 group"
    >
      <span className="grid place-items-center w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-glow shadow-[0_0_18px_rgba(124,92,255,0.45)] group-hover:shadow-[0_0_24px_rgba(124,92,255,0.7)] transition">
        <Sparkles className="w-4 h-4 text-white" strokeWidth={2.4} />
      </span>
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-tight text-ink">
          HomoDeus
        </div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-ink-dim">
          Labor Agent
        </div>
      </div>
    </Link>
  );
}
