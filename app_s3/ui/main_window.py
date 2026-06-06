"""Ventana principal de la aplicación."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app_s3.application.bucket_service import BookmarkService
from app_s3.application.credential_service import CredentialService
from app_s3.application.settings_service import SettingsService
from app_s3.application.transfer_service import TransferService
from app_s3.domain.exceptions import CredentialError, S3OperationError
from app_s3.domain.models import BucketBookmark
from app_s3.infrastructure.credential_store import CredentialStore
from app_s3.ui.dialogs.add_bucket_dialog import AddBucketDialog
from app_s3.ui.dialogs.credential_dialog import CredentialDialog
from app_s3.ui.widgets.connection_sidebar import ConnectionSidebar
from app_s3.ui.widgets.s3_browser_widget import S3BrowserWidget
from app_s3.ui.widgets.transfer_panel import TransferPanel
from app_s3.ui.workers.transfer_worker import TransferWorkerPool

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        credential_store: CredentialStore,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("S3 Desktop")
        self.resize(1100, 700)

        self._credential_store = credential_store
        self._credential_service = CredentialService(credential_store)
        self._settings_service = SettingsService()
        self._bookmark_service = BookmarkService()
        self._transfer_service = TransferService()
        self._worker_pool = TransferWorkerPool()
        self._current_profile_id: str | None = None
        self._current_repo = None

        self._build_ui()
        self._refresh_profiles()

    def closeEvent(self, event) -> None:
        self._credential_store.lock()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self._sidebar = ConnectionSidebar()
        self._sidebar.profile_selected.connect(self._on_profile_selected)
        self._sidebar.bucket_selected.connect(self._on_bucket_selected)
        self._sidebar.add_credential_requested.connect(self._add_credential)
        self._sidebar.edit_credential_requested.connect(self._edit_credential)
        self._sidebar.set_default_credential_requested.connect(
            self._set_default_credential
        )
        self._sidebar.delete_credential_requested.connect(self._delete_credential)
        self._sidebar.add_bucket_requested.connect(self._add_bucket)
        self._sidebar.lock_requested.connect(self._lock_app)
        splitter.addWidget(self._sidebar)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        content_panel = QWidget()
        main_layout = QVBoxLayout(content_panel)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        self._s3_browser = S3BrowserWidget()
        self._s3_browser.files_dropped.connect(self._on_files_dropped)
        self._s3_browser.download_requested.connect(self._on_download)
        self._s3_browser.download_many_requested.connect(self._on_download_many)
        self._s3_browser.delete_requested.connect(self._on_delete)
        self._s3_browser.create_folder_requested.connect(self._on_create_folder)
        self._s3_browser.rename_requested.connect(self._on_rename)
        main_layout.addWidget(self._s3_browser, stretch=3)

        self._transfer_panel = TransferPanel()
        main_layout.addWidget(self._transfer_panel, stretch=1)

        right_layout.addWidget(content_panel, stretch=1)

        self._status_bar = QStatusBar()
        right_layout.addWidget(self._status_bar)

        splitter.addWidget(right_column)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 800])
        splitter.setChildrenCollapsible(False)
        self._sidebar.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )

    def _refresh_profiles(self) -> None:
        profiles = self._credential_service.profiles
        profile_ids = [profile.id for profile in profiles]
        default_id = self._settings_service.ensure_default_for_profiles(
            profile_ids
        )

        active_id = self._current_profile_id
        if profiles and active_id not in profile_ids:
            active_id = self._settings_service.resolve_initial_profile_id(
                profile_ids
            )
        elif profiles and not active_id:
            active_id = self._settings_service.resolve_initial_profile_id(
                profile_ids
            )

        self._sidebar.set_profiles(profiles, active_id, default_id)
        if active_id:
            self._load_profile(active_id)
        else:
            self._current_profile_id = None
            self._current_repo = None
            self._sidebar.clear_buckets()
            self._s3_browser.set_repository(None)
            self._s3_browser.navigate_to("", "")

    def _on_profile_selected(self, profile_id: str) -> None:
        self._load_profile(profile_id)

    def _load_profile(
        self,
        profile_id: str,
        active_bucket: str | None = None,
    ) -> None:
        self._current_profile_id = profile_id
        self._current_repo = self._credential_service.create_repository(profile_id)
        self._s3_browser.set_repository(self._current_repo)

        bookmarks = self._bookmark_service.get_for_profile(profile_id)
        bucket_names = [b.bucket_name for b in bookmarks]
        if active_bucket and active_bucket in bucket_names:
            selected_bucket = active_bucket
        else:
            current = self._sidebar.current_bucket_name()
            if current in bucket_names:
                selected_bucket = current
            else:
                selected_bucket = bucket_names[0] if bucket_names else None
        self._sidebar.set_buckets(bucket_names, selected_bucket)

        if selected_bucket and self._current_repo:
            self._s3_browser.navigate_to(selected_bucket, "")
        else:
            self._s3_browser.navigate_to("", "")

        alias = self._sidebar.current_profile_alias().removeprefix("★ ").strip()
        if alias:
            self._status_bar.showMessage(f"Cuenta activa: {alias}", 3000)

    def _on_bucket_selected(self, bucket_name: str) -> None:
        if bucket_name and self._current_repo:
            self._s3_browser.navigate_to(bucket_name, "")

    def _refresh_browser(self) -> None:
        bucket = self._sidebar.current_bucket_name()
        if bucket and self._current_repo:
            prefix = self._s3_browser.prefix
            self._s3_browser.navigate_to(bucket, prefix)

    def _add_credential(self) -> None:
        dialog = CredentialDialog(parent=self)
        if dialog.exec() != CredentialDialog.DialogCode.Accepted:
            return
        try:
            self._credential_service.add_profile(dialog.get_profile())
            new_profile = self._credential_service.profiles[-1]
            if len(self._credential_service.profiles) == 1:
                self._settings_service.set_default_credential_id(new_profile.id)
            self._refresh_profiles()
        except CredentialError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _set_default_credential(self) -> None:
        profile_id = self._sidebar.current_profile_id()
        if not profile_id:
            QMessageBox.information(self, "Info", "Selecciona una cuenta.")
            return
        self._settings_service.set_default_credential_id(profile_id)
        self._refresh_profiles()
        alias = self._sidebar.current_profile_alias().lstrip("★ ").strip()
        self._status_bar.showMessage(f"Cuenta predeterminada: {alias}", 3000)

    def _delete_credential(self) -> None:
        profile_id = self._sidebar.current_profile_id()
        if not profile_id:
            QMessageBox.information(self, "Info", "Selecciona una cuenta.")
            return

        profiles = self._credential_service.profiles
        profile_ids = [profile.id for profile in profiles]
        can_delete, message = self._settings_service.can_delete_profile(
            profile_id,
            profile_ids,
        )
        if not can_delete:
            QMessageBox.warning(self, "No se puede eliminar", message)
            return

        profile = self._credential_service.get_profile(profile_id)
        if not profile:
            return
        alias = profile.alias
        if not CredentialDialog.confirm_delete(self, alias):
            return

        try:
            self._credential_service.delete_profile(profile_id)
        except CredentialError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        remaining_ids = [
            profile.id
            for profile in self._credential_service.profiles
        ]
        self._settings_service.on_profile_deleted(profile_id, remaining_ids)
        if profile_id == self._current_profile_id:
            self._current_profile_id = None
        self._refresh_profiles()

    def _edit_credential(self) -> None:
        profile_id = self._sidebar.current_profile_id()
        if not profile_id:
            QMessageBox.information(self, "Info", "Selecciona una cuenta.")
            return
        profile = self._credential_service.get_profile(profile_id)
        if not profile:
            return
        dialog = CredentialDialog(profile, parent=self)
        if dialog.exec() != CredentialDialog.DialogCode.Accepted:
            return
        try:
            self._credential_service.update_profile(dialog.get_profile())
            self._refresh_profiles()
        except CredentialError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _add_bucket(self) -> None:
        if not self._current_repo or not self._current_profile_id:
            QMessageBox.information(self, "Info", "Selecciona una cuenta primero.")
            return

        dialog = AddBucketDialog(parent=self)
        if dialog.exec() != AddBucketDialog.DialogCode.Accepted:
            return
        name = dialog.bucket_name
        self._bookmark_service.add(
            BucketBookmark(
                credential_id=self._current_profile_id,
                bucket_name=name,
            )
        )
        self._load_profile(self._current_profile_id, active_bucket=name)

    def _on_files_dropped(self, local_paths: list, prefix: str) -> None:
        if not self._current_repo:
            return
        bucket = self._s3_browser.bucket
        if not bucket:
            return
        for path in local_paths:
            p = Path(path)
            if p.is_file():
                task = self._transfer_service.enqueue_upload(
                    str(p), bucket, prefix
                )
                self._transfer_panel.add_task(task)
                self._worker_pool.submit(
                    task,
                    self._current_repo,
                    self._transfer_service,
                    self._transfer_panel.update_task,
                    self._on_transfer_finished,
                )

    def _on_download(self, key: str) -> None:
        if not self._current_repo:
            return
        bucket = self._s3_browser.bucket
        filename = key.rstrip("/").split("/")[-1]
        save_path, ok = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo",
            filename,
        )
        if not ok or not save_path:
            return
        task = self._transfer_service.enqueue_download(
            bucket,
            key,
            str(Path(save_path).parent),
            local_path=save_path,
        )
        self._transfer_panel.add_task(task)
        self._worker_pool.submit(
            task,
            self._current_repo,
            self._transfer_service,
            self._transfer_panel.update_task,
            self._on_transfer_finished,
        )

    def _on_download_many(self, keys: list[str]) -> None:
        if not self._current_repo or not keys:
            return
        bucket = self._s3_browser.bucket
        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Carpeta destino para descarga",
        )
        if not dest_dir:
            return
        for key in keys:
            filename = key.rstrip("/").split("/")[-1]
            save_path = str(Path(dest_dir) / filename)
            task = self._transfer_service.enqueue_download(
                bucket,
                key,
                dest_dir,
                local_path=save_path,
            )
            self._transfer_panel.add_task(task)
            self._worker_pool.submit(
                task,
                self._current_repo,
                self._transfer_service,
                self._transfer_panel.update_task,
                self._on_transfer_finished,
            )

    def _on_delete(self, key: str) -> None:
        if not self._current_repo:
            return
        bucket = self._s3_browser.bucket
        reply = QMessageBox.question(
            self,
            "Eliminar",
            f"¿Eliminar '{key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._current_repo.delete_object(bucket, key)
            self._refresh_browser()
        except S3OperationError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_create_folder(self) -> None:
        if not self._current_repo:
            return
        bucket = self._s3_browser.bucket
        prefix = self._s3_browser.prefix
        name, ok = QInputDialog.getText(self, "Nueva carpeta", "Nombre:")
        if not ok or not name:
            return
        folder_prefix = prefix + name if prefix else name
        try:
            self._current_repo.create_folder(bucket, folder_prefix)
            self._refresh_browser()
        except S3OperationError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_rename(self, old_key: str, new_key: str) -> None:
        if not self._current_repo:
            return
        bucket = self._s3_browser.bucket
        try:
            self._current_repo.rename_object(bucket, old_key, new_key)
            self._refresh_browser()
        except S3OperationError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_transfer_finished(self, task) -> None:
        self._transfer_panel.update_task(task)
        self._refresh_browser()

    def _lock_app(self) -> None:
        self._credential_store.lock()
        self.close()
