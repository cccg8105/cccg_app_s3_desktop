"""Diálogo para agregar bucket bookmark."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class AddBucketDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Agregar bucket")
        self.resize(400, 120)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._bucket_input = QLineEdit()
        self._bucket_input.setPlaceholderText("mi-bucket-produccion")
        form.addRow("Bucket:", self._bucket_input)

        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def bucket_name(self) -> str:
        return self._bucket_input.text().strip()

    def _validate(self) -> None:
        if not self.bucket_name:
            self._error.setText("El nombre del bucket no puede estar vacío.")
            self._error.show()
            return
        self.accept()
