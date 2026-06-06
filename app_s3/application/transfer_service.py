"""Coordinador de transferencias manuales."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from app_s3.domain.models import TransferDirection, TransferStatus, TransferTask
from app_s3.infrastructure.local_fs import LocalFileSystem
from app_s3.infrastructure.s3_repository import S3Repository

logger = logging.getLogger(__name__)

ProgressHandler = Callable[[TransferTask], None]


class TransferService:
    def __init__(self, local_fs: LocalFileSystem | None = None) -> None:
        self._local_fs = local_fs or LocalFileSystem()
        self._tasks: list[TransferTask] = []
        self._cancelled: set[str] = set()

    @property
    def tasks(self) -> list[TransferTask]:
        return list(self._tasks)

    def cancel_task(self, task_id: str) -> None:
        self._cancelled.add(task_id)

    def enqueue_upload(
        self,
        local_path: str,
        bucket: str,
        s3_prefix: str,
    ) -> TransferTask:
        path = Path(local_path)
        key = s3_prefix.rstrip("/") + "/" + path.name if s3_prefix else path.name
        task = TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=str(path),
            bucket=bucket,
            s3_key=key,
            total_bytes=path.stat().st_size if path.is_file() else 0,
        )
        self._tasks.append(task)
        return task

    def enqueue_download(
        self,
        bucket: str,
        s3_key: str,
        local_dir: str,
        local_path: str | None = None,
    ) -> TransferTask:
        if local_path is None:
            filename = s3_key.rstrip("/").split("/")[-1]
            local_path = str(Path(local_dir) / filename)
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            bucket=bucket,
            s3_key=s3_key,
        )
        self._tasks.append(task)
        return task

    def run_task(
        self,
        task: TransferTask,
        repo: S3Repository,
        on_progress: ProgressHandler | None = None,
    ) -> TransferTask:
        if task.id in self._cancelled:
            task.status = TransferStatus.CANCELLED
            return task

        task.status = TransferStatus.RUNNING

        def progress(bytes_amount: int) -> None:
            task.bytes_transferred += bytes_amount
            if on_progress:
                on_progress(task)

        try:
            if task.direction == TransferDirection.UPLOAD:
                repo.upload_file(
                    task.local_path,
                    task.bucket,
                    task.s3_key,
                    progress=progress,
                )
            else:
                self._local_fs.ensure_parent(task.local_path)
                repo.download_file(
                    task.bucket,
                    task.s3_key,
                    task.local_path,
                    progress=progress,
                )
            task.status = TransferStatus.COMPLETED
        except Exception as exc:
            logger.exception("Transfer failed: %s", task.id)
            task.status = TransferStatus.FAILED
            task.error_message = str(exc)

        if on_progress:
            on_progress(task)
        return task
