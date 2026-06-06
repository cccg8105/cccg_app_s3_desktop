"""Diálogo CRUD de credenciales AWS."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app_s3.domain.models import CredentialProfile


class CredentialDialog(QDialog):
    def __init__(
        self,
        profile: CredentialProfile | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appDialog")
        self.setWindowTitle(
            "Editar credencial" if profile else "Nueva credencial AWS"
        )
        self.resize(480, 320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._alias = QLineEdit()
        self._alias.setPlaceholderText("Mi cuenta AWS")
        form.addRow("Alias:", self._alias)

        self._access_key = QLineEdit()
        form.addRow("Access Key ID:", self._access_key)

        secret_row = QHBoxLayout()
        self._secret_key = QLineEdit()
        self._secret_key.setEchoMode(QLineEdit.EchoMode.Password)
        reveal_btn = QPushButton("Mostrar")
        reveal_btn.setCheckable(True)
        reveal_btn.toggled.connect(self._toggle_secret)
        secret_row.addWidget(self._secret_key)
        secret_row.addWidget(reveal_btn)
        form.addRow("Secret Access Key:", secret_row)

        self._region = QLineEdit("us-east-1")
        form.addRow("Región:", self._region)

        self._session_token = QLineEdit()
        self._session_token.setPlaceholderText("Opcional")
        form.addRow("Session Token:", self._session_token)

        self._endpoint = QLineEdit()
        self._endpoint.setPlaceholderText("Opcional (MinIO, LocalStack)")
        form.addRow("Endpoint URL:", self._endpoint)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._profile_id = profile.id if profile else None
        if profile:
            self._alias.setText(profile.alias)
            self._access_key.setText(profile.access_key_id)
            self._secret_key.setText(profile.secret_access_key)
            self._region.setText(profile.region)
            if profile.session_token:
                self._session_token.setText(profile.session_token)
            if profile.endpoint_url:
                self._endpoint.setText(profile.endpoint_url)

    def _toggle_secret(self, checked: bool) -> None:
        mode = (
            QLineEdit.EchoMode.Normal
            if checked
            else QLineEdit.EchoMode.Password
        )
        self._secret_key.setEchoMode(mode)

    def get_profile(self) -> CredentialProfile:
        data = {
            "alias": self._alias.text().strip(),
            "access_key_id": self._access_key.text().strip(),
            "secret_access_key": self._secret_key.text().strip(),
            "region": self._region.text().strip() or "us-east-1",
            "session_token": self._session_token.text().strip() or None,
            "endpoint_url": self._endpoint.text().strip() or None,
        }
        if self._profile_id:
            data["id"] = self._profile_id
        return CredentialProfile.model_validate(data)

    @staticmethod
    def confirm_delete(parent, alias: str) -> bool:
        reply = QMessageBox.question(
            parent,
            "Eliminar credencial",
            f"¿Eliminar la credencial '{alias}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes
