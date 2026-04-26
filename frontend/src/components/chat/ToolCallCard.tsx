"use client";

import * as Collapsible from "@radix-ui/react-collapsible";
import { useState } from "react";
import {
  ChevronDown,
  Search,
  Globe,
  Database,
  Calculator,
  AlertTriangle,
  Check,
} from "lucide-react";
import type { ToolCallTrace } from "@/lib/types";
import { cn, fmtMs } from "@/lib/utils";

const TOOL_META: Record<
  string,
  { label: string; icon: React.ComponentType<{ className?: string }> }
> = {
  search_web: { label: "Pesquisa web", icon: Search },
  fetch_url: { label: "Fetch URL", icon: Globe },
  search_labor_code: { label: "Índice — Código do Trabalho", icon: Database },
  calculate: { label: "Calculadora salarial", icon: Calculator },
};

interface Props {
  trace: ToolCallTrace;
  defaultOpen?: boolean;
}

export function ToolCallCard({ trace, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const meta = TOOL_META[trace.tool_name] ?? {
    label: trace.tool_name,
    icon: Search,
  };
  const Icon = meta.icon;

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <Collapsible.Trigger asChild>
        <button
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left",
            "bg-bg-elevated/40 border border-border hover:border-accent/40",
            "transition group"
          )}
        >
          <span className="grid place-items-center w-7 h-7 rounded-md bg-accent-soft text-accent shrink-0">
            <Icon className="w-3.5 h-3.5" />
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium">{meta.label}</span>
              {trace.success ? (
                <Check className="w-3.5 h-3.5 text-success" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-warning" />
              )}
            </div>
            <div className="text-[11px] text-ink-dim font-mono truncate">
              {summarizeArgs(trace.args)}
            </div>
          </div>
          <span className="text-[11px] text-ink-dim font-mono shrink-0">
            {fmtMs(trace.duration_ms)}
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-ink-dim transition-transform shrink-0",
              open && "rotate-180"
            )}
          />
        </button>
      </Collapsible.Trigger>
      <Collapsible.Content className="overflow-hidden data-[state=open]:animate-fade-in">
        <div className="mt-1 mx-2 px-3 py-2.5 rounded-lg bg-bg-subtle border border-border text-xs">
          <div className="text-[10px] uppercase tracking-wider text-ink-dim mb-1">
            Argumentos
          </div>
          <pre className="font-mono text-[11px] text-ink-muted whitespace-pre-wrap break-words mb-2">
            {JSON.stringify(trace.args, null, 2)}
          </pre>
          <div className="text-[10px] uppercase tracking-wider text-ink-dim mb-1 mt-2">
            Saída
          </div>
          <pre className="font-mono text-[11px] text-ink whitespace-pre-wrap break-words">
            {trace.output_summary || trace.error || "(sem saída)"}
          </pre>
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}

function summarizeArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args);
  if (!entries.length) return "(sem argumentos)";
  return entries
    .map(([k, v]) => {
      const s =
        typeof v === "string"
          ? `"${v.length > 60 ? v.slice(0, 57) + "…" : v}"`
          : JSON.stringify(v);
      return `${k}=${s}`;
    })
    .join(", ");
}
