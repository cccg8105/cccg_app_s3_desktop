"""Excepciones de dominio."""


class AppS3Error(Exception):
    """Error base de la aplicación."""


class CredentialError(AppS3Error):
    """Error relacionado con credenciales."""


class UnlockError(CredentialError):
    """Contraseña maestra incorrecta o datos corruptos."""


class S3OperationError(AppS3Error):
    """Error en operaciones S3."""


class SyncError(AppS3Error):
    """Error en sincronización."""
