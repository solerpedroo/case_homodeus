import Link from "next/link";

export function Brand() {
  return (
    <Link
      href="/chat"
      className="group flex items-center gap-3"
      aria-label="HomoDeus Labor Agent"
    >
      <span
        className="grid place-items-center w-7 h-7 border border-border-strong text-[11px] font-mono font-semibold tracking-[0.05em] text-ink group-hover:border-ink transition-colors"
        aria-hidden
      >
        HD
      </span>
      <span className="flex items-baseline gap-2 leading-none">
        <span className="text-sm font-semibold tracking-tightest text-ink">
          HomoDeus
        </span>
        <span className="hidden sm:inline text-[11px] font-mono text-ink-dim">
          /labor
        </span>
      </span>
    </Link>
  );
}
