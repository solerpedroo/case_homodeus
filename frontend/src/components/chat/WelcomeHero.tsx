"use client";

import { useT } from "@/lib/i18n";

interface Props {
  onPickExample?: (q: string) => void;
}

export function WelcomeHero({ onPickExample }: Props) {
  const t = useT();
  return (
    <div className="py-12 animate-fade-in">
      <div className="marker mb-6">{t.hero.kicker}</div>

      <h1 className="text-3xl md:text-5xl font-semibold tracking-tightest text-ink leading-[1.05] max-w-3xl">
        {t.hero.titleLine1}
        <br />
        <span className="text-ink-muted">{t.hero.titleLine2}</span>
      </h1>

      <p className="mt-6 text-[15px] text-ink-muted max-w-2xl leading-relaxed">
        {t.hero.subtitle}
      </p>

      <section className="mt-14">
        <div className="marker mb-5">{t.hero.howKicker}</div>
        <ol className="grid grid-cols-1 md:grid-cols-3 gap-x-12 gap-y-6 border-t border-border pt-6">
          {t.hero.how.map((step) => (
            <li key={step.id} className="grid grid-cols-12 gap-3">
              <div className="col-span-2 marker tabular pt-1">/{step.id}</div>
              <div className="col-span-10 text-[14px] text-ink leading-relaxed">
                {step.body}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-14">
        <div className="marker mb-3">{t.hero.examplesKicker}</div>
        <ul className="border-t border-border divide-y divide-border">
          {t.hero.examples.map((q) => (
            <li key={q}>
              <button
                type="button"
                onClick={() => onPickExample?.(q)}
                className="w-full text-left flex items-baseline gap-3 py-3 group"
              >
                <span className="font-mono text-ink-dim shrink-0">·</span>
                <span className="text-[14.5px] text-ink-muted group-hover:text-ink transition-colors flex-1 min-w-0">
                  {q}
                </span>
                <span className="font-mono text-ink-dim opacity-0 group-hover:opacity-100 transition-opacity">
                  →
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
