"""Operaciones del sistema de archivos local."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class LocalFileEntry:
    relative_path: str
    absolute_path: str
    size: int
    mtime: datetime
    is_dir: bool


class LocalFileSystem:
    """Acceso al filesystem local para sync y transferencias."""

    def ensure_parent(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def scan_directory(self, root: str | Path) -> list[LocalFileEntry]:
        root_path = Path(root)
        if not root_path.exists():
            return []

        entries: list[LocalFileEntry] = []
        for dirpath, _dirnames, filenames in os.walk(root_path):
            dir_path = Path(dirpath)
            rel_dir = dir_path.relative_to(root_path).as_posix()
            if rel_dir != ".":
                mtime = datetime.fromtimestamp(
                    dir_path.stat().st_mtime, tz=timezone.utc
                )
                entries.append(
                    LocalFileEntry(
                        relative_path=rel_dir + "/",
                        absolute_path=str(dir_path),
                        size=0,
                        mtime=mtime,
                        is_dir=True,
                    )
                )
            for name in filenames:
                file_path = dir_path / name
                rel = file_path.relative_to(root_path).as_posix()
                stat = file_path.stat()
                entries.append(
                    LocalFileEntry(
                        relative_path=rel,
                        absolute_path=str(file_path),
                        size=stat.st_size,
                        mtime=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ),
                        is_dir=False,
                    )
                )
        return entries
