"""Deterministic Portuguese payroll calculators.

EN:
    **Design rule:** the LLM must never do payroll arithmetic. It picks an
    `action` and numeric inputs; this module returns exact values, readable
    formulas, and `Source` rows (DRE, Portal das Finanças, CT PDF).

    Actions (see `CALCULATOR_ACTIONS`): **tsu**, **irs**, **holiday_subsidy**,
    **christmas_subsidy**, **net_salary**. Public entry: `calculate(action, **kwargs)`.

PT:
    **Regra:** o LLM não faz contas salariais. Escolhe `action` e números;
    o módulo devolve valores, fórmulas e `Source` oficiais.

    Ações: **tsu**, **irs**, **holiday_subsidy**, **christmas_subsidy**,
    **net_salary**. Entrada: `calculate(action, **kwargs)`.

CRITICAL / CRÍTICO: the LLM never does arithmetic — eliminates hallucinated numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.agent.state import Source
from app.agent.tools import ToolResult


# ----- TSU rates (Lei n.º 110/2009, Código dos Regimes Contributivos) ----- #

TSU_EMPLOYER_RATE = 0.2375
TSU_WORKER_RATE = 0.11

TSU_SOURCE = Source(
    url="https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2009-34514575",
    title="Código dos Regimes Contributivos — Lei n.º 110/2009",
    snippet="Regime geral: empregador 23,75%, trabalhador 11%.",
    domain="diariodarepublica.pt",
    score=1.0,
    source_type="calculator",
)


# ----- IRS withholding 2025 (continente, não casado, sem dependentes) ----- #
# Approximation derived from Despacho 236-A/2025. Official tables published at
# info.portaldasfinancas.gov.pt — we cite that URL and recommend the user
# verifies before payroll runs. We model the principal brackets used by 99%
# of monthly payrolls.

@dataclass(frozen=True)
class IrsBracket:
    upper_limit: float  # gross monthly EUR
    rate: float
    deductible: float


# Marginal-style monthly brackets for 2025 (continente, "não casado, sem deps").
# Source: Despacho 236-A/2025, tabela I (trabalhadores dependentes não casados).
IRS_BRACKETS_2025_SINGLE = [
    IrsBracket(upper_limit=870.0,    rate=0.000, deductible=0.00),
    IrsBracket(upper_limit=991.0,    rate=0.130, deductible=113.10),
    IrsBracket(upper_limit=1070.0,   rate=0.165, deductible=147.79),
    IrsBracket(upper_limit=1187.0,   rate=0.220, deductible=206.64),
    IrsBracket(upper_limit=1427.0,   rate=0.260, deductible=254.12),
    IrsBracket(upper_limit=1666.0,   rate=0.288, deductible=294.07),
    IrsBracket(upper_limit=1969.0,   rate=0.323, deductible=352.40),
    IrsBracket(upper_limit=2331.0,   rate=0.346, deductible=397.69),
    IrsBracket(upper_limit=2790.0,   rate=0.385, deductible=488.61),
    IrsBracket(upper_limit=3326.0,   rate=0.405, deductible=544.41),
    IrsBracket(upper_limit=4318.0,   rate=0.420, deductible=594.30),
    IrsBracket(upper_limit=5687.0,   rate=0.450, deductible=723.85),
    IrsBracket(upper_limit=11279.0,  rate=0.480, deductible=894.46),
    IrsBracket(upper_limit=20067.0,  rate=0.490, deductible=1007.25),
    IrsBracket(upper_limit=float("inf"), rate=0.530, deductible=1809.93),
]

IRS_SOURCE = Source(
    url="https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/tabela_ret_doclib/",
    title="Tabelas de Retenção na Fonte IRS 2025 — Despacho 236-A/2025",
    snippet="Tabela I — trabalhadores dependentes não casados, continente.",
    domain="info.portaldasfinancas.gov.pt",
    score=1.0,
    source_type="calculator",
)


CT_HOLIDAY_SUBSIDY_SOURCE = Source(
    url="https://www.act.gov.pt/(pt-PT)/Legislacao/Legislacao_n/Documents/C%C3%B3digo%20do%20Trabalho.pdf",
    title="Código do Trabalho — Art. 264.º (Subsídio de Férias)",
    snippet="O trabalhador tem direito a um subsídio de férias compreendendo a retribuição base e demais prestações retributivas.",
    domain="act.gov.pt",
    score=1.0,
    source_type="calculator",
)

CT_CHRISTMAS_SUBSIDY_SOURCE = Source(
    url="https://www.act.gov.pt/(pt-PT)/Legislacao/Legislacao_n/Documents/C%C3%B3digo%20do%20Trabalho.pdf",
    title="Código do Trabalho — Art. 263.º (Subsídio de Natal)",
    snippet="O trabalhador tem direito a subsídio de Natal de valor igual a um mês de retribuição, pago até 15 de Dezembro.",
    domain="act.gov.pt",
    score=1.0,
    source_type="calculator",
)


def _tsu(gross: float) -> dict:
    employer = round(gross * TSU_EMPLOYER_RATE, 2)
    worker = round(gross * TSU_WORKER_RATE, 2)
    return {
        "employer": employer,
        "worker": worker,
        "formula": f"empregador = {gross:.2f} × 0,2375 = {employer:.2f}; "
                   f"trabalhador = {gross:.2f} × 0,11 = {worker:.2f}",
        "sources": [TSU_SOURCE],
    }


def _irs(gross: float, table: list[IrsBracket] = IRS_BRACKETS_2025_SINGLE) -> dict:
    bracket = next(b for b in table if gross <= b.upper_limit)
    irs = max(0.0, round(gross * bracket.rate - bracket.deductible, 2))
    return {
        "value": irs,
        "rate": bracket.rate,
        "deductible": bracket.deductible,
        "formula": f"IRS = max(0, {gross:.2f} × {bracket.rate:.3f} − {bracket.deductible:.2f}) = {irs:.2f}",
        "sources": [IRS_SOURCE],
    }


def calc_tsu(gross_monthly: float) -> ToolResult:
    r = _tsu(gross_monthly)
    return ToolResult(
        ok=True,
        data={"employer_eur": r["employer"], "worker_eur": r["worker"]},
        sources=r["sources"],
        summary=(
            f"TSU para {gross_monthly:.2f} €/mês:\n"
            f"  - Empregador: {r['employer']:.2f} € (23,75%)\n"
            f"  - Trabalhador: {r['worker']:.2f} € (11%)\n"
            f"Fórmula: {r['formula']}"
        ),
        error=None,
    )


def calc_irs_withholding(
    gross_monthly: float,
    marital_status: Literal["single", "married_single_holder", "married_two_holders"] = "single",
    dependents: int = 0,
) -> ToolResult:
    r = _irs(gross_monthly)
    note = (
        "Tabela aplicada: Tabela I (não casado, sem dependentes, continente, 2025). "
        "Para outras situações (casado, dependentes, IRS Jovem) consulte as restantes "
        "tabelas no Portal das Finanças."
    )
    if marital_status != "single" or dependents > 0:
        note = (
            f"AVISO: pediu marital={marital_status}, dependents={dependents}. "
            "Esta calculadora usa apenas a Tabela I. Para outras tabelas, consulte "
            "o Portal das Finanças (link nas fontes)."
        )
    return ToolResult(
        ok=True,
        data={"irs_eur": r["value"], "rate": r["rate"], "deductible": r["deductible"]},
        sources=r["sources"],
        summary=(
            f"Retenção IRS para {gross_monthly:.2f} €/mês:\n"
            f"  - IRS: {r['value']:.2f} €\n"
            f"  - Taxa marginal: {r['rate']*100:.1f}%\n"
            f"  - Parcela a abater: {r['deductible']:.2f} €\n"
            f"Fórmula: {r['formula']}\n{note}"
        ),
        error=None,
    )


def calc_holiday_subsidy(
    monthly_gross: float,
    months_worked_in_year: int = 12,
) -> ToolResult:
    months = max(0, min(12, int(months_worked_in_year)))
    pro_rata = round(monthly_gross * months / 12, 2)
    return ToolResult(
        ok=True,
        data={"value_eur": pro_rata, "pro_rata": months != 12},
        sources=[CT_HOLIDAY_SUBSIDY_SOURCE],
        summary=(
            f"Subsídio de férias (Art. 264.º CT):\n"
            f"  - Base mensal: {monthly_gross:.2f} €\n"
            f"  - Meses trabalhados no ano: {months}\n"
            f"  - Valor: {monthly_gross:.2f} × {months}/12 = {pro_rata:.2f} €\n"
            f"  - Em ano completo: igual a 1 mês de retribuição."
        ),
        error=None,
    )


def calc_christmas_subsidy(
    monthly_gross: float,
    months_worked_in_year: int = 12,
) -> ToolResult:
    months = max(0, min(12, int(months_worked_in_year)))
    pro_rata = round(monthly_gross * months / 12, 2)
    return ToolResult(
        ok=True,
        data={"value_eur": pro_rata, "pro_rata": months != 12},
        sources=[CT_CHRISTMAS_SUBSIDY_SOURCE],
        summary=(
            f"Subsídio de Natal (Art. 263.º CT):\n"
            f"  - Base mensal: {monthly_gross:.2f} €\n"
            f"  - Meses trabalhados no ano: {months}\n"
            f"  - Valor: {monthly_gross:.2f} × {months}/12 = {pro_rata:.2f} €\n"
            f"  - Pago até 15 de Dezembro."
        ),
        error=None,
    )


def calc_net_salary(gross_monthly: float) -> ToolResult:
    tsu = _tsu(gross_monthly)
    irs = _irs(gross_monthly)
    net = round(gross_monthly - tsu["worker"] - irs["value"], 2)
    return ToolResult(
        ok=True,
        data={
            "gross_eur": gross_monthly,
            "irs_eur": irs["value"],
            "ss_worker_eur": tsu["worker"],
            "net_eur": net,
        },
        sources=[TSU_SOURCE, IRS_SOURCE],
        summary=(
            f"Salário líquido estimado para {gross_monthly:.2f} €/mês:\n"
            f"  - Bruto: {gross_monthly:.2f} €\n"
            f"  - SS trabalhador (11%): −{tsu['worker']:.2f} €\n"
            f"  - IRS (taxa {irs['rate']*100:.1f}%): −{irs['value']:.2f} €\n"
            f"  - Líquido: {net:.2f} €\n"
            "Pressupostos: não casado, sem dependentes, continente, 2025."
        ),
        error=None,
    )


# Map a calculator action keyword to its function. The agent picks one when
# routing salary_calc questions.
CALCULATOR_ACTIONS = {
    "tsu": calc_tsu,
    "irs": calc_irs_withholding,
    "holiday_subsidy": calc_holiday_subsidy,
    "christmas_subsidy": calc_christmas_subsidy,
    "net_salary": calc_net_salary,
}


def calculate(action: str, **kwargs) -> ToolResult:
    fn = CALCULATOR_ACTIONS.get(action)
    if fn is None:
        return ToolResult(
            ok=False,
            data=None,
            sources=[],
            summary="",
            error=(
                f"Unknown calculator action '{action}'. Valid: "
                f"{list(CALCULATOR_ACTIONS.keys())}"
            ),
        )
    try:
        return fn(**kwargs)
    except TypeError as exc:
        return ToolResult(ok=False, data=None, sources=[], summary="", error=str(exc))
