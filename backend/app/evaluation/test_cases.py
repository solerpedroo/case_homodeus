"""Annotated test cases for the labor-law agent.

EN:
    This module is the **ground truth specification** for offline evaluation.
    Each `TestCase` records:
    - `difficulty`: basic / intermediate / advanced / edge / refusal — used
      only for reporting buckets in `metrics.aggregate`.
    - `expected_category`: what the classifier *should* output (sanity check).
    - `expected_domains`: substrings that should appear in cited URLs or
      `Source.domain` for citation-quality scoring.
    - `ground_truth_facts`: short strings the judge checks for coverage.
    - `expects_refusal`: if True, `refusal_correct` expects the agent to
      decline rather than hallucinate.

    The harness iterates `TEST_CASES` in order; use `limit` to shorten runs.

PT:
    Este módulo é a **especificação de verdade** para avaliação offline.
    Cada `TestCase` contém:
    - `difficulty`: basic / intermediate / advanced / edge / refusal — só para
      agregações no `metrics.aggregate`.
    - `expected_category`: o que o classificador *deveria* produzir.
    - `expected_domains`: substrings que devem aparecer em URLs citadas ou em
      `Source.domain` para pontuar qualidade de citação.
    - `ground_truth_facts`: frases curtas que o juiz verifica quanto à cobertura.
    - `expects_refusal`: se True, espera-se que o agente recuse em vez de
      inventar.

    O harness percorre `TEST_CASES` em ordem; use `limit` para corridas curtas.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


Difficulty = Literal["basic", "intermediate", "advanced", "edge", "refusal"]


class TestCase(BaseModel):
    id: str
    difficulty: Difficulty
    question: str
    expected_category: str
    expected_domains: list[str]
    ground_truth_facts: list[str]
    expects_refusal: bool = False
    notes: str = ""


TEST_CASES: list[TestCase] = [
    # --- BASIC --- #
    TestCase(
        id="basic-01",
        difficulty="basic",
        question="Qual é o salário mínimo nacional atual em Portugal?",
        expected_category="salary_calc",
        expected_domains=["dre.pt", "diariodarepublica.pt", "act.gov.pt"],
        ground_truth_facts=[
            "Salário mínimo nacional (continente) em vigor: 920 EUR/mês (efeitos 1/1/2026, Decreto-Lei n.º 139/2025)",
            "Atualizado por Decreto-Lei publicado no DRE",
        ],
    ),
    TestCase(
        id="basic-02",
        difficulty="basic",
        question="A quantos dias de férias tem direito um trabalhador a tempo inteiro?",
        expected_category="labor_code",
        expected_domains=["act.gov.pt", "portal.act.gov.pt"],
        ground_truth_facts=[
            "22 dias úteis de férias por ano (Art. 238.º CT)",
            "Aplica-se após o ano de admissão",
        ],
    ),
    TestCase(
        id="basic-03",
        difficulty="basic",
        question="Existe um período experimental num contrato sem termo em Portugal?",
        expected_category="labor_code",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Período experimental em contrato sem termo: 90 dias regra geral, 180 dias para cargos de complexidade técnica, 240 dias para cargos de direção (Art. 112.º CT)",
        ],
    ),
    # --- INTERMEDIATE --- #
    TestCase(
        id="inter-01",
        difficulty="intermediate",
        question="Como se calcula o subsídio de férias para um trabalhador que ganha 1.500 EUR/mês?",
        expected_category="salary_calc",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Subsídio de férias = retribuição base + prestações regulares (Art. 264.º CT)",
            "Para 1.500 EUR/mês em ano completo, valor = 1.500 EUR",
        ],
    ),
    TestCase(
        id="inter-02",
        difficulty="intermediate",
        question="Quais são as taxas de contribuição TSU do empregador e do trabalhador num contrato sem termo?",
        expected_category="social_security",
        expected_domains=["diariodarepublica.pt", "seg-social.pt"],
        ground_truth_facts=[
            "Empregador: 23,75%",
            "Trabalhador: 11%",
            "Lei 110/2009 (Código dos Regimes Contributivos)",
        ],
    ),
    TestCase(
        id="inter-03",
        difficulty="intermediate",
        question="Que prazo de aviso prévio é necessário para despedir um trabalhador com 3 anos de antiguidade?",
        expected_category="labor_code",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Despedimento por iniciativa do empregador requer aviso prévio que varia com antiguidade (Art. 363.º CT — despedimento coletivo / Art. 371.º — extinção do posto)",
            "Para antiguidade ≥ 2 e < 5 anos: 30 a 60 dias dependendo da modalidade",
        ],
    ),
    TestCase(
        id="inter-04",
        difficulty="intermediate",
        question="Qual é a retenção na fonte de IRS para um trabalhador solteiro sem dependentes que ganha 2.000 EUR brutos/mês em 2025?",
        expected_category="tax",
        expected_domains=["info.portaldasfinancas.gov.pt", "portaldasfinancas.gov.pt"],
        ground_truth_facts=[
            "Tabela I 2025 (não casado, sem dependentes, continente)",
            "Despacho 236-A/2025",
            "Resultado entre 280 e 360 EUR consoante escalão exato",
        ],
    ),
    # --- ADVANCED --- #
    TestCase(
        id="adv-01",
        difficulty="advanced",
        question="Como difere o cálculo do subsídio de Natal para um trabalhador contratado a meio do ano?",
        expected_category="salary_calc",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Pago proporcionalmente aos meses trabalhados no ano (Art. 263.º CT)",
            "Fórmula: retribuição mensal × meses_trabalhados / 12",
            "Pago até 15 de Dezembro",
        ],
    ),
    TestCase(
        id="adv-02",
        difficulty="advanced",
        question="Quais são as taxas de retenção na fonte de IRS para um contribuinte solteiro com 2.200 EUR brutos/mês em 2024?",
        expected_category="tax",
        expected_domains=["info.portaldasfinancas.gov.pt", "portaldasfinancas.gov.pt"],
        ground_truth_facts=[
            "Tabela I (não casado, sem dependentes) 2024",
            "Despacho 4/2024 (versão de Janeiro) ou versão posterior",
            "Cita o link oficial das tabelas",
        ],
    ),
    TestCase(
        id="adv-03",
        difficulty="advanced",
        question="Em que condições pode um empregador implementar lay-off ao abrigo da lei portuguesa?",
        expected_category="labor_code",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Crise empresarial (motivos económicos, mercado, técnicos ou catástrofe)",
            "Art. 298.º a 308.º do Código do Trabalho",
            "Comunicação prévia aos trabalhadores e à ACT/Segurança Social",
            "Limite temporal e proteção do emprego",
        ],
    ),
    # --- EDGE --- #
    TestCase(
        id="edge-01",
        difficulty="edge",
        question="A minha empresa está em Portugal mas o trabalhador trabalha remotamente a partir de Espanha. Qual a lei laboral aplicável?",
        expected_category="edge_case",
        expected_domains=["act.gov.pt", "diariodarepublica.pt", "cite.gov.pt"],
        ground_truth_facts=[
            "Roma I (Regulamento UE 593/2008) — lei do local habitual de execução do trabalho",
            "Espanha como local habitual = lei espanhola pode aplicar-se",
            "Possível escolha de lei portuguesa contratualmente, mas não pode privar o trabalhador de proteção mínima espanhola",
            "Recomenda análise jurídica especializada",
        ],
    ),
    TestCase(
        id="edge-02",
        difficulty="edge",
        question="É legal incluir uma cláusula de não concorrência de 3 anos num contrato de trabalho português?",
        expected_category="labor_code",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Cláusula de não concorrência regulada no Art. 136.º CT",
            "Limite máximo de 2 anos (3 em casos especiais com competência rara)",
            "Tem de ser por escrito e ter compensação",
            "3 anos só é válido para atividades cuja saída cria efetivo prejuízo",
        ],
    ),
    TestCase(
        id="edge-03",
        difficulty="edge",
        question="Pode um trabalhador recusar fazer horas extraordinárias?",
        expected_category="labor_code",
        expected_domains=["act.gov.pt"],
        ground_truth_facts=[
            "Trabalho suplementar: dever de prestação salvo motivo atendível (Art. 227.º a 231.º CT)",
            "Exceções: trabalhador deficiente, grávidas, trabalhadores-estudantes",
            "Limites diários e anuais",
        ],
    ),
    # --- REFUSAL --- #
    TestCase(
        id="refusal-01",
        difficulty="refusal",
        question="Qual é a melhor receita de bacalhau à brás?",
        expected_category="out_of_scope",
        expected_domains=[],
        ground_truth_facts=[],
        expects_refusal=True,
        notes="Out-of-scope: agent should refuse politely.",
    ),
    TestCase(
        id="refusal-02",
        difficulty="refusal",
        question="Qual será o salário mínimo em Portugal em 2030?",
        expected_category="edge_case",
        expected_domains=[],
        ground_truth_facts=[],
        expects_refusal=True,
        notes="Future prediction with no official source — should refuse or hedge clearly.",
    ),
]
