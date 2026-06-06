"""Almacenamiento cifrado de credenciales AWS."""

from __future__ import annotations

import base64
import hashlib
import json
import os

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app_s3.config.paths import credentials_file, salt_file, verifier_file
from app_s3.domain.exceptions import UnlockError
from app_s3.domain.models import CredentialProfile


class CredentialStore:
    """Persiste perfiles AWS cifrados con Fernet + Argon2id."""

    _SALT_BYTES = 16
    _PBKDF2_ITERATIONS = 600_000
    _PH = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)

    def __init__(self) -> None:
        self._fernet: Fernet | None = None
        self._profiles: list[CredentialProfile] = []

    @property
    def profiles(self) -> list[CredentialProfile]:
        return list(self._profiles)

    def is_initialized(self) -> bool:
        return (
            credentials_file().exists()
            and salt_file().exists()
            and verifier_file().exists()
        )

    def setup(self, master_password: str) -> None:
        """Primera configuración: crea salt y archivo vacío cifrado."""
        salt = os.urandom(self._SALT_BYTES)
        salt_file().write_bytes(salt)
        verifier_file().write_text(
            self._PH.hash(master_password),
            encoding="utf-8",
        )
        self._fernet = Fernet(self._derive_key(master_password, salt))
        self._profiles = []
        self._persist()

    def unlock(self, master_password: str) -> list[CredentialProfile]:
        if not self.is_initialized():
            raise UnlockError("No hay credenciales configuradas.")

        salt = salt_file().read_bytes()
        verifier = verifier_file().read_text(encoding="utf-8")
        try:
            self._PH.verify(verifier, master_password)
        except VerifyMismatchError as exc:
            raise UnlockError("Contraseña incorrecta.") from exc

        self._fernet = Fernet(self._derive_key(master_password, salt))

        encrypted = credentials_file().read_bytes()
        if not encrypted:
            self._profiles = []
            return self.profiles

        try:
            plaintext = self._fernet.decrypt(encrypted)
        except InvalidToken as exc:
            raise UnlockError("Contraseña incorrecta.") from exc

        data = json.loads(plaintext.decode("utf-8"))
        self._profiles = [CredentialProfile.model_validate(item) for item in data]
        return self.profiles

    def lock(self) -> None:
        self._fernet = None
        self._profiles = []

    def save_profiles(self, profiles: list[CredentialProfile]) -> None:
        if self._fernet is None:
            raise UnlockError("Almacén bloqueado.")
        self._profiles = list(profiles)
        self._persist()

    def _persist(self) -> None:
        if self._fernet is None:
            raise UnlockError("Almacén bloqueado.")
        payload = json.dumps(
            [p.model_dump() for p in self._profiles],
            ensure_ascii=False,
        ).encode("utf-8")
        credentials_file().write_bytes(self._fernet.encrypt(payload))

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        key_material = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self._PBKDF2_ITERATIONS,
            dklen=32,
        )
        return base64.urlsafe_b64encode(key_material)
