"""Workers Qt para transferencias en background."""

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from app_s3.application.transfer_service import TransferService
from app_s3.domain.models import TransferTask
from app_s3.infrastructure.s3_repository import S3Repository


class TransferSignals(QObject):
    progress = Signal(object)
    finished = Signal(object)


class TransferWorker(QRunnable):
    def __init__(
        self,
        task: TransferTask,
        repo: S3Repository,
        transfer_service: TransferService,
    ) -> None:
        super().__init__()
        self._task = task
        self._repo = repo
        self._transfer_service = transfer_service
        self.signals = TransferSignals()

    @Slot()
    def run(self) -> None:
        def on_progress(t: TransferTask) -> None:
            self.signals.progress.emit(t)

        result = self._transfer_service.run_task(
            self._task, self._repo, on_progress=on_progress
        )
        self.signals.finished.emit(result)


class TransferWorkerPool:
    def __init__(self, max_threads: int = 3) -> None:
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(max_threads)

    def submit(
        self,
        task: TransferTask,
        repo: S3Repository,
        transfer_service: TransferService,
        on_progress,
        on_finished,
    ) -> None:
        worker = TransferWorker(task, repo, transfer_service)
        worker.signals.progress.connect(on_progress)
        worker.signals.finished.connect(on_finished)
        self._pool.start(worker)
