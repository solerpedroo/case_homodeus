"""Labor law Q&A agent (async tool-calling orchestrator).

EN:
    The public surface is `LaborAgent` in `app.agent.graph`. It classifies
    questions, plans tool calls (web search, PDF index, URL fetch, calculator),
    streams tokens to the client, and scores confidence for v2.

PT:
    A superfície pública é `LaborAgent` em `app.agent.graph`. Classifica
    perguntas, planifica chamadas a ferramentas (pesquisa web, índice do CT,
    fetch de URL, calculadora), envia tokens em stream ao cliente e avalia
    confiança na v2.
"""
