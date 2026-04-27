"""Evaluation harness, metrics and LLM-as-judge.

EN:
    - `test_cases`: curated questions with expected domains and ground-truth
      bullets for automated grading.
    - `harness`: runs the agent concurrently, persists JSON results.
    - `judge`: optional second LLM pass that scores correctness / citations.
    - `metrics`: aggregates per-case scores into dashboard-friendly summaries.

PT:
    - `test_cases`: perguntas curadas com domínios esperados e factos para
      avaliação automática.
    - `harness`: executa o agente em concorrência e grava resultados JSON.
    - `judge`: passagem opcional de segundo LLM que pontua correção / citações.
    - `metrics`: agrega scores por caso em resumos para o dashboard.
"""
