"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brand } from "./Brand";
import { cn } from "@/lib/utils";
import { BarChart3, MessageSquare, Github } from "lucide-react";
import type { AgentVersion } from "@/lib/types";

interface HeaderProps {
  version: AgentVersion;
  onVersionChange: (v: AgentVersion) => void;
}

export function Header({ version, onVersionChange }: HeaderProps) {
  const pathname = usePathname();
  return (
    <header className="border-b border-border bg-bg/70 backdrop-blur-xl sticky top-0 z-30">
      <div className="container max-w-6xl flex items-center justify-between py-3">
        <Brand />
        <nav className="flex items-center gap-1">
          <NavLink href="/chat" active={pathname === "/chat"} icon={<MessageSquare className="w-4 h-4" />}>
            Chat
          </NavLink>
          <NavLink href="/eval" active={pathname === "/eval"} icon={<BarChart3 className="w-4 h-4" />}>
            Avaliação
          </NavLink>
        </nav>
        <div className="flex items-center gap-3">
          <VersionToggle value={version} onChange={onVersionChange} />
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="text-ink-muted hover:text-ink transition p-1.5 rounded-md hover:bg-bg-elevated"
            title="GitHub"
          >
            <Github className="w-4 h-4" />
          </a>
        </div>
      </div>
    </header>
  );
}

function NavLink({
  href,
  active,
  icon,
  children,
}: {
  href: string;
  active: boolean;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition",
        active
          ? "bg-bg-elevated text-ink shadow-inner"
          : "text-ink-muted hover:text-ink hover:bg-bg-elevated/60"
      )}
    >
      {icon}
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
    <div className="inline-flex items-center rounded-lg bg-bg-elevated p-0.5 border border-border">
      {(["v1", "v2"] as const).map((v) => {
        const active = value === v;
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            className={cn(
              "px-2.5 py-1 text-xs font-mono uppercase tracking-wider rounded-md transition",
              active
                ? "bg-accent text-white shadow-[0_0_12px_rgba(124,92,255,0.4)]"
                : "text-ink-muted hover:text-ink"
            )}
            title={v === "v2" ? "v2 — full architecture" : "v1 — baseline"}
          >
            {v}
          </button>
        );
      })}
    </div>
  );
}
