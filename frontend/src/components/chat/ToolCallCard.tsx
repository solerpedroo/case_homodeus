"use client";

import * as Collapsible from "@radix-ui/react-collapsible";
import { useState } from "react";
import type { ToolCallTrace } from "@/lib/types";
import { cn, fmtMs } from "@/lib/utils";

const TOOL_LABELS: Record<string, string> = {
  search_web: "search_web",
  fetch_url: "fetch_url",
  search_labor_code: "search_labor_code",
  calculate: "calculate",
};

interface Props {
  trace: ToolCallTrace;
  defaultOpen?: boolean;
}

export function ToolCallCard({ trace, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const label = TOOL_LABELS[trace.tool_name] ?? trace.tool_name;

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <Collapsible.Trigger asChild>
        <button
          className={cn(
            "w-full text-left flex items-baseline gap-2 py-1.5",
            "font-mono text-[12px] leading-snug",
            "text-ink-muted hover:text-ink transition-colors",
            "border-l-2 border-transparent hover:border-ink-dim pl-3 -ml-px",
            open && "border-accent text-ink"
          )}
        >
          <span className="text-ink-dim shrink-0">↳</span>
          <span className="text-ink shrink-0">{label}</span>
          <span className="text-ink-muted truncate flex-1 min-w-0">
            {summarizeArgs(trace.args)}
          </span>
          <span
            className={cn(
              "shrink-0 text-[11px]",
              trace.success ? "text-ink-dim" : "text-warning"
            )}
          >
            {trace.success ? "ok" : "warn"}
          </span>
          <span className="shrink-0 text-ink-dim text-[11px] tabular">
            {fmtMs(trace.duration_ms)}
          </span>
        </button>
      </Collapsible.Trigger>
      <Collapsible.Content className="overflow-hidden data-[state=open]:animate-fade-in">
        <div className="ml-3 pl-3 border-l border-accent py-2 my-1 text-[11px] font-mono">
          <div className="marker mb-1">args</div>
          <pre className="text-ink-muted whitespace-pre-wrap break-words mb-3">
            {JSON.stringify(trace.args, null, 2)}
          </pre>
          <div className="marker mb-1">output</div>
          <pre className="text-ink whitespace-pre-wrap break-words">
            {trace.output_summary || trace.error || "(sem saída)"}
          </pre>
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}

function summarizeArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args);
  if (!entries.length) return "()";
  const parts = entries.map(([k, v]) => {
    const s =
      typeof v === "string"
        ? `"${v.length > 50 ? v.slice(0, 47) + "…" : v}"`
        : JSON.stringify(v);
    return `${k}=${s}`;
  });
  return parts.join(" ");
}
