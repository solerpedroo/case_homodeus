"use client";

/**
 * EN: PT/EN toggle — writes preference to localStorage via `useLocale`.
 * PT: Alternador PT/EN — grava preferência em localStorage via `useLocale`.
 */

import { useLocale, type Locale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function LangSwitcher() {
  const { locale, setLocale } = useLocale();
  return (
    <div
      className="inline-flex items-center gap-2 font-mono text-xs"
      role="group"
      aria-label="Language"
    >
      <Option
        code="pt"
        active={locale === "pt"}
        onSelect={setLocale}
        flag={<PortugueseFlag />}
        title="Português"
      />
      <span className="text-ink-dim">/</span>
      <Option
        code="en"
        active={locale === "en"}
        onSelect={setLocale}
        flag={<BritishFlag />}
        title="English"
      />
    </div>
  );
}

function Option({
  code,
  active,
  onSelect,
  flag,
  title,
}: {
  code: Locale;
  active: boolean;
  onSelect: (l: Locale) => void;
  flag: React.ReactNode;
  title: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(code)}
      title={title}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 pb-0.5 border-b transition-colors",
        active
          ? "text-ink border-ink"
          : "text-ink-dim border-transparent hover:text-ink"
      )}
    >
      <span
        className={cn(
          "inline-block h-[10px] w-[14px] border transition-colors",
          active ? "border-border-strong" : "border-border"
        )}
      >
        {flag}
      </span>
      <span className="uppercase tracking-marker">{code}</span>
    </button>
  );
}

function PortugueseFlag() {
  return (
    <svg
      viewBox="0 0 14 10"
      width="14"
      height="10"
      preserveAspectRatio="none"
      aria-hidden
      className="block"
    >
      <rect x="0" y="0" width="5.5" height="10" fill="#006600" />
      <rect x="5.5" y="0" width="8.5" height="10" fill="#cc0000" />
      <circle cx="5.5" cy="5" r="1.5" fill="#ffe600" stroke="#000" strokeWidth="0.3" />
    </svg>
  );
}

function BritishFlag() {
  return (
    <svg
      viewBox="0 0 14 10"
      width="14"
      height="10"
      preserveAspectRatio="none"
      aria-hidden
      className="block"
    >
      <rect width="14" height="10" fill="#012169" />
      <path d="M0,0 L14,10 M14,0 L0,10" stroke="#ffffff" strokeWidth="1.6" />
      <path d="M0,0 L14,10 M14,0 L0,10" stroke="#c8102e" strokeWidth="0.9" />
      <path d="M7,0 V10 M0,5 H14" stroke="#ffffff" strokeWidth="2" />
      <path d="M7,0 V10 M0,5 H14" stroke="#c8102e" strokeWidth="1.1" />
    </svg>
  );
}
