"""Operaciones S3 vía boto3."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app_s3.domain.exceptions import S3OperationError
from app_s3.domain.models import CredentialProfile, S3ListingEntry
from app_s3.infrastructure.log_timing import log_elapsed

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int], None]


class S3Repository:
    """Wrapper de boto3 para operaciones S3."""

    def __init__(self, profile: CredentialProfile) -> None:
        self._profile = profile
        session_kwargs: dict = {
            "aws_access_key_id": profile.access_key_id,
            "aws_secret_access_key": profile.secret_access_key,
            "region_name": profile.region,
        }
        if profile.session_token:
            session_kwargs["aws_session_token"] = profile.session_token

        self._session = boto3.Session(**session_kwargs)
        client_kwargs: dict = {
            "config": Config(retries={"max_attempts": 5, "mode": "standard"}),
        }
        if profile.endpoint_url:
            client_kwargs["endpoint_url"] = profile.endpoint_url

        self._client = self._session.client("s3", **client_kwargs)

    @property
    def profile(self) -> CredentialProfile:
        return self._profile

    def validate_credentials(self) -> str:
        """Verifica credenciales vía STS GetCallerIdentity."""
        sts_kwargs: dict = {
            "aws_access_key_id": self._profile.access_key_id,
            "aws_secret_access_key": self._profile.secret_access_key,
            "region_name": self._profile.region,
        }
        if self._profile.session_token:
            sts_kwargs["aws_session_token"] = self._profile.session_token
        if self._profile.endpoint_url:
            sts_kwargs["endpoint_url"] = self._profile.endpoint_url

        sts = self._session.client("sts", **sts_kwargs)
        identity = sts.get_caller_identity()
        return identity.get("Arn", "unknown")

    def list_buckets(self) -> list[str]:
        try:
            response = self._client.list_buckets()
            return sorted(b["Name"] for b in response.get("Buckets", []))
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc

    def list_prefix(
        self, bucket: str, prefix: str = ""
    ) -> list[S3ListingEntry]:
        prefix = self._normalize_prefix(prefix)
        total_start = time.perf_counter()
        logger.info(
            "list_prefix start bucket=%s prefix=%s",
            bucket,
            prefix or "(root)",
        )

        entries: list[S3ListingEntry] = []
        fetch_start = time.perf_counter()
        page_number = 0
        try:
            for page_number, page_entries, _accumulated in self.iter_prefix_pages(
                bucket, prefix
            ):
                page_start = time.perf_counter()
                entries.extend(page_entries)
                log_elapsed(
                    logger,
                    f"list_prefix page={page_number}",
                    page_start,
                    keys=len(page_entries),
                    accumulated=len(entries),
                )
        except S3OperationError:
            raise

        folders = sum(1 for entry in entries if entry.is_prefix)
        files = len(entries) - folders
        log_elapsed(
            logger,
            "list_prefix fetch done",
            fetch_start,
            pages=page_number,
            folders=folders,
            files=files,
            entries=len(entries),
        )

        sort_start = time.perf_counter()
        sorted_entries = self._sort_entries(entries)
        log_elapsed(
            logger,
            "list_prefix sort done",
            sort_start,
            entries=len(sorted_entries),
        )

        log_elapsed(
            logger,
            "list_prefix done",
            total_start,
            entries=len(sorted_entries),
        )
        return sorted_entries

    def iter_prefix_pages(
        self,
        bucket: str,
        prefix: str = "",
        should_cancel: Callable[[], bool] | None = None,
    ):
        """Genera (page_number, page_entries, accumulated) por cada página S3."""
        prefix = self._normalize_prefix(prefix)
        paginator = self._client.get_paginator("list_objects_v2")
        accumulated = 0
        page_number = 0
        try:
            for page in paginator.paginate(
                Bucket=bucket,
                Prefix=prefix,
                Delimiter="/",
            ):
                if should_cancel and should_cancel():
                    logger.info(
                        "list_prefix cancelled bucket=%s prefix=%s page=%s",
                        bucket,
                        prefix or "(root)",
                        page_number,
                    )
                    return
                page_number += 1
                page_entries = self._entries_from_page(page, prefix)
                accumulated += len(page_entries)
                yield page_number, page_entries, accumulated
        except ClientError as exc:
            logger.exception(
                "list_prefix failed bucket=%s prefix=%s pages=%s",
                bucket,
                prefix or "(root)",
                page_number,
            )
            raise S3OperationError(str(exc)) from exc

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        if prefix and not prefix.endswith("/"):
            return prefix + "/"
        return prefix

    @staticmethod
    def _sort_entries(entries: list[S3ListingEntry]) -> list[S3ListingEntry]:
        return sorted(entries, key=lambda e: (not e.is_prefix, e.name.lower()))

    def _entries_from_page(
        self, page: dict, prefix: str
    ) -> list[S3ListingEntry]:
        entries: list[S3ListingEntry] = []
        for common in page.get("CommonPrefixes", []):
            key = common["Prefix"]
            name = key.rstrip("/").split("/")[-1]
            entries.append(S3ListingEntry(name=name, key=key, is_prefix=True))
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key == prefix:
                continue
            name = key.rstrip("/").split("/")[-1]
            entries.append(
                S3ListingEntry(
                    name=name,
                    key=key,
                    is_prefix=False,
                    size=obj.get("Size", 0),
                    last_modified=obj.get("LastModified"),
                )
            )
        return entries

    def list_all_objects(
        self, bucket: str, prefix: str = ""
    ) -> list[S3ListingEntry]:
        """Lista recursivamente todos los objetos bajo un prefijo."""
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"

        entries: list[S3ListingEntry] = []
        paginator = self._client.get_paginator("list_objects_v2")
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue
                    name = key.split("/")[-1]
                    entries.append(
                        S3ListingEntry(
                            name=name,
                            key=key,
                            is_prefix=False,
                            size=obj.get("Size", 0),
                            last_modified=obj.get("LastModified"),
                        )
                    )
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc
        return entries

    def upload_file(
        self,
        local_path: str,
        bucket: str,
        key: str,
        progress: ProgressCallback | None = None,
    ) -> None:
        try:
            self._client.upload_file(
                local_path,
                bucket,
                key,
                Callback=progress,
            )
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc

    def download_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        progress: ProgressCallback | None = None,
    ) -> None:
        try:
            self._client.download_file(
                bucket,
                key,
                local_path,
                Callback=progress,
            )
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc

    def delete_object(self, bucket: str, key: str) -> None:
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc

    def create_folder(self, bucket: str, prefix: str) -> None:
        folder_key = prefix if prefix.endswith("/") else prefix + "/"
        try:
            self._client.put_object(Bucket=bucket, Key=folder_key, Body=b"")
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc

    def rename_object(
        self, bucket: str, old_key: str, new_key: str
    ) -> None:
        try:
            copy_source = {"Bucket": bucket, "Key": old_key}
            self._client.copy_object(
                CopySource=copy_source,
                Bucket=bucket,
                Key=new_key,
            )
            self._client.delete_object(Bucket=bucket, Key=old_key)
        except ClientError as exc:
            raise S3OperationError(str(exc)) from exc
