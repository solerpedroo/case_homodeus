import { Sparkles, Scale, Calculator, Globe2 } from "lucide-react";

export function WelcomeHero() {
  return (
    <div className="text-center py-10 animate-fade-in">
      <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-accent to-accent-glow shadow-[0_0_28px_rgba(124,92,255,0.55)] mb-5 animate-pulse-glow">
        <Sparkles className="w-7 h-7 text-white" strokeWidth={2.2} />
      </div>
      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">
        Direito laboral português,
        <br />
        <span className="bg-gradient-to-r from-accent-glow to-success bg-clip-text text-transparent">
          com fontes oficiais.
        </span>
      </h1>
      <p className="mt-3 text-sm text-ink-muted max-w-xl mx-auto leading-relaxed">
        Q&amp;A em tempo real sobre Código do Trabalho, IRS e Segurança Social.
        Cada afirmação suportada por uma fonte oficial; cálculos
        determinísticos; recusa graciosa quando faltam dados.
      </p>
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-2 max-w-2xl mx-auto text-left">
        <Feature
          icon={<Scale className="w-4 h-4" />}
          title="Código do Trabalho"
          subtitle="Indexado por artigo"
        />
        <Feature
          icon={<Calculator className="w-4 h-4" />}
          title="Cálculos exatos"
          subtitle="TSU · IRS · Subsídios"
        />
        <Feature
          icon={<Globe2 className="w-4 h-4" />}
          title="Fontes ao vivo"
          subtitle="ACT · DRE · Finanças"
        />
      </div>
    </div>
  );
}

function Feature({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-bg-panel/60 p-3 hover:border-accent/40 transition">
      <div className="flex items-center gap-2 text-accent">
        {icon}
        <span className="text-sm font-medium text-ink">{title}</span>
      </div>
      <div className="mt-0.5 text-[11px] text-ink-dim">{subtitle}</div>
    </div>
  );
}
