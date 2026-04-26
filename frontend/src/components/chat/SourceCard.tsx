import type { Source } from "@/lib/types";
import { domainFromUrl, faviconFor, cn } from "@/lib/utils";
import { ExternalLink, Database, Calculator, Globe } from "lucide-react";

interface Props {
  sources: Source[];
}

export function SourceList({ sources }: Props) {
  if (!sources?.length) return null;

  // Deduplicate by URL
  const seen = new Set<string>();
  const unique = sources.filter((s) => {
    const k = s.url || s.title;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  return (
    <div className="mt-4 pt-3 border-t border-border">
      <div className="text-[11px] uppercase tracking-[0.18em] text-ink-dim mb-2">
        Fontes ({unique.length})
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {unique.map((s, idx) => (
          <SourceChip key={`${s.url}-${idx}`} source={s} />
        ))}
      </div>
    </div>
  );
}

function SourceChip({ source }: { source: Source }) {
  const domain = source.domain || domainFromUrl(source.url);
  const Icon =
    source.source_type === "labor_code_index"
      ? Database
      : source.source_type === "calculator"
      ? Calculator
      : Globe;

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noreferrer"
      className={cn(
        "group flex items-start gap-2 p-2.5 rounded-lg",
        "bg-bg-elevated/60 border border-border hover:border-accent/50",
        "hover:bg-bg-elevated transition"
      )}
    >
      <div className="shrink-0 mt-0.5">
        {source.source_type === "web" && domain ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={faviconFor(domain)}
            alt=""
            className="w-4 h-4 rounded"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <Icon className="w-4 h-4 text-accent" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 text-[11px] text-ink-dim mb-0.5">
          <span className="font-mono truncate">{domain}</span>
          <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
        </div>
        <div className="text-xs font-medium text-ink line-clamp-2 leading-snug">
          {source.title || source.url}
        </div>
        {source.snippet && (
          <div className="mt-1 text-[11px] text-ink-muted line-clamp-2 leading-relaxed">
            {source.snippet}
          </div>
        )}
      </div>
    </a>
  );
}
