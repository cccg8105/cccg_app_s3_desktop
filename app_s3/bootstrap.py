"""Arranque y wiring de dependencias."""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from app_s3.domain.exceptions import UnlockError
from app_s3.infrastructure.credential_store import CredentialStore
from app_s3.ui.dialogs.unlock_dialog import UnlockDialog
from app_s3.ui.main_window import MainWindow
from app_s3.ui.resources import get_app_icon
from app_s3.ui.theme import configure_application_theme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setApplicationName("S3 Desktop")
    app.setOrganizationName("app-s3")
    app.setWindowIcon(get_app_icon())
    configure_application_theme(app)
    return app


def run() -> int:
    logger.info("Logging to stderr (run from terminal to capture output)")
    app = create_app()
    store = CredentialStore()
    is_first_run = not store.is_initialized()

    unlock = UnlockDialog(is_first_run=is_first_run)
    if unlock.exec() != UnlockDialog.DialogCode.Accepted:
        return 0

    password = unlock.master_password
    try:
        if is_first_run:
            store.setup(password)
        else:
            store.unlock(password)
    except UnlockError as exc:
        QMessageBox.critical(None, "Error", str(exc))
        return 1

    window = MainWindow(store)
    window.show()
    return app.exec()
