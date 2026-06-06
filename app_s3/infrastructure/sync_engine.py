"""Motor de sincronización bidireccional local ↔ S3."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

from app_s3.domain.models import (
    ConflictPolicy,
    S3ListingEntry,
    SyncAction,
    SyncDirection,
    SyncJob,
    SyncResult,
)
from app_s3.infrastructure.local_fs import LocalFileSystem
from app_s3.infrastructure.s3_repository import S3Repository


class SyncEngine:
    """Calcula diff y ejecuta transferencias según políticas del job."""

    def __init__(self, local_fs: LocalFileSystem | None = None) -> None:
        self._local_fs = local_fs or LocalFileSystem()

    def compute_diff(
        self, job: SyncJob, repo: S3Repository
    ) -> list[SyncAction]:
        local_root = Path(job.local_path)
        local_files = {
            e.relative_path: e
            for e in self._local_fs.scan_directory(local_root)
            if not e.is_dir
        }

        s3_objects = repo.list_all_objects(job.bucket, job.s3_prefix)
        prefix = job.s3_prefix
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"

        s3_files: dict[str, S3ListingEntry] = {}
        for obj in s3_objects:
            rel = obj.key
            if prefix and rel.startswith(prefix):
                rel = rel[len(prefix) :]
            s3_files[rel] = obj

        actions: list[SyncAction] = []
        all_keys = set(local_files.keys()) | set(s3_files.keys())

        for rel in sorted(all_keys):
            local = local_files.get(rel)
            s3_obj = s3_files.get(rel)
            s3_key = (prefix + rel) if prefix else rel

            if local and not s3_obj:
                if job.direction in (
                    SyncDirection.BIDIRECTIONAL,
                    SyncDirection.UPLOAD_ONLY,
                ):
                    actions.append(
                        SyncAction(
                            action="upload",
                            local_path=local.absolute_path,
                            s3_key=s3_key,
                            reason="Solo en local",
                        )
                    )
                continue

            if s3_obj and not local:
                if job.direction in (
                    SyncDirection.BIDIRECTIONAL,
                    SyncDirection.DOWNLOAD_ONLY,
                ):
                    dest = str(local_root / rel)
                    actions.append(
                        SyncAction(
                            action="download",
                            local_path=dest,
                            s3_key=s3_obj.key,
                            reason="Solo en S3",
                        )
                    )
                continue

            if local and s3_obj:
                action = self._resolve_conflict(job, local, s3_obj, s3_key)
                if action:
                    actions.append(action)

        return actions

    def run_sync(self, job: SyncJob, repo: S3Repository) -> SyncResult:
        actions = self.compute_diff(job, repo)
        errors: list[str] = []
        executed: list[SyncAction] = []

        for action in actions:
            if action.action == "skip":
                executed.append(action)
                continue
            try:
                if action.action == "upload":
                    repo.upload_file(
                        action.local_path,
                        job.bucket,
                        action.s3_key,
                    )
                elif action.action == "download":
                    self._local_fs.ensure_parent(action.local_path)
                    repo.download_file(
                        job.bucket,
                        action.s3_key,
                        action.local_path,
                    )
                executed.append(action)
            except Exception as exc:
                errors.append(f"{action.s3_key}: {exc}")

        return SyncResult(
            job_id=job.id,
            actions=executed,
            errors=errors,
            success=len(errors) == 0,
        )

    def _resolve_conflict(
        self,
        job: SyncJob,
        local,
        s3_obj: S3ListingEntry,
        s3_key: str,
    ) -> SyncAction | None:
        policy = job.conflict_policy
        s3_mtime = s3_obj.last_modified
        if s3_mtime and s3_mtime.tzinfo is None:
            s3_mtime = s3_mtime.replace(tzinfo=timezone.utc)

        if policy == ConflictPolicy.MANUAL:
            return SyncAction(
                action="skip",
                local_path=local.absolute_path,
                s3_key=s3_key,
                reason="Conflicto manual",
            )

        if policy == ConflictPolicy.S3_WINS:
            if job.direction in (
                SyncDirection.BIDIRECTIONAL,
                SyncDirection.DOWNLOAD_ONLY,
            ):
                return SyncAction(
                    action="download",
                    local_path=local.absolute_path,
                    s3_key=s3_key,
                    reason="S3 gana",
                )
            return None

        if policy == ConflictPolicy.LOCAL_WINS:
            if job.direction in (
                SyncDirection.BIDIRECTIONAL,
                SyncDirection.UPLOAD_ONLY,
            ):
                return SyncAction(
                    action="upload",
                    local_path=local.absolute_path,
                    s3_key=s3_key,
                    reason="Local gana",
                )
            return None

        local_mtime = local.mtime
        if s3_mtime and local_mtime >= s3_mtime:
            if job.direction in (
                SyncDirection.BIDIRECTIONAL,
                SyncDirection.UPLOAD_ONLY,
            ):
                return SyncAction(
                    action="upload",
                    local_path=local.absolute_path,
                    s3_key=s3_key,
                    reason="Local más reciente",
                )
        elif job.direction in (
            SyncDirection.BIDIRECTIONAL,
            SyncDirection.DOWNLOAD_ONLY,
        ):
            return SyncAction(
                action="download",
                local_path=local.absolute_path,
                s3_key=s3_key,
                reason="S3 más reciente",
            )
        return None
