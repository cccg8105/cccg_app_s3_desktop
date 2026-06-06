"""Persistencia de bookmarks de buckets."""

from __future__ import annotations

import json

from app_s3.config.paths import bookmarks_file
from app_s3.domain.models import BookmarksStore, BucketBookmark


class BookmarkService:
    def load(self) -> BookmarksStore:
        path = bookmarks_file()
        if not path.exists():
            return BookmarksStore()
        data = json.loads(path.read_text(encoding="utf-8"))
        return BookmarksStore.model_validate(data)

    def save(self, store: BookmarksStore) -> None:
        bookmarks_file().write_text(
            store.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_for_profile(
        self, credential_id: str
    ) -> list[BucketBookmark]:
        store = self.load()
        return [
            b for b in store.bookmarks if b.credential_id == credential_id
        ]

    def add(self, bookmark: BucketBookmark) -> None:
        store = self.load()
        store.bookmarks = [
            b
            for b in store.bookmarks
            if not (
                b.credential_id == bookmark.credential_id
                and b.bucket_name == bookmark.bucket_name
            )
        ]
        store.bookmarks.append(bookmark)
        self.save(store)

    def remove(self, credential_id: str, bucket_name: str) -> None:
        store = self.load()
        store.bookmarks = [
            b
            for b in store.bookmarks
            if not (
                b.credential_id == credential_id
                and b.bucket_name == bucket_name
            )
        ]
        self.save(store)
