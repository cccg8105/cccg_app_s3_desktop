"""Worker Qt para listar prefijos S3 en background."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app_s3.domain.models import S3ListingEntry
from app_s3.infrastructure.log_timing import log_elapsed
from app_s3.infrastructure.s3_repository import S3Repository

logger = logging.getLogger(__name__)


class ListingSignals(QObject):
    progress = Signal(int, int)
    finished = Signal(list)
    failed = Signal(str)


class ListingWorker(QRunnable):
    """Lista un prefijo S3 sin bloquear el hilo de UI."""

    def __init__(
        self,
        repo: S3Repository,
        bucket: str,
        prefix: str,
        cancel_event: threading.Event,
        signals: ListingSignals,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self._repo = repo
        self._bucket = bucket
        self._prefix = prefix
        self._cancel_event = cancel_event
        self.signals = signals

    @Slot()
    def run(self) -> None:
        total_start = time.perf_counter()
        logger.info(
            "listing worker start bucket=%s prefix=%s",
            self._bucket,
            self._prefix or "(root)",
        )
        entries: list[S3ListingEntry] = []
        try:
            should_cancel: Callable[[], bool] = self._cancel_event.is_set
            for page_number, page_entries, accumulated in self._repo.iter_prefix_pages(
                self._bucket,
                self._prefix,
                should_cancel=should_cancel,
            ):
                entries.extend(page_entries)
                self.signals.progress.emit(page_number, accumulated)
                if should_cancel():
                    logger.info(
                        "listing worker cancelled at page=%s accumulated=%s",
                        page_number,
                        accumulated,
                    )
                    return
        except Exception as exc:
            if not self._cancel_event.is_set():
                logger.exception(
                    "listing worker failed bucket=%s prefix=%s",
                    self._bucket,
                    self._prefix or "(root)",
                )
                self.signals.failed.emit(str(exc))
            return

        if self._cancel_event.is_set():
            return

        sort_start = time.perf_counter()
        sorted_entries = S3Repository._sort_entries(entries)
        log_elapsed(
            logger,
            "listing worker sort done",
            sort_start,
            entries=len(sorted_entries),
        )
        log_elapsed(
            logger,
            "listing worker done",
            total_start,
            entries=len(sorted_entries),
        )
        self.signals.finished.emit(sorted_entries)
