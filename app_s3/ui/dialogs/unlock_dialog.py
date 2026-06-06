"""Diálogo de desbloqueo / configuración inicial."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class UnlockDialog(QDialog):
    def __init__(
        self,
        is_first_run: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Configurar contraseña maestra"
            if is_first_run
            else "Desbloquear S3 Desktop"
        )
        self.setModal(True)
        self.resize(440, 220)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        hint = QLabel(
            "Establece una contraseña maestra para cifrar tus credenciales AWS."
            if is_first_run
            else "Introduce tu contraseña maestra para acceder a las credenciales."
        )
        hint.setWordWrap(True)
        hint.setObjectName("dialogHint")
        layout.addWidget(hint)

        form = QFormLayout()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Contraseña maestra")
        form.addRow("Contraseña:", self._password)

        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm.setPlaceholderText("Confirmar contraseña")
        if is_first_run:
            form.addRow("Confirmar:", self._confirm)
        else:
            self._confirm.hide()

        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setObjectName("errorLabel")
        self._error.hide()
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._is_first_run = is_first_run
        self._master_password = ""

    @property
    def master_password(self) -> str:
        return self._master_password

    def _validate(self) -> None:
        pwd = self._password.text()
        if not pwd:
            self._show_error("La contraseña no puede estar vacía.")
            return
        if self._is_first_run and pwd != self._confirm.text():
            self._show_error("Las contraseñas no coinciden.")
            return
        self._master_password = pwd
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()
