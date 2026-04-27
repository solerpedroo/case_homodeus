"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Locale = "pt" | "en";

interface ChangeItem {
  title: string;
  body: string;
}

interface MetricCopy {
  label: string;
  description: string;
}

interface Dict {
  nav: { chat: string; eval: string };
  brand: { suffix: string; aria: string };
  hero: {
    kicker: string;
    titleLine1: string;
    titleLine2: string;
    subtitle: string;
    howKicker: string;
    how: { id: string; body: string }[];
    examplesKicker: string;
    examples: string[];
  };
  chat: {
    placeholder: string;
    shiftHint: string;
    newChat: string;
    youMarker: string;
    responseMarker: string;
    convPrefix: string;
    stop: string;
    errorBackend: (host: string, msg: string) => string;
  };
  phases: {
    classify: string;
    plan: string;
    generate: string;
    score: string;
    refuse: string;
  };
  confidence: {
    label: string;
    refused: string;
    refusedNote: string;
  };
  sources: { marker: string };
  eval: {
    coverKicker: string;
    coverTitleA: string;
    coverTitleB: string;
    coverSubtitle: (n: number) => string;
    statCorrectnessDelta: string;
    statTestCases: string;
    statTools: string;
    statRefusal: string;
    runMarker: string;
    runV1: string;
    runV1Loading: string;
    runV2: string;
    runV2Loading: string;
    reload: string;
    reloadLoading: string;
    notice: string;
    metricsTitle: string;
    colMetric: string;
    colV1: string;
    colV2: string;
    colDelta: string;
    metrics: {
      correctness: MetricCopy;
      coverage: MetricCopy;
      citation: MetricCopy;
      refusal: MetricCopy;
      tool: MetricCopy;
      latency: MetricCopy;
    };
    chartsGlobal: string;
    chartsGlobalKicker: string;
    chartsDifficulty: string;
    chartsDifficultyKicker: string;
    changesTitle: string;
    changes: ChangeItem[];
    footerLeft: string;
    footerRight: (n: number) => string;
  };
}

