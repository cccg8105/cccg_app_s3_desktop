"""Panel de cola de transferencias."""

from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app_s3.domain.models import TransferStatus, TransferTask


class TransferPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("transferPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        title = QLabel("Transferencias")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Dirección", "Archivo", "Estado", "Progreso"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        self._task_rows: dict[str, int] = {}

    def add_task(self, task: TransferTask) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._task_rows[task.id] = row

        self._table.setItem(row, 0, QTableWidgetItem(task.direction.value))
        name = task.s3_key if task.direction.value == "download" else task.local_path
        self._table.setItem(row, 1, QTableWidgetItem(name))
        self._table.setItem(row, 2, QTableWidgetItem(task.status.value))

        progress = QProgressBar()
        progress.setRange(0, max(task.total_bytes, 1))
        progress.setValue(task.bytes_transferred)
        self._table.setCellWidget(row, 3, progress)

    def update_task(self, task: TransferTask) -> None:
        row = self._task_rows.get(task.id)
        if row is None:
            self.add_task(task)
            row = self._task_rows[task.id]

        status_item = self._table.item(row, 2)
        if status_item:
            status_item.setText(task.status.value)
        widget = self._table.cellWidget(row, 3)
        if isinstance(widget, QProgressBar):
            total = max(task.total_bytes, task.bytes_transferred, 1)
            widget.setRange(0, total)
            widget.setValue(task.bytes_transferred)
            if task.status == TransferStatus.COMPLETED:
                widget.setValue(total)
