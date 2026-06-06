"""Tests del motor de sincronización."""

from datetime import datetime, timezone

from app_s3.domain.models import (
    S3ListingEntry,
    SyncDirection,
    SyncJob,
)
from app_s3.infrastructure.sync_engine import SyncEngine


class FakeS3Repo:
    def __init__(self, objects: list[S3ListingEntry]):
        self._objects = objects

    def list_all_objects(self, bucket: str, prefix: str = ""):
        return self._objects


def test_compute_diff_upload_only_local(tmp_path):
    local_file = tmp_path / "doc.txt"
    local_file.write_text("hello")

    job = SyncJob(
        name="test",
        credential_id="c1",
        bucket="my-bucket",
        s3_prefix="",
        local_path=str(tmp_path),
        direction=SyncDirection.BIDIRECTIONAL,
    )

    engine = SyncEngine()
    repo = FakeS3Repo([])
    actions = engine.compute_diff(job, repo)

    assert len(actions) == 1
    assert actions[0].action == "upload"
    assert actions[0].s3_key == "doc.txt"


def test_compute_diff_download_only_s3(tmp_path):
    job = SyncJob(
        name="test",
        credential_id="c1",
        bucket="my-bucket",
        s3_prefix="",
        local_path=str(tmp_path),
        direction=SyncDirection.BIDIRECTIONAL,
    )

    s3_obj = S3ListingEntry(
        name="remote.txt",
        key="remote.txt",
        is_prefix=False,
        size=100,
        last_modified=datetime.now(timezone.utc),
    )
    engine = SyncEngine()
    repo = FakeS3Repo([s3_obj])
    actions = engine.compute_diff(job, repo)

    assert len(actions) == 1
    assert actions[0].action == "download"