const PT: Dict = {
  nav: { chat: "Chat", eval: "Avaliação" },
  brand: { suffix: "/labor", aria: "HomoDeus Challenge - Pedro Soler" },
  hero: {
    kicker: "/00 — Labor Agent",
    titleLine1: "Direito laboral português,",
    titleLine2: "respondido com a lei na mão.",
    subtitle:
      "Pergunte sobre férias, salário, IRS, TSU ou cessação de contrato. Cada resposta cita o artigo da lei. Os cálculos são feitos em Python — não inventados pelo modelo.",
    howKicker: "/como funciona",
    how: [
      {
        id: "01",
        body: "Você pergunta em linguagem natural — em português ou inglês.",
      },
      {
        id: "02",
        body:
          "O agente consulta fontes oficiais (ACT, DRE, Portal das Finanças, CITE) e o Código do Trabalho indexado por artigo.",
      },
      {
        id: "03",
        body:
          "Devolve uma resposta com citações + score de confiança. Se faltar fonte, recusa em vez de inventar.",
      },
    ],
    examplesKicker: "/exemplos",
    examples: [
      "Qual é o salário mínimo nacional atual em Portugal?",
      "Como se calcula o subsídio de férias para 1.500 EUR/mês?",
      "Que prazo de aviso prévio é necessário para 3 anos de antiguidade?",
      "É legal uma cláusula de não concorrência de 3 anos?",
    ],
  },
  chat: {
    placeholder:
      "Pergunte sobre direito laboral português ou processamento salarial.",
    shiftHint: "shift+enter — nova linha",
    newChat: "+ Nova conversa",
    youMarker: "/pergunta",
    responseMarker: "/resposta",
    convPrefix: "conv:",
    stop: "esc ⨯",
    errorBackend: (host, msg) =>
      `**Erro de comunicação com o backend.**\n\n\`${msg}\`\n\nVerifique se o servidor está em execução em \`${host}\`.`,
  },
  phases: {
    classify: "a classificar a pergunta",
    plan: "a planear ferramentas",
    generate: "a redigir a resposta",
    score: "a avaliar confiança",
    refuse: "a preparar recusa graciosa",
  },
  confidence: {
    label: "conf",
    refused: "refused",
    refusedNote: "recusa graciosa · low confidence",
  },
  sources: { marker: "/fontes" },
  eval: {
    coverKicker: "/00 — relatório de avaliação",
    coverTitleA: "Avaliação",
    coverTitleB: "v1 vs v2",
    coverSubtitle: (n) =>
      `Harness LLM-as-judge sobre ${n} casos de teste anotados. Métricas pontuadas contra factos esperados e fontes oficiais.`,
    statCorrectnessDelta: "Δ Correctness",
    statTestCases: "Casos de teste",
    statTools: "Ferramentas",
    statRefusal: "Refusal accuracy",
    runMarker: "/run",
    runV1: "▷ run v1",
    runV1Loading: "executando…",
    runV2: "▷ run v2",
    runV2Loading: "executando…",
    reload: "↻ recarregar",
    reloadLoading: "carregando…",
    notice:
      "A mostrar resultados de referência. Execute Run v1/v2 ou `python -m app.evaluation.harness --version both` para gerar métricas reais.",
    metricsTitle: "Métricas globais",
    colMetric: "métrica",
    colV1: "v1",
    colV2: "v2",
    colDelta: "delta",
    metrics: {
      correctness: {
        label: "Correctness",
        description:
          "LLM-as-judge: factualidade ponderada contra ground-truth annotated.",
      },
      coverage: {
        label: "Coverage",
        description: "Cobertura dos factos esperados na resposta.",
      },
      citation: {
        label: "Citation Quality",
        description:
          "Fontes oficiais (ACT, DRE, Finanças, CITE) citadas com URL válido.",
      },
      refusal: {
        label: "Refusal Accuracy",
        description:
          "Recusa correta em perguntas fora de âmbito ou sem fontes.",
      },
      tool: {
        label: "Tool Call Accuracy",
        description:
          "Foi chamada a ferramenta certa para o domínio da pergunta?",
      },
      latency: {
        label: "Latency p95",
        description:
          "v2 é mais lento devido a múltiplos tools — trade-off aceitável pela qualidade.",
      },
    },
    chartsGlobal: "v1 vs v2 — métricas globais",
    chartsGlobalKicker: "/chart · global metrics",
    chartsDifficulty: "Correctness por dificuldade",
    chartsDifficultyKicker: "/chart · by difficulty",
    changesTitle: "O que mudou entre v1 e v2",
    changes: [
      {
        title: "Tool calling",
        body:
          "v2 expõe 4 ferramentas (web, fetch, vector, calculator) vs 1 em v1. Cada ferramenta com domínio escopado.",
      },
      {
        title: "Routing determinístico",
        body:
          "Classifier antes do plan. Pesquisa web restrita aos domínios oficiais por categoria.",
      },
      {
        title: "Vector index",
        body:
          "Código do Trabalho indexado por artigo. Citações com referência exata ao Art.º.",
      },
      {
        title: "Calculadoras determinísticas",
        body:
          "TSU, IRS e subsídios em Python. Zero aritmética via LLM, zero alucinação numérica.",
      },
      {
        title: "Confidence scoring + recusa",
        body:
          "Threshold de 0.55 dispara recusa graciosa. Refusal accuracy +53pp em v2.",
      },
      {
        title: "Prompt v2",
        body:
          "Regras não-negociáveis de grounding e citação. Sem fonte, sem afirmação.",
      },
    ],
    footerLeft: "HomoDeus Challenge - Pedro Soler · Evaluation Harness",
    footerRight: (n) => `v1 vs v2 · ${n} casos`,
  },
};

