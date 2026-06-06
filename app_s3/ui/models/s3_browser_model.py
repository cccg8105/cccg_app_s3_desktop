"""Modelo de lista plana para el explorador S3."""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QStyle

from app_s3.domain.models import S3ListingEntry
from app_s3.infrastructure.log_timing import log_elapsed, log_thread_context
from app_s3.infrastructure.s3_repository import S3Repository

logger = logging.getLogger(__name__)

PARENT_ROW_KEY = ".."
COL_CHECK = 0
COL_NAME = 1
COL_SIZE = 2
COL_MODIFIED = 3
ROLE_KEY = Qt.ItemDataRole.UserRole
ROLE_IS_PREFIX = Qt.ItemDataRole.UserRole + 1
ROLE_SEARCH_NAME = Qt.ItemDataRole.UserRole + 2
_APPEND_ROW_LOG_INTERVAL = 500


class S3BrowserModel(QStandardItemModel):
    """Lista el contenido de un prefijo S3 (carpetas y archivos)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["", "Nombre", "Tamaño", "Modificado"])
        self._repo: S3Repository | None = None
        self._bucket = ""
        self._prefix = ""
        self._parent_icon = QIcon()
        self._folder_icon = QIcon()
        self._file_icon = QIcon()
        self._icons_ready = False
        self._folder_count = 0
        self._file_count = 0

    def content_counts(self) -> tuple[int, int]:
        """Retorna (carpetas, archivos) cacheados sin recorrer filas."""
        return self._folder_count, self._file_count

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def prefix(self) -> str:
        return self._prefix

    def start_load(
        self,
        repo: S3Repository | None,
        bucket: str,
        prefix: str = "",
    ) -> None:
        """Prepara el modelo antes de una carga asíncrona."""
        normalized_prefix = (
            prefix if not prefix or prefix.endswith("/") else prefix + "/"
        )
        log_thread_context(
            logger,
            f"start_load bucket={bucket} prefix={normalized_prefix or '(root)'}",
        )
        self._repo = repo
        self._bucket = bucket
        self._prefix = normalized_prefix
        self._folder_count = 0
        self._file_count = 0
        self._ensure_icons()

        clear_start = time.perf_counter()
        self.clear()
        self.setHorizontalHeaderLabels(["", "Nombre", "Tamaño", "Modificado"])
        log_elapsed(logger, "start_load clear done", clear_start)

        if self._prefix:
            self.appendRow(self._make_row("..", PARENT_ROW_KEY, is_prefix=True))

    def append_entries_batch(self, entries: list[S3ListingEntry]) -> None:
        """Agrega entradas en lote; el proxy debe recibir rowsInserted."""
        if not entries:
            return

        build_start = time.perf_counter()
        for index, entry in enumerate(entries, start=1):
            if entry.is_prefix:
                self._folder_count += 1
            else:
                self._file_count += 1
            self.appendRow(
                self._make_row(
                    entry.name,
                    entry.key,
                    is_prefix=entry.is_prefix,
                    size=entry.size,
                    last_modified=entry.last_modified,
                )
            )
            if index % _APPEND_ROW_LOG_INTERVAL == 0:
                log_elapsed(
                    logger,
                    f"append_entries_batch progress rows={index}",
                    build_start,
                )

        log_elapsed(
            logger,
            "append_entries_batch done",
            build_start,
            rows=len(entries),
            total_rows=self.rowCount(),
        )

    def load(
        self,
        repo: S3Repository | None,
        bucket: str,
        prefix: str = "",
    ) -> None:
        """Carga síncrona (tests y rutas simples)."""
        load_start = time.perf_counter()
        self.start_load(repo, bucket, prefix)

        if not repo or not bucket:
            log_elapsed(logger, "load done (empty)", load_start, rows=0)
            return

        fetch_start = time.perf_counter()
        try:
            entries = repo.list_prefix(bucket, self._prefix)
        except Exception:
            logger.exception(
                "list_prefix failed bucket=%s prefix=%s",
                bucket,
                self._prefix or "(root)",
            )
            entries = []
        log_elapsed(
            logger,
            "load list_prefix done",
            fetch_start,
            entries=len(entries),
        )
        self.append_entries_batch(entries)
        log_elapsed(
            logger,
            "load done",
            load_start,
            rows=self.rowCount(),
        )

    def get_entry(self, row: int) -> tuple[str, str, bool]:
        """Retorna (key, display_name, is_prefix) para la fila."""
        name_item = self.item(row, COL_NAME)
        if name_item is None:
            return "", "", False
        key = name_item.data(ROLE_KEY) or ""
        is_prefix = bool(name_item.data(ROLE_IS_PREFIX))
        return key, name_item.text(), is_prefix

    def count_contents(self) -> tuple[int, int]:
        """Retorna (carpetas, archivos) sin contar la fila padre '..'."""
        folders = 0
        files = 0
        for row in range(self.rowCount()):
            key, _, is_prefix = self.get_entry(row)
            if key == PARENT_ROW_KEY:
                continue
            if is_prefix:
                folders += 1
            else:
                files += 1
        return folders, files

    def get_selected_file_keys(self) -> list[str]:
        keys: list[str] = []
        for row in range(self.rowCount()):
            check_item = self.item(row, COL_CHECK)
            if check_item is None or not check_item.isCheckable():
                continue
            if check_item.checkState() != Qt.CheckState.Checked:
                continue
            key, _, is_prefix = self.get_entry(row)
            if key and key != PARENT_ROW_KEY and not is_prefix:
                keys.append(key)
        return keys

    def get_file_rows(self) -> list[int]:
        rows: list[int] = []
        for row in range(self.rowCount()):
            key, _, is_prefix = self.get_entry(row)
            if not is_prefix and key != PARENT_ROW_KEY:
                rows.append(row)
        return rows

    def set_rows_checked(self, rows: list[int], checked: bool) -> int:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        count = 0
        self.blockSignals(True)
        try:
            for row in rows:
                check_item = self.item(row, COL_CHECK)
                if check_item and check_item.isCheckable():
                    check_item.setCheckState(state)
                    count += 1
        finally:
            self.blockSignals(False)
        return count

    def set_all_files_checked(self, checked: bool) -> int:
        return self.set_rows_checked(self.get_file_rows(), checked)

    def _ensure_icons(self) -> None:
        if self._icons_ready:
            return
        app = QApplication.instance()
        if app is None:
            self._icons_ready = True
            return
        style = app.style()
        self._parent_icon = style.standardIcon(
            QStyle.StandardPixmap.SP_FileDialogToParent
        )
        self._folder_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self._icons_ready = True

    def _make_row(
        self,
        name: str,
        key: str,
        is_prefix: bool,
        size: int = 0,
        last_modified=None,
    ) -> list[QStandardItem]:
        check_item = QStandardItem()
        check_item.setEditable(False)
        if not is_prefix and key != PARENT_ROW_KEY:
            check_item.setCheckable(True)
            check_item.setCheckState(Qt.CheckState.Unchecked)
        else:
            check_item.setCheckable(False)

        name_item = QStandardItem(name)
        name_item.setIcon(self._entry_icon(key, is_prefix))
        name_item.setData(key, ROLE_KEY)
        name_item.setData(is_prefix, ROLE_IS_PREFIX)
        name_item.setData(name.lower(), ROLE_SEARCH_NAME)
        name_item.setEditable(False)

        size_text = "" if is_prefix else self._format_size(size)
        size_item = QStandardItem(size_text)
        size_item.setEditable(False)

        modified = ""
        if last_modified:
            modified = last_modified.strftime("%Y-%m-%d %H:%M")
        modified_item = QStandardItem(modified)
        modified_item.setEditable(False)

        return [check_item, name_item, size_item, modified_item]

    def _entry_icon(self, key: str, is_prefix: bool) -> QIcon:
        if key == PARENT_ROW_KEY:
            return self._parent_icon
        if is_prefix:
            return self._folder_icon
        return self._file_icon

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
