"""Explorador S3 estilo lista de archivos con drag-and-drop."""

from __future__ import annotations

import logging
import threading
import time

from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionHeader,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app_s3.infrastructure.log_timing import log_elapsed
from app_s3.infrastructure.s3_repository import S3Repository
from app_s3.ui.models.s3_browser_model import (
    COL_CHECK,
    COL_MODIFIED,
    COL_NAME,
    COL_SIZE,
    PARENT_ROW_KEY,
    S3BrowserModel,
)
from app_s3.ui.models.s3_browser_proxy import S3BrowserFilterProxy
from app_s3.ui.widgets.loading_overlay import LoadingOverlay
from app_s3.ui.workers.listing_worker import ListingSignals, ListingWorker

logger = logging.getLogger(__name__)

_BATCH_THRESHOLD = 300
_BATCH_SIZE = 200
_POPULATE_BATCH_SIZE = 200
_LABEL_SELECT_ALL = "Seleccionar todo"
_LABEL_DESELECT_ALL = "Deseleccionar todo"
_MIN_CHECK_COLUMN_WIDTH = 32
_SIZE_COLUMN_WIDTH = 96
_MODIFIED_COLUMN_WIDTH = 150
_MIN_NAME_COLUMN_WIDTH = 80


class _CheckColumnHeaderView(QHeaderView):
    """Cabecera de la columna de selección con icono de casilla."""

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip("Seleccionar archivos")

    def paintSection(self, painter: QPainter, rect, logical_index: int) -> None:
        if logical_index != COL_CHECK:
            super().paintSection(painter, rect, logical_index)
            return

        painter.save()
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logical_index
        option.text = ""
        option.state = QStyle.StateFlag.State_Enabled
        self.style().drawControl(
            QStyle.ControlElement.CE_Header,
            option,
            painter,
            self,
        )

        check_option = QStyleOptionButton()
        check_option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Off
        indicator = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            check_option,
            self,
        )
        x = rect.x() + (rect.width() - indicator.width()) // 2
        y = rect.y() + (rect.height() - indicator.height()) // 2
        check_option.rect = indicator.translated(x - indicator.x(), y - indicator.y())
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_IndicatorCheckBox,
            check_option,
            painter,
            self,
        )
        painter.restore()


class _CheckBoxColumnDelegate(QStyledItemDelegate):
    """Centra los checkboxes y evita que el padding del tema los recorte."""

    def paint(self, painter, option, index) -> None:
        if index.column() != COL_CHECK:
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if not (opt.features & QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator):
            return

        opt.text = ""
        opt.displayAlignment = Qt.AlignmentFlag.AlignCenter
        widget = option.widget
        if widget is not None:
            widget.style().drawControl(
                QStyle.ControlElement.CE_ItemViewItem,
                opt,
                painter,
                widget,
            )

    def sizeHint(self, option, index):
        if index.column() == COL_CHECK:
            return QSize(_MIN_CHECK_COLUMN_WIDTH, 24)
        return super().sizeHint(option, index)


