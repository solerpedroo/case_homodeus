"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brand } from "./Brand";
import { LangSwitcher } from "./LangSwitcher";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import type { AgentVersion } from "@/lib/types";

interface HeaderProps {
  version: AgentVersion;
  onVersionChange: (v: AgentVersion) => void;
}

export function Header({ version, onVersionChange }: HeaderProps) {
  const pathname = usePathname();
  const t = useT();
  return (
    <header className="border-b border-border bg-bg sticky top-0 z-30">
      <div className="container max-w-6xl flex items-center justify-between gap-6 py-4">
        <Brand />
        <nav className="hidden sm:flex items-center gap-6 text-sm">
          <NavLink href="/chat" active={pathname === "/chat"}>
            {t.nav.chat}
          </NavLink>
          <NavLink href="/eval" active={pathname === "/eval"}>
            {t.nav.eval}
          </NavLink>
        </nav>
        <div className="flex items-center gap-5">
          <LangSwitcher />
          <span className="text-ink-dim hidden sm:inline">·</span>
          <VersionToggle value={version} onChange={onVersionChange} />
        </div>
      </div>
      <nav className="sm:hidden border-t border-border bg-bg">
        <div className="container max-w-6xl flex items-center gap-6 py-2 text-sm">
          <NavLink href="/chat" active={pathname === "/chat"}>
            {t.nav.chat}
          </NavLink>
          <NavLink href="/eval" active={pathname === "/eval"}>
            {t.nav.eval}
          </NavLink>
        </div>
      </nav>
    </header>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "transition-colors",
        active ? "text-ink" : "text-ink-dim hover:text-ink"
      )}
    >
      {children}
    </Link>
  );
}

function VersionToggle({
  value,
  onChange,
}: {
  value: AgentVersion;
  onChange: (v: AgentVersion) => void;
}) {
  return (
    <div className="inline-flex items-center gap-2 font-mono text-xs">
      {(["v1", "v2"] as const).map((v, i) => {
        const active = value === v;
        return (
          <span key={v} className="flex items-center">
            <button
              onClick={() => onChange(v)}
              className={cn(
                "uppercase tracking-marker transition-colors pb-0.5 border-b",
                active
                  ? "text-ink border-ink"
                  : "text-ink-dim border-transparent hover:text-ink"
              )}
              title={v === "v2" ? "v2 — full architecture" : "v1 — baseline"}
            >
              {v}
            </button>
            {i === 0 && <span className="mx-2 text-ink-dim">/</span>}
          </span>
        );
      })}
    </div>
  );
}
