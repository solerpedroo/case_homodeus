"""Loguru-based structured logging.

EN:
    Removes Loguru's default handler and adds one stdout sink with a fixed
    format (timestamp, level, location, message). Every module does
    `from app.logging_config import logger` — no `basicConfig` boilerplate.
    `diagnose=False` avoids leaking local variables in logs in production.

PT:
    Remove o handler por defeito do Loguru e adiciona um sink stdout com
    formato fixo (hora, nível, localização, mensagem). Cada módulo faz
    `from app.logging_config import logger` — sem `basicConfig`.
    `diagnose=False` evita vazar variáveis locais nos logs em produção.
"""
from __future__ import annotations

import sys

from loguru import logger as _logger

# EN: Replace default stderr handler with our single stdout configuration.
# PT: Substitui o handler por defeito no stderr pela nossa configuração stdout.
_logger.remove()
_logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "| <level>{level: <8}</level> "
        "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
        "- <level>{message}</level>"
    ),
    backtrace=True,
    diagnose=False,
)

logger = _logger