class S3BrowserTable(QTableView):
    """Tabla con soporte de arrastre desde el Explorador de Windows."""

    def __init__(self, browser: "S3BrowserWidget", parent=None) -> None:
        super().__init__(parent)
        self._browser = browser

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        self._browser._handle_drag_enter(event)

    def dragMoveEvent(self, event) -> None:
        self._browser._handle_drag_move(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._browser._handle_drop(event)


class S3BrowserWidget(QWidget):
    """Vista de archivos S3 con navegación por carpetas y subida por arrastre."""

    files_dropped = Signal(list, str)
    download_requested = Signal(str)
    download_many_requested = Signal(list)
    delete_requested = Signal(str)
    create_folder_requested = Signal()
    rename_requested = Signal(str, str)
    navigation_changed = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("s3Browser")
        self._repo: S3Repository | None = None
        self._bucket = ""
        self._prefix = ""
        self._select_all_rows: list[int] = []
        self._select_all_checked = True
        self._select_all_batch_index = 0
        self._load_generation = 0
        self._listing_cancel: threading.Event | None = None
        self._pending_entries: list = []
        self._populate_index = 0
        self._populate_generation = 0
        self._navigate_start = 0.0
        self._listing_signals = ListingSignals(self)
        self._active_listing_worker: ListingWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        nav_row = QHBoxLayout()
        self._up_btn = QPushButton("↑ Subir")
        self._up_btn.setToolTip("Volver a la carpeta anterior")
        self._up_btn.clicked.connect(self._go_up)
        self._up_btn.setEnabled(False)
        nav_row.addWidget(self._up_btn)

        self._refresh_btn = QPushButton("Actualizar")
        self._refresh_btn.setToolTip("Recargar el contenido de la carpeta actual")
        self._refresh_btn.clicked.connect(self.refresh)
        nav_row.addWidget(self._refresh_btn)

        self._new_folder_btn = QPushButton("Nueva carpeta")
        self._new_folder_btn.setToolTip("Crear una carpeta en la ubicación actual")
        self._new_folder_btn.clicked.connect(self.create_folder_requested.emit)
        nav_row.addWidget(self._new_folder_btn)

        self._select_all_btn = QPushButton(_LABEL_SELECT_ALL)
        self._select_all_btn.setToolTip(
            "Marcar la casilla de todos los archivos visibles"
        )
        self._select_all_btn.clicked.connect(self._select_all_files)
        nav_row.addWidget(self._select_all_btn)

        self._download_btn = QPushButton("Descargar seleccionados")
        self._download_btn.setObjectName("primaryButton")
        self._download_btn.setToolTip(
            "Descargar a tu equipo los archivos marcados con la casilla"
        )
        self._download_btn.clicked.connect(self._download_selected)
        self._download_btn.setEnabled(False)
        nav_row.addWidget(self._download_btn)

        self._delete_btn = QPushButton("Eliminar")
        self._delete_btn.setToolTip(
            "Eliminar el archivo o carpeta seleccionado en la lista"
        )
        self._delete_btn.clicked.connect(self._delete_selected)
        self._delete_btn.setEnabled(False)
        nav_row.addWidget(self._delete_btn)

        layout.addLayout(nav_row)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Ruta:"))
        self._path_display = QLineEdit()
        self._path_display.setObjectName("pathDisplay")
        self._path_display.setReadOnly(True)
        path_row.addWidget(self._path_display, stretch=1)
        layout.addLayout(path_row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrar:"))
        self._filter_input = QLineEdit()
        self._filter_input.setObjectName("nameFilter")
        self._filter_input.setPlaceholderText("Nombre de archivo...")
        self._filter_input.setClearButtonEnabled(True)
        self._filter_input.setToolTip(
            "Escriba el texto y pulse Filtrar (o Enter) para acotar archivos"
        )
        self._filter_input.returnPressed.connect(self._apply_name_filter)
        filter_row.addWidget(self._filter_input, stretch=1)

        self._apply_filter_btn = QPushButton("Filtrar")
        self._apply_filter_btn.setObjectName("filterAction")
        self._apply_filter_btn.setToolTip("Aplicar filtro por nombre de archivo")
        self._apply_filter_btn.clicked.connect(self._apply_name_filter)
        filter_row.addWidget(self._apply_filter_btn)

        self._clear_filter_btn = QPushButton("Limpiar")
        self._clear_filter_btn.setObjectName("filterAction")
        self._clear_filter_btn.setToolTip("Quitar filtro y mostrar todos los archivos")
        self._clear_filter_btn.clicked.connect(self._clear_name_filter)
        filter_row.addWidget(self._clear_filter_btn)

        self._stats_label = QLabel("")
        self._stats_label.setObjectName("folderStats")
        self._stats_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        filter_row.addWidget(self._stats_label)
        layout.addLayout(filter_row)

        self._model = S3BrowserModel()
        self._model.itemChanged.connect(self._on_item_changed)
        self._proxy_model = S3BrowserFilterProxy()
        self._proxy_model.setSourceModel(self._model)
        self._table = S3BrowserTable(self)
        check_header = _CheckColumnHeaderView(self._table)
        self._table.setHorizontalHeader(check_header)
        self._table.setModel(self._proxy_model)
        self._table.setItemDelegate(_CheckBoxColumnDelegate(self._table))
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setAcceptDrops(True)
        self._table.setDropIndicatorShown(True)
        self._table.setDragDropMode(QTableView.DragDropMode.DropOnly)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._table.verticalHeader().setVisible(False)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)
        selection_model = self._table.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(
                lambda *_args: self._update_delete_button()
            )
        header = self._table.horizontalHeader()
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        header.setMinimumSectionSize(_MIN_CHECK_COLUMN_WIDTH)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_MODIFIED, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_CHECK, _MIN_CHECK_COLUMN_WIDTH)
        header.resizeSection(COL_SIZE, _SIZE_COLUMN_WIDTH)
        header.resizeSection(COL_MODIFIED, _MODIFIED_COLUMN_WIDTH)
        layout.addWidget(self._table, stretch=1)

        self._loading_overlay = LoadingOverlay(self._table)
        self._loading_overlay.hide()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit_table_columns()
        self._sync_loading_overlay_geometry()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fit_table_columns()
        self._sync_loading_overlay_geometry()

    def _sync_loading_overlay_geometry(self) -> None:
        overlay = self._loading_overlay
        if overlay.isVisible() and overlay.parent() is self._table:
            overlay.setGeometry(self._table.rect())

    def _fit_table_columns(self) -> None:
        """Ajusta la columna Nombre para ocupar el ancho restante del viewport."""
        header = self._table.horizontalHeader()
        viewport_width = self._table.viewport().width()
        if viewport_width <= 0:
            return

        fixed_width = (
            header.sectionSize(COL_CHECK)
            + header.sectionSize(COL_SIZE)
            + header.sectionSize(COL_MODIFIED)
        )
        name_width = max(_MIN_NAME_COLUMN_WIDTH, viewport_width - fixed_width)
        if abs(header.sectionSize(COL_NAME) - name_width) > 1:
            header.resizeSection(COL_NAME, name_width)

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def prefix(self) -> str:
        return self._prefix

    def set_repository(self, repo: S3Repository | None) -> None:
        self._repo = repo

    def _cancel_listing(self) -> None:
        if self._listing_cancel is not None:
            self._listing_cancel.set()

    def _release_listing_worker(self) -> None:
        self._active_listing_worker = None

    def _disconnect_listing_signals(self) -> None:
        self._listing_signals.progress.disconnect()
        self._listing_signals.finished.disconnect()
        self._listing_signals.failed.disconnect()

    def _set_loading(self, loading: bool) -> None:
        self._table.setEnabled(not loading)
        self._filter_input.setEnabled(not loading)
        self._refresh_btn.setEnabled(not loading and bool(self._bucket))
        self._select_all_btn.setEnabled(not loading)
        has_selection = bool(self._model.get_selected_file_keys())
        self._download_btn.setEnabled(not loading and has_selection)
        if loading:
            self._delete_btn.setEnabled(False)

    def navigate_to(self, bucket: str, prefix: str = "") -> None:
        self._cancel_listing()
        self._load_generation += 1
        generation = self._load_generation
        self._listing_cancel = threading.Event()

        self._navigate_start = time.perf_counter()
        self._bucket = bucket
        self._prefix = prefix if not prefix or prefix.endswith("/") else prefix + "/"
        path = self._format_path()
        logger.info("navigate_to start path=%s", path or "(empty)")

        self._up_btn.setEnabled(bool(self._prefix))
        self._path_display.setText(path)
        self._reset_name_filter()
        self._stats_label.setText("Cargando...")
        self._model.start_load(self._repo, self._bucket, self._prefix)

        if not self._repo or not bucket:
            self._update_folder_stats()
            self._finish_navigation(generation)
            return

        self._set_loading(True)
        self._loading_overlay.show_overlay("Listando archivos desde S3...")
        self._sync_loading_overlay_geometry()

        self._disconnect_listing_signals()
        self._listing_signals.progress.connect(
            lambda page, accumulated: self._on_listing_progress(
                generation, page, accumulated
            )
        )
        self._listing_signals.finished.connect(
            lambda entries: self._on_listing_finished(generation, entries)
        )
        self._listing_signals.failed.connect(
            lambda message: self._on_listing_failed(generation, message)
        )

        worker = ListingWorker(
            self._repo,
            bucket,
            self._prefix,
            self._listing_cancel,
            self._listing_signals,
        )
        self._active_listing_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_listing_progress(
        self, generation: int, page: int, accumulated: int
    ) -> None:
        if generation != self._load_generation:
            return
        self._loading_overlay.show_overlay(
            f"Listando archivos... pagina {page} ({accumulated} encontrados)"
        )
        self._sync_loading_overlay_geometry()
        self._stats_label.setText(
            f"Listando... {self._format_count(accumulated)} encontrados"
        )

    def _on_listing_finished(self, generation: int, entries: list) -> None:
        if generation != self._load_generation:
            return
        logger.info(
            "navigate_to listing finished entries=%s generation=%s",
            len(entries),
            generation,
        )
        if not entries:
            self._finish_navigation(generation)
            return

        self._pending_entries = entries
        self._populate_index = 0
        self._populate_generation = generation
        self._loading_overlay.show_overlay(f"Mostrando {len(entries)} archivos...")
        QTimer.singleShot(0, self._populate_next_batch)

    def _populate_next_batch(self) -> None:
        if self._populate_generation != self._load_generation:
            return

        start = self._populate_index
        end = min(start + _POPULATE_BATCH_SIZE, len(self._pending_entries))
        batch = self._pending_entries[start:end]
        self._model.append_entries_batch(batch)
        self._populate_index = end

        if self._populate_index < len(self._pending_entries):
            total = len(self._pending_entries)
            self._loading_overlay.show_overlay(
                f"Mostrando archivos... {self._populate_index}/{total}"
            )
            QTimer.singleShot(0, self._populate_next_batch)
            return

        self._pending_entries = []
        self._finish_navigation(self._load_generation)
        self._proxy_model.invalidate()
        self._table.viewport().update()

    def _on_listing_failed(self, generation: int, message: str) -> None:
        if generation != self._load_generation:
            return
        logger.error("navigate_to listing failed: %s", message)
        self._finish_navigation(generation)

    def _finish_navigation(self, generation: int) -> None:
        if generation != self._load_generation:
            return

        self._set_loading(False)
        self._loading_overlay.hide_overlay()
        self._release_listing_worker()

        logger.info(
            "_finish_navigation generation=%s rows=%s",
            generation,
            self._model.rowCount(),
        )

        resize_start = time.perf_counter()
        self._resize_check_column()
        log_elapsed(logger, "navigate_to resize_check_column done", resize_start)

        fit_start = time.perf_counter()
        self._fit_table_columns()
        log_elapsed(logger, "navigate_to fit_table_columns done", fit_start)

        buttons_start = time.perf_counter()
        self._update_download_button()
        self._update_delete_button()
        log_elapsed(logger, "navigate_to update_buttons done", buttons_start)

        self._update_folder_stats()
        self.navigation_changed.emit(self._bucket, self._prefix)
        log_elapsed(
            logger,
            "navigate_to done",
            self._navigate_start,
            path=self._format_path() or "(empty)",
        )

    def _reset_name_filter(self) -> None:
        self._filter_input.blockSignals(True)
        self._filter_input.clear()
        self._filter_input.blockSignals(False)
        self._proxy_model.set_name_filter("")

    def _apply_name_filter(self) -> None:
        self._proxy_model.set_name_filter(self._filter_input.text())
        self._update_folder_stats()
        self._update_select_all_button_text()

    def _clear_name_filter(self) -> None:
        self._reset_name_filter()
        self._update_folder_stats()
        self._update_select_all_button_text()

    @staticmethod
    def _format_count(value: int) -> str:
        return f"{value:,}".replace(",", ".")

    def _update_folder_stats(self) -> None:
        if not self._bucket:
            self._stats_label.setText("")
            return

        folders, files = self._model.content_counts()
        if folders == 0 and files == 0:
            self._stats_label.setText("Carpeta vacía")
            return

        parts: list[str] = []
        if folders:
            label = "carpeta" if folders == 1 else "carpetas"
            parts.append(f"{self._format_count(folders)} {label}")
        file_label = "archivo" if files == 1 else "archivos"
        parts.append(f"{self._format_count(files)} {file_label}")
        text = " · ".join(parts)

        if self._proxy_model.name_filter():
            visible_files = self._proxy_model.count_visible_files()
            text += f" (mostrando {self._format_count(visible_files)})"

        self._stats_label.setText(text)

    def _source_row(self, proxy_row: int) -> int:
        source_index = self._proxy_model.mapToSource(
            self._proxy_model.index(proxy_row, COL_NAME)
        )
        return source_index.row()

    def _entry_at_proxy_row(self, proxy_row: int) -> tuple[str, str, bool]:
        return self._model.get_entry(self._source_row(proxy_row))

    def _entry_at_index(self, index) -> tuple[str, str, bool]:
        source_index = self._proxy_model.mapToSource(index)
        return self._model.get_entry(source_index.row())

    def refresh(self) -> None:
        if self._bucket:
            self.navigate_to(self._bucket, self._prefix)

    def _check_column_width(self) -> int:
        style = self.style()
        indicator = style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth)
        margin = style.pixelMetric(
            QStyle.PixelMetric.PM_FocusFrameHMargin, None, self
        )
        return max(_MIN_CHECK_COLUMN_WIDTH, indicator + margin * 2 + 8)

    def _resize_check_column(self) -> None:
        width = self._check_column_width()
        self._table.horizontalHeader().resizeSection(COL_CHECK, width)
        self._fit_table_columns()

    def _format_path(self) -> str:
        if not self._bucket:
            return ""
        base = f"s3://{self._bucket}/"
        if self._prefix:
            return base + self._prefix
        return base

    def _go_up(self) -> None:
        if not self._prefix:
            return
        parts = self._prefix.rstrip("/").split("/")
        parts.pop()
        new_prefix = "/".join(parts)
        if new_prefix:
            new_prefix += "/"
        self.navigate_to(self._bucket, new_prefix)

    def _on_double_click(self, index) -> None:
        if index.column() == 0:
            return
        key, _name, is_prefix = self._entry_at_index(index)
        if key == PARENT_ROW_KEY:
            self._go_up()
            return
        if is_prefix:
            self.navigate_to(self._bucket, key)

    def _drop_target_prefix(self, row: int | None) -> str:
        if row is not None and row >= 0:
            key, _name, is_prefix = self._entry_at_proxy_row(row)
            if key == PARENT_ROW_KEY:
                return self._prefix
            if is_prefix and key:
                return key if key.endswith("/") else key + "/"
        return self._prefix

    def _handle_drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and self._bucket:
            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_drag_move(self, event) -> None:
        if event.mimeData().hasUrls() and self._bucket:
            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_drop(self, event: QDropEvent) -> None:
        if not event.mimeData().hasUrls() or not self._bucket:
            event.ignore()
            return

        index = self._table.indexAt(event.position().toPoint())
        row = index.row() if index.isValid() else None
        target_prefix = self._drop_target_prefix(row)

        local_paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.toLocalFile()
        ]
        if not local_paths:
            event.ignore()
            return

        self.files_dropped.emit(local_paths, target_prefix)
        event.acceptProposedAction()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        self._handle_drag_enter(event)

    def dragMoveEvent(self, event) -> None:
        self._handle_drag_move(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._handle_drop(event)

    def _show_context_menu(self, pos) -> None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            menu = QMenu(self)
            paste_action = menu.addAction("Subir archivos aquí...")
            paste_action.setEnabled(False)
            new_folder = menu.addAction("Nueva carpeta")
            new_folder.triggered.connect(self.create_folder_requested.emit)
            menu.exec(self._table.viewport().mapToGlobal(pos))
            return

        row = index.row()
        key, _name, is_prefix = self._entry_at_proxy_row(row)
        if key == PARENT_ROW_KEY:
            return

        menu = QMenu(self)
        if is_prefix:
            open_action = menu.addAction("Abrir")
            open_action.triggered.connect(
                lambda: self.navigate_to(self._bucket, key)
            )
            new_folder = menu.addAction("Nueva carpeta")
            new_folder.triggered.connect(self.create_folder_requested.emit)
        else:
            download_action = menu.addAction("Descargar")
            download_action.triggered.connect(
                lambda: self.download_requested.emit(key)
            )

        if key:
            delete_action = menu.addAction("Eliminar")
            delete_action.triggered.connect(
                lambda: self.delete_requested.emit(key)
            )
            rename_action = menu.addAction("Renombrar")
            rename_action.triggered.connect(
                lambda: self._prompt_rename(key)
            )

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _prompt_rename(self, key: str) -> None:
        from PySide6.QtWidgets import QInputDialog

        old_name = key.rstrip("/").split("/")[-1]
        new_name, ok = QInputDialog.getText(
            self, "Renombrar", "Nuevo nombre:", text=old_name
        )
        if ok and new_name and new_name != old_name:
            parent = key[: -len(old_name)] if key.endswith(old_name) else ""
            new_key = parent + new_name
            if key.endswith("/"):
                new_key += "/"
            self.rename_requested.emit(key, new_key)

    def _on_item_changed(self, item) -> None:
        if item.column() == 0:
            self._update_selection_controls()

    def _are_all_files_selected(self) -> bool:
        file_rows = self._proxy_model.visible_file_source_rows()
        if not file_rows:
            return False
        return all(
            self._model.item(row, COL_CHECK)
            and self._model.item(row, COL_CHECK).checkState()
            == Qt.CheckState.Checked
            for row in file_rows
        )

    def _update_select_all_button_text(self) -> None:
        if self._are_all_files_selected():
            self._select_all_btn.setText(_LABEL_DESELECT_ALL)
            self._select_all_btn.setToolTip(
                "Quitar la selección de todos los archivos visibles"
            )
        else:
            self._select_all_btn.setText(_LABEL_SELECT_ALL)
            self._select_all_btn.setToolTip(
                "Marcar la casilla de todos los archivos visibles"
            )

    def _update_selection_controls(self) -> None:
        selected = self._model.get_selected_file_keys()
        self._download_btn.setEnabled(len(selected) > 0)
        self._update_select_all_button_text()

    def _update_download_button(self) -> None:
        self._update_selection_controls()

    def _update_delete_button(self) -> None:
        if not self._repo or not self._bucket:
            self._delete_btn.setEnabled(False)
            return
        indexes = self._table.selectionModel().selectedRows()
        if len(indexes) != 1:
            self._delete_btn.setEnabled(False)
            return
        row = indexes[0].row()
        key, _name, _is_prefix = self._entry_at_proxy_row(row)
        self._delete_btn.setEnabled(bool(key) and key != PARENT_ROW_KEY)

    def _delete_selected(self) -> None:
        indexes = self._table.selectionModel().selectedRows()
        if len(indexes) != 1:
            return
        row = indexes[0].row()
        key, _name, _is_prefix = self._entry_at_proxy_row(row)
        if key and key != PARENT_ROW_KEY:
            self.delete_requested.emit(key)

    def _select_all_files(self) -> None:
        file_rows = self._proxy_model.visible_file_source_rows()
        if not file_rows:
            return

        all_selected = self._are_all_files_selected()
        self._select_all_rows = file_rows
        self._select_all_checked = not all_selected
        self._select_all_batch_index = 0

        message = (
            "Seleccionando archivos..."
            if self._select_all_checked
            else "Desmarcando archivos..."
        )
        self._loading_overlay.show_overlay(message)
        self._select_all_btn.setEnabled(False)
        self._download_btn.setEnabled(False)
        QTimer.singleShot(0, self._apply_select_all_batch)

    def _apply_select_all_batch(self) -> None:
        rows = self._select_all_rows
        if len(rows) <= _BATCH_THRESHOLD:
            self._model.set_rows_checked(rows, self._select_all_checked)
            self._finish_select_all()
            return

        start = self._select_all_batch_index
        end = min(start + _BATCH_SIZE, len(rows))
        batch = rows[start:end]
        self._model.set_rows_checked(batch, self._select_all_checked)
        self._select_all_batch_index = end
        if end < len(rows):
            QTimer.singleShot(0, self._apply_select_all_batch)
        else:
            self._finish_select_all()

    def _finish_select_all(self) -> None:
        self._loading_overlay.hide_overlay()
        self._select_all_btn.setEnabled(True)
        self._update_download_button()

    def _download_selected(self) -> None:
        keys = self._model.get_selected_file_keys()
        if keys:
            self.download_many_requested.emit(keys)
