"""Persistencia y ejecución de jobs de sincronización."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app_s3.application.credential_service import CredentialService
from app_s3.config.paths import logs_dir, sync_jobs_file
from app_s3.domain.models import SyncJob, SyncJobsStore, SyncResult
from app_s3.infrastructure.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(
        self,
        credential_service: CredentialService,
        sync_engine: SyncEngine | None = None,
    ) -> None:
        self._credential_service = credential_service
        self._sync_engine = sync_engine or SyncEngine()
        self._scheduler = BackgroundScheduler()
        self._on_complete = None

    def set_on_complete(self, callback) -> None:
        self._on_complete = callback

    def load_jobs(self) -> SyncJobsStore:
        path = sync_jobs_file()
        if not path.exists():
            return SyncJobsStore()
        data = json.loads(path.read_text(encoding="utf-8"))
        return SyncJobsStore.model_validate(data)

    def save_jobs(self, store: SyncJobsStore) -> None:
        sync_jobs_file().write_text(
            store.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def add_job(self, job: SyncJob) -> None:
        store = self.load_jobs()
        store.jobs.append(job)
        self.save_jobs(store)
        if job.enabled:
            self._schedule_job(job)

    def update_job(self, job: SyncJob) -> None:
        store = self.load_jobs()
        store.jobs = [job if j.id == job.id else j for j in store.jobs]
        self.save_jobs(store)
        self._unschedule_job(job.id)
        if job.enabled:
            self._schedule_job(job)

    def delete_job(self, job_id: str) -> None:
        store = self.load_jobs()
        store.jobs = [j for j in store.jobs if j.id != job_id]
        self.save_jobs(store)
        self._unschedule_job(job_id)

    def run_job_now(self, job_id: str) -> SyncResult | None:
        store = self.load_jobs()
        job = next((j for j in store.jobs if j.id == job_id), None)
        if job is None:
            return None
        return self._execute_job(job)

    def start_scheduler(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
        for job in self.load_jobs().jobs:
            if job.enabled:
                self._schedule_job(job)

    def stop_scheduler(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def _execute_job(self, job: SyncJob) -> SyncResult:
        repo = self._credential_service.create_repository(job.credential_id)
        if repo is None:
            result = SyncResult(
                job_id=job.id,
                errors=["Perfil de credencial no encontrado"],
                success=False,
            )
            self._log_result(job, result)
            return result

        result = self._sync_engine.run_sync(job, repo)
        job.last_run = datetime.now(timezone.utc)
        job.last_status = "ok" if result.success else "error"
        store = self.load_jobs()
        store.jobs = [job if j.id == job.id else j for j in store.jobs]
        self.save_jobs(store)
        self._log_result(job, result)
        if self._on_complete:
            self._on_complete(job, result)
        return result

    def _log_result(self, job: SyncJob, result: SyncResult) -> None:
        log_path = logs_dir() / f"sync_{job.id}.log"
        lines = [
            f"Job: {job.name} ({job.id})",
            f"Success: {result.success}",
            f"Actions: {len(result.actions)}",
        ]
        for err in result.errors:
            lines.append(f"ERROR: {err}")
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _schedule_job(self, job: SyncJob) -> None:
        def run():
            try:
                self._execute_job(job)
            except Exception:
                logger.exception("Scheduled sync failed: %s", job.id)

        trigger = None
        if job.schedule_cron:
            trigger = CronTrigger.from_crontab(job.schedule_cron)
        elif job.schedule_interval_minutes:
            trigger = IntervalTrigger(minutes=job.schedule_interval_minutes)

        if trigger:
            self._scheduler.add_job(
                run,
                trigger=trigger,
                id=job.id,
                replace_existing=True,
            )

    def _unschedule_job(self, job_id: str) -> None:
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass
