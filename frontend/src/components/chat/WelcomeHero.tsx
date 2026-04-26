export function WelcomeHero() {
  return (
    <div className="py-12 animate-fade-in">
      <div className="marker mb-6">/00 — Labor Agent</div>

      <h1 className="text-3xl md:text-5xl font-semibold tracking-tightest text-ink leading-[1.05] max-w-3xl">
        Direito laboral português
        <br />
        <span className="text-ink-muted">com citações ao artigo.</span>
      </h1>

      <p className="mt-6 text-[15px] text-ink-muted max-w-2xl leading-relaxed">
        Q&amp;A sobre Código do Trabalho, IRS e Segurança Social. Cada
        afirmação suportada por fonte oficial. Cálculos determinísticos. Recusa
        graciosa quando faltam dados.
      </p>

      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-y-8 md:gap-x-12 max-w-3xl">
        <Column
          marker="/01"
          title="Fontes verificadas"
          lines={[
            "portal.act.gov.pt",
            "info.portaldasfinancas.gov.pt",
            "diariodarepublica.pt",
          ]}
        />
        <Column
          marker="/02"
          title="Cálculos determinísticos"
          lines={["TSU 11% · 23,75%", "IRS — Despacho 236-A/2025", "Subsídios — Lei 7/2009"]}
        />
        <Column
          marker="/03"
          title="Recusa graciosa"
          lines={["Sem alucinações", "Confiança medida", "Citação obrigatória"]}
        />
      </div>
    </div>
  );
}

function Column({
  marker,
  title,
  lines,
}: {
  marker: string;
  title: string;
  lines: string[];
}) {
  return (
    <div>
      <div className="marker mb-3">{marker}</div>
      <div className="text-sm font-semibold text-ink tracking-tight mb-2">
        {title}
      </div>
      <ul className="space-y-1 text-[13px] text-ink-muted font-mono">
        {lines.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
    </div>
  );
}