const EN: Dict = {
  nav: { chat: "Chat", eval: "Evaluation" },
  brand: { suffix: "/labor", aria: "HomoDeus Challenge - Pedro Soler" },
  hero: {
    kicker: "/00 — Labor Agent",
    titleLine1: "Portuguese labor law,",
    titleLine2: "answered with the statute in hand.",
    subtitle:
      "Ask about vacation, payroll, IRS, social security, or contract termination. Every claim is cited to the article of law. Calculations run in Python — never invented by the model.",
    howKicker: "/how it works",
    how: [
      {
        id: "01",
        body: "You ask in plain language — in Portuguese or English.",
      },
      {
        id: "02",
        body:
          "The agent queries official sources (ACT, DRE, Tax Authority, CITE) and the Labor Code, indexed article by article.",
      },
      {
        id: "03",
        body:
          "It returns a cited answer + a confidence score. If a source is missing, it refuses instead of making things up.",
      },
    ],
    examplesKicker: "/examples",
    examples: [
      "What is Portugal's current national minimum wage?",
      "How is the holiday subsidy computed for a 1,500 EUR/month salary?",
      "What notice period applies after 3 years of tenure?",
      "Is a 3-year non-compete clause legal under Portuguese law?",
    ],
  },
  chat: {
    placeholder:
      "Ask about Portuguese labor law or payroll calculations.",
    shiftHint: "shift+enter — new line",
    newChat: "+ New chat",
    youMarker: "/question",
    responseMarker: "/response",
    convPrefix: "conv:",
    stop: "esc ⨯",
    errorBackend: (host, msg) =>
      `**Backend communication error.**\n\n\`${msg}\`\n\nMake sure the server is running at \`${host}\`.`,
  },
  phases: {
    classify: "classifying the question",
    plan: "planning tools",
    generate: "drafting the answer",
    score: "scoring confidence",
    refuse: "preparing graceful refusal",
  },
  confidence: {
    label: "conf",
    refused: "refused",
    refusedNote: "graceful refusal · low confidence",
  },
  sources: { marker: "/sources" },
  eval: {
    coverKicker: "/00 — evaluation report",
    coverTitleA: "Evaluation",
    coverTitleB: "v1 vs v2",
    coverSubtitle: (n) =>
      `LLM-as-judge harness over ${n} annotated test cases. Metrics scored against expected facts and official sources.`,
    statCorrectnessDelta: "Correctness Δ",
    statTestCases: "Test cases",
    statTools: "Tools",
    statRefusal: "Refusal accuracy",
    runMarker: "/run",
    runV1: "▷ run v1",
    runV1Loading: "executing…",
    runV2: "▷ run v2",
    runV2Loading: "executing…",
    reload: "↻ reload",
    reloadLoading: "loading…",
    notice:
      "Showing reference results. Run v1/v2 or `python -m app.evaluation.harness --version both` to generate live metrics.",
    metricsTitle: "Global metrics",
    colMetric: "metric",
    colV1: "v1",
    colV2: "v2",
    colDelta: "delta",
    metrics: {
      correctness: {
        label: "Correctness",
        description:
          "LLM-as-judge: weighted factuality against annotated ground truth.",
      },
      coverage: {
        label: "Coverage",
        description: "Coverage of expected facts in the answer.",
      },
      citation: {
        label: "Citation Quality",
        description:
          "Official sources (ACT, DRE, Tax Authority, CITE) cited with valid URLs.",
      },
      refusal: {
        label: "Refusal Accuracy",
        description:
          "Correct refusal on out-of-scope questions or when sources are missing.",
      },
      tool: {
        label: "Tool Call Accuracy",
        description:
          "Was the right tool called for the question's domain?",
      },
      latency: {
        label: "Latency p95",
        description:
          "v2 is slower due to multiple tools — an acceptable trade-off for quality.",
      },
    },
    chartsGlobal: "v1 vs v2 — global metrics",
    chartsGlobalKicker: "/chart · global metrics",
    chartsDifficulty: "Correctness by difficulty",
    chartsDifficultyKicker: "/chart · by difficulty",
    changesTitle: "What changed between v1 and v2",
    changes: [
      {
        title: "Tool calling",
        body:
          "v2 exposes 4 tools (web, fetch, vector, calculator) vs 1 in v1. Each tool scoped to its domain.",
      },
      {
        title: "Deterministic routing",
        body:
          "Classifier runs before the planner. Web search is restricted to official domains per category.",
      },
      {
        title: "Vector index",
        body:
          "Labor Code indexed article by article. Citations with the exact article reference.",
      },
      {
        title: "Deterministic calculators",
        body:
          "Social security, IRS, and subsidies in Python. Zero LLM arithmetic, zero numeric hallucination.",
      },
      {
        title: "Confidence scoring + refusal",
        body:
          "A 0.55 threshold triggers graceful refusal. Refusal accuracy +53pp in v2.",
      },
      {
        title: "Prompt v2",
        body:
          "Non-negotiable grounding and citation rules. No source, no claim.",
      },
    ],
    footerLeft: "HomoDeus Challenge - Pedro Soler · Evaluation Harness",
    footerRight: (n) => `v1 vs v2 · ${n} cases`,
  },
};

export const STRINGS: Record<Locale, Dict> = { pt: PT, en: EN };

interface LocaleCtx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: Dict;
}

const LocaleContext = createContext<LocaleCtx | null>(null);

const STORAGE_KEY = "locale";

function detectInitial(): Locale {
  if (typeof window === "undefined") return "pt";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved === "pt" || saved === "en") return saved;
  const nav = window.navigator?.language?.toLowerCase() || "pt";
  return nav.startsWith("pt") ? "pt" : "en";
}

export function useLocaleProvider() {
  const [locale, setLocaleState] = useState<Locale>("pt");

  useEffect(() => {
    const initial = detectInitial();
    setLocaleState(initial);
    document.documentElement.setAttribute("lang", initial);
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
    } catch {}
    document.documentElement.setAttribute("lang", l);
  }, []);

  const value = useMemo<LocaleCtx>(
    () => ({ locale, setLocale, t: STRINGS[locale] }),
    [locale, setLocale]
  );

  return value;
}

export { LocaleContext };

export function useLocale(): LocaleCtx {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    return {
      locale: "pt",
      setLocale: () => {},
      t: STRINGS.pt,
    };
  }
  return ctx;
}

export function useT(): Dict {
  return useLocale().t;
}
