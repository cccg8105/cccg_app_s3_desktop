"""Servicio de credenciales AWS."""

from __future__ import annotations

from app_s3.domain.exceptions import CredentialError
from app_s3.domain.models import CredentialProfile
from app_s3.infrastructure.credential_store import CredentialStore
from app_s3.infrastructure.s3_repository import S3Repository


class CredentialService:
    def __init__(self, store: CredentialStore) -> None:
        self._store = store

    @property
    def profiles(self) -> list[CredentialProfile]:
        return self._store.profiles

    def add_profile(self, profile: CredentialProfile) -> None:
        repo = S3Repository(profile)
        try:
            repo.validate_credentials()
        except Exception as exc:
            raise CredentialError(f"Credenciales inválidas: {exc}") from exc

        profiles = self._store.profiles
        profiles.append(profile)
        self._store.save_profiles(profiles)

    def update_profile(self, profile: CredentialProfile) -> None:
        repo = S3Repository(profile)
        try:
            repo.validate_credentials()
        except Exception as exc:
            raise CredentialError(f"Credenciales inválidas: {exc}") from exc

        profiles = [
            profile if p.id == profile.id else p for p in self._store.profiles
        ]
        self._store.save_profiles(profiles)

    def delete_profile(self, profile_id: str) -> None:
        profiles = [p for p in self._store.profiles if p.id != profile_id]
        if len(profiles) == len(self._store.profiles):
            raise CredentialError("La cuenta no existe.")
        self._store.save_profiles(profiles)

    def get_profile(self, profile_id: str) -> CredentialProfile | None:
        for profile in self._store.profiles:
            if profile.id == profile_id:
                return profile
        return None

    def create_repository(
        self, profile_id: str
    ) -> S3Repository | None:
        profile = self.get_profile(profile_id)
        if profile is None:
            return None
        return S3Repository(profile)
