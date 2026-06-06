"""Recursos estáticos de la interfaz (iconos, etc.)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from PySide6.QtGui import QIcon


def app_icon_path() -> Path:
    """Ruta al PNG del icono de la aplicación."""
    return Path(resources.files("app_s3")) / "assets" / "app_icon.png"


def get_app_icon() -> QIcon:
    """Icono principal de S3 Desktop."""
    return QIcon(str(app_icon_path()))
