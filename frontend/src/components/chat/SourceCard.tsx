import type { Source } from "@/lib/types";
import { domainFromUrl } from "@/lib/utils";

interface Props {
  sources: Source[];
}

export function SourceList({ sources }: Props) {
  if (!sources?.length) return null;

  const seen = new Set<string>();
  const unique = sources.filter((s) => {
    const k = s.url || s.title;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  return (
    <div className="mt-6 pt-4 border-t border-border">
      <div className="marker mb-3">/sources · {unique.length}</div>
      <ol className="space-y-1.5 text-[12.5px] leading-snug">
        {unique.map((s, idx) => (
          <SourceRow key={`${s.url}-${idx}`} source={s} index={idx + 1} />
        ))}
      </ol>
    </div>
  );
}

function SourceRow({ source, index }: { source: Source; index: number }) {
  const domain = source.domain || domainFromUrl(source.url) || "";
  const label =
    source.source_type === "labor_code_index"
      ? "código do trabalho"
      : source.source_type === "calculator"
      ? "cálculo determinístico"
      : domain;

  const title = source.title || source.url || "(sem título)";

  const Tag = source.url ? "a" : "div";
  const tagProps = source.url
    ? { href: source.url, target: "_blank", rel: "noreferrer" }
    : {};

  return (
    <li className="flex items-baseline gap-2">
      <span className="font-mono text-ink-dim tabular shrink-0 text-[11px] pt-0.5">
        [{String(index).padStart(2, "0")}]
      </span>
      <Tag
        {...tagProps}
        className="group min-w-0 flex-1 block"
      >
        <span className="font-mono text-[11px] text-ink-dim mr-2">
          {label}
        </span>
        <span className="text-ink group-hover:underline underline-offset-4 decoration-ink-dim">
          {title}
        </span>
        {source.url && (
          <span className="ml-1 text-ink-dim opacity-0 group-hover:opacity-100 transition-opacity">
            →
          </span>
        )}
        {source.snippet && (
          <span className="block mt-0.5 text-[11.5px] text-ink-muted line-clamp-2">
            {source.snippet}
          </span>
        )}
      </Tag>
    </li>
  );
}
