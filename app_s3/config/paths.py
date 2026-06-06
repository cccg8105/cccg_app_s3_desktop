"""Rutas de datos de usuario en Windows."""

from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "S3Desktop"
APP_AUTHOR = "app-s3"


def get_data_dir() -> Path:
    """Directorio base de datos de usuario (%APPDATA%/S3Desktop)."""
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def credentials_file() -> Path:
    return get_data_dir() / "credentials.enc"


def salt_file() -> Path:
    return get_data_dir() / ".salt"


def verifier_file() -> Path:
    return get_data_dir() / ".verifier"


def bookmarks_file() -> Path:
    return get_data_dir() / "bookmarks.json"


def sync_jobs_file() -> Path:
    return get_data_dir() / "sync_jobs.json"


def settings_file() -> Path:
    return get_data_dir() / "settings.json"


def logs_dir() -> Path:
    path = get_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
