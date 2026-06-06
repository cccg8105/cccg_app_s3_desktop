"""Diálogo CRUD de jobs de sincronización."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app_s3.domain.models import (
    ConflictPolicy,
    CredentialProfile,
    DeletePolicy,
    SyncDirection,
    SyncJob,
)

_DIRECTION_LABELS = {
    SyncDirection.BIDIRECTIONAL: "Bidireccional",
    SyncDirection.UPLOAD_ONLY: "Solo subida",
    SyncDirection.DOWNLOAD_ONLY: "Solo descarga",
}

_CONFLICT_LABELS = {
    ConflictPolicy.NEWER_WINS: "Gana el más reciente",
    ConflictPolicy.S3_WINS: "Gana S3",
    ConflictPolicy.LOCAL_WINS: "Gana carpeta local",
    ConflictPolicy.MANUAL: "Resolver manualmente",
}

_DELETE_LABELS = {
    DeletePolicy.SAFE: "Seguro (no borra)",
    DeletePolicy.MIRROR: "Espejo (sincroniza borrados)",
}


class SyncJobDialog(QDialog):
    def __init__(
        self,
        profiles: list[CredentialProfile],
        job: SyncJob | None = None,
        default_credential_id: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appDialog")
        self.setWindowTitle("Editar job de sync" if job else "Nuevo job de sync")
        self.resize(540, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setSpacing(10)

        self._name = QLineEdit()
        form.addRow("Nombre:", self._name)

        self._profile_combo = QComboBox()
        for profile in profiles:
            self._profile_combo.addItem(profile.alias, profile.id)
        form.addRow("Credencial:", self._profile_combo)

        self._bucket = QLineEdit()
        form.addRow("Bucket:", self._bucket)

        self._prefix = QLineEdit()
        self._prefix.setPlaceholderText("carpeta/subcarpeta/")
        form.addRow("Prefijo S3:", self._prefix)

        local_row = QHBoxLayout()
        self._local_path = QLineEdit()
        browse_btn = QPushButton("Examinar...")
        browse_btn.setToolTip("Elegir la carpeta local a sincronizar")
        browse_btn.clicked.connect(self._browse_local)
        local_row.addWidget(self._local_path)
        local_row.addWidget(browse_btn)
        form.addRow("Carpeta local:", local_row)

        self._direction = QComboBox()
        for direction in SyncDirection:
            self._direction.addItem(
                _DIRECTION_LABELS[direction],
                direction,
            )
        form.addRow("Dirección:", self._direction)

        self._conflict = QComboBox()
        for policy in ConflictPolicy:
            self._conflict.addItem(_CONFLICT_LABELS[policy], policy)
        form.addRow("Conflicto:", self._conflict)

        self._delete_policy = QComboBox()
        for policy in DeletePolicy:
            self._delete_policy.addItem(_DELETE_LABELS[policy], policy)
        form.addRow("Eliminaciones:", self._delete_policy)

        self._interval = QSpinBox()
        self._interval.setRange(1, 10080)
        self._interval.setValue(60)
        self._interval.setSuffix(" min")
        form.addRow("Intervalo:", self._interval)

        self._cron = QLineEdit()
        self._cron.setPlaceholderText("Opcional: 0 */6 * * *")
        form.addRow("Cron:", self._cron)

        self._enabled = QCheckBox("Habilitado")
        self._enabled.setChecked(True)
        form.addRow("", self._enabled)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._job_id = job.id if job else None
        if job:
            self._name.setText(job.name)
            idx = self._profile_combo.findData(job.credential_id)
            if idx >= 0:
                self._profile_combo.setCurrentIndex(idx)
            self._bucket.setText(job.bucket)
            self._prefix.setText(job.s3_prefix)
            self._local_path.setText(job.local_path)
            self._set_combo(self._direction, job.direction)
            self._set_combo(self._conflict, job.conflict_policy)
            self._set_combo(self._delete_policy, job.delete_policy)
            if job.schedule_interval_minutes:
                self._interval.setValue(job.schedule_interval_minutes)
            if job.schedule_cron:
                self._cron.setText(job.schedule_cron)
            self._enabled.setChecked(job.enabled)
        elif default_credential_id:
            idx = self._profile_combo.findData(default_credential_id)
            if idx >= 0:
                self._profile_combo.setCurrentIndex(idx)

    def _browse_local(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Carpeta local")
        if path:
            self._local_path.setText(path)

    @staticmethod
    def _set_combo(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def get_job(self) -> SyncJob:
        cron = self._cron.text().strip() or None
        interval = None if cron else self._interval.value()
        data = {
            "name": self._name.text().strip(),
            "credential_id": self._profile_combo.currentData(),
            "bucket": self._bucket.text().strip(),
            "s3_prefix": self._prefix.text().strip(),
            "local_path": self._local_path.text().strip(),
            "direction": self._direction.currentData(),
            "conflict_policy": self._conflict.currentData(),
            "delete_policy": self._delete_policy.currentData(),
            "schedule_cron": cron,
            "schedule_interval_minutes": interval,
            "enabled": self._enabled.isChecked(),
        }
        if self._job_id:
            data["id"] = self._job_id
        return SyncJob.model_validate(data)
