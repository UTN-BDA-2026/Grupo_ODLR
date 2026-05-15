"""Centralized logging module.

Single entry point for logging configuration and logger creation.
"""

import logging

from app.core.logging.factory import LoggerFactory
from app.core.logging.formatters import JsonFormatter, TextFormatter
from app.core.logging.interfaces import LoggerInterface

__all__ = [
    "get_logger",
    "LoggerInterface",
    "JsonFormatter",
    "TextFormatter",
    "LoggerFactory",
    "configure_logging",
]

_factory: LoggerFactory | None = None
_managed_logger_names: set[str] = set()


def configure_logging(
    level: str = "INFO",
    format_type: str = "text",
    propagate: bool = False,
) -> None:
    """Configure centralized logging for the whole application.

    If loggers were already created, this re-applies the new configuration
    so startup settings affect every managed logger consistently.
    """
    global _factory
    _factory = LoggerFactory(
        level=getattr(logging, level.upper(), logging.INFO),
        format_type=format_type,
        propagate=propagate,
    )

    for logger_name in list(_managed_logger_names):
        _factory.create_logger(logger_name)


def get_logger(name: str) -> logging.Logger:
    """Return a centrally configured logger."""
    global _factory

    if _factory is None:
        configure_logging()

    _managed_logger_names.add(name)
    return _factory.create_logger(name)
