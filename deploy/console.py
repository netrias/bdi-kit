"""Colored console logging for deploy output. Changes when log styling or format changes."""

from __future__ import annotations

import logging
from typing import Final

_GREEN: Final[str] = "\033[0;32m"
_RED: Final[str] = "\033[0;31m"
_YELLOW: Final[str] = "\033[1;33m"
_RESET: Final[str] = "\033[0m"


class _ColorFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="[%(asctime)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        color = {
            logging.INFO: _GREEN,
            logging.ERROR: _RED,
            logging.WARNING: _YELLOW,
        }.get(record.levelno, _RESET)
        record.msg = f"{color}{record.msg}{_RESET}"
        return super().format(record)


def _logger() -> logging.Logger:
    logger = logging.getLogger("deploy")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_ColorFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_info(message: str) -> None:
    _logger().info(f"INFO {message}")


def log_error(message: str) -> None:
    _logger().error(f"ERROR {message}")


def log_warning(message: str) -> None:
    _logger().warning(f"WARN {message}")
