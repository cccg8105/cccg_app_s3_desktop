"""Utilidades de logging con medición de tiempo."""

from __future__ import annotations

import logging
import threading
import time


def elapsed_ms(start: float) -> float:
    """Duración en milisegundos desde ``start`` (``time.perf_counter()``)."""
    return (time.perf_counter() - start) * 1000


def format_extras(**extra: object) -> str:
    """Formatea kwargs como fragmento ``key=value`` para mensajes de log."""
    if not extra:
        return ""
    parts = [f"{key}={value}" for key, value in extra.items()]
    return " " + " ".join(parts)


def log_elapsed(
    logger: logging.Logger,
    label: str,
    start: float,
    **extra: object,
) -> None:
    """Registra duración en ms con metadatos opcionales."""
    logger.info(
        "%s%s elapsed_ms=%.1f",
        label,
        format_extras(**extra),
        elapsed_ms(start),
    )


def log_thread_context(logger: logging.Logger, label: str) -> None:
    """Registra el hilo actual (útil para confirmar ejecución en UI thread)."""
    thread = threading.current_thread()
    logger.info("%s thread=%s", label, thread.name)
