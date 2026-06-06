"""Preferencias de usuario persistentes."""

from __future__ import annotations

import json

from app_s3.config.paths import settings_file
from app_s3.domain.models import AppSettings


class SettingsService:
    def load(self) -> AppSettings:
        path = settings_file()
        if not path.exists():
            return AppSettings()
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings.model_validate(data)

    def save(self, settings: AppSettings) -> None:
        settings_file().write_text(
            settings.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_default_credential_id(self) -> str | None:
        return self.load().default_credential_id

    def set_default_credential_id(self, profile_id: str | None) -> None:
        settings = self.load()
        settings.default_credential_id = profile_id
        self.save(settings)

    def resolve_initial_profile_id(
        self,
        profile_ids: list[str],
    ) -> str | None:
        if not profile_ids:
            return None
        default_id = self.get_default_credential_id()
        if default_id and default_id in profile_ids:
            return default_id
        return profile_ids[0]

    def ensure_default_for_profiles(self, profile_ids: list[str]) -> str | None:
        """Mantiene una predeterminada válida; asigna la primera si falta."""
        if not profile_ids:
            self.set_default_credential_id(None)
            return None
        default_id = self.get_default_credential_id()
        if default_id and default_id in profile_ids:
            return default_id
        first_id = profile_ids[0]
        self.set_default_credential_id(first_id)
        return first_id

    def on_profile_deleted(
        self,
        profile_id: str,
        remaining_ids: list[str],
    ) -> None:
        if self.get_default_credential_id() != profile_id:
            return
        if remaining_ids:
            self.set_default_credential_id(remaining_ids[0])
        else:
            self.set_default_credential_id(None)

    def can_delete_profile(
        self,
        profile_id: str,
        profile_ids: list[str],
    ) -> tuple[bool, str]:
        if profile_id not in profile_ids:
            return False, "La cuenta seleccionada no existe."
        if len(profile_ids) <= 1:
            return True, ""
        default_id = self.get_default_credential_id()
        if default_id == profile_id:
            return (
                False,
                "No puedes eliminar la cuenta predeterminada. "
                "Elige otra cuenta como predeterminada primero.",
            )
        return True, ""
