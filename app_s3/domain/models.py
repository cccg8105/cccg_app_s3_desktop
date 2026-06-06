"""Modelos de dominio."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SyncDirection(str, Enum):
    BIDIRECTIONAL = "bidirectional"
    UPLOAD_ONLY = "upload_only"
    DOWNLOAD_ONLY = "download_only"


class ConflictPolicy(str, Enum):
    NEWER_WINS = "newer_wins"
    S3_WINS = "s3_wins"
    LOCAL_WINS = "local_wins"
    MANUAL = "manual"


class DeletePolicy(str, Enum):
    SAFE = "safe"
    MIRROR = "mirror"


class TransferDirection(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TransferStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CredentialProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    alias: str
    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    session_token: str | None = None
    endpoint_url: str | None = None


class BucketBookmark(BaseModel):
    credential_id: str
    bucket_name: str


class BookmarksStore(BaseModel):
    bookmarks: list[BucketBookmark] = Field(default_factory=list)


class AppSettings(BaseModel):
    default_credential_id: str | None = None


class S3ListingEntry(BaseModel):
    name: str
    key: str
    is_prefix: bool
    size: int = 0
    last_modified: datetime | None = None


class TransferTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    direction: TransferDirection
    local_path: str
    bucket: str
    s3_key: str
    status: TransferStatus = TransferStatus.PENDING
    bytes_transferred: int = 0
    total_bytes: int = 0
    error_message: str | None = None


class SyncJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    credential_id: str
    bucket: str
    s3_prefix: str = ""
    local_path: str
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    schedule_cron: str | None = None
    schedule_interval_minutes: int | None = None
    conflict_policy: ConflictPolicy = ConflictPolicy.NEWER_WINS
    delete_policy: DeletePolicy = DeletePolicy.SAFE
    enabled: bool = True
    last_run: datetime | None = None
    last_status: str | None = None


class SyncJobsStore(BaseModel):
    jobs: list[SyncJob] = Field(default_factory=list)


class SyncAction(BaseModel):
    action: Literal["upload", "download", "skip"]
    local_path: str
    s3_key: str
    reason: str = ""


class SyncResult(BaseModel):
    job_id: str
    actions: list[SyncAction] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    success: bool = True
