"""Proxy de filtrado para el explorador S3."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel

from app_s3.ui.models.s3_browser_model import (
    COL_NAME,
    PARENT_ROW_KEY,
    ROLE_IS_PREFIX,
    ROLE_KEY,
    ROLE_SEARCH_NAME,
    S3BrowserModel,
)


class S3BrowserFilterProxy(QSortFilterProxyModel):
    """Filtra archivos por nombre; mantiene visibles carpetas y la fila padre."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._name_filter = ""

    def set_name_filter(self, text: str) -> None:
        self._name_filter = text.strip().lower()
        self.invalidateFilter()

    def name_filter(self) -> str:
        return self._name_filter

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        if not isinstance(model, S3BrowserModel):
            return True

        name_item = model.item(source_row, COL_NAME)
        if name_item is None:
            return False

        key = name_item.data(ROLE_KEY) or ""
        if key == PARENT_ROW_KEY or bool(name_item.data(ROLE_IS_PREFIX)):
            return True
        if not self._name_filter:
            return True

        search_name = name_item.data(ROLE_SEARCH_NAME) or ""
        return self._name_filter in search_name

    def count_visible_files(self) -> int:
        """Cuenta archivos visibles tras el filtro (un solo recorrido)."""
        model = self.sourceModel()
        if not isinstance(model, S3BrowserModel):
            return 0

        count = 0
        for proxy_row in range(self.rowCount()):
            source_index = self.mapToSource(self.index(proxy_row, COL_NAME))
            name_item = model.item(source_index.row(), COL_NAME)
            if name_item is None:
                continue
            key = name_item.data(ROLE_KEY) or ""
            if key == PARENT_ROW_KEY or bool(name_item.data(ROLE_IS_PREFIX)):
                continue
            count += 1
        return count

    def visible_file_source_rows(self) -> list[int]:
        """Filas fuente de archivos visibles tras aplicar el filtro."""
        model = self.sourceModel()
        if not isinstance(model, S3BrowserModel):
            return []

        rows: list[int] = []
        for proxy_row in range(self.rowCount()):
            source_index = self.mapToSource(self.index(proxy_row, COL_NAME))
            source_row = source_index.row()
            name_item = model.item(source_row, COL_NAME)
            if name_item is None:
                continue
            key = name_item.data(ROLE_KEY) or ""
            if not bool(name_item.data(ROLE_IS_PREFIX)) and key != PARENT_ROW_KEY:
                rows.append(source_row)
        return rows
