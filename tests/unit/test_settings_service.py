"""Tests de SettingsService."""

import json

import pytest

from app_s3.application.settings_service import SettingsService


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        "app_s3.application.settings_service.settings_file",
        lambda: path,
    )
    return SettingsService(), path


def test_default_credential_persistence(isolated_settings):
    service, path = isolated_settings
    service.set_default_credential_id("profile-1")
    assert service.get_default_credential_id() == "profile-1"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["default_credential_id"] == "profile-1"


def test_resolve_initial_profile_id(isolated_settings):
    service, _ = isolated_settings
    service.set_default_credential_id("b")
    assert service.resolve_initial_profile_id(["a", "b", "c"]) == "b"
    assert service.resolve_initial_profile_id(["a", "c"]) == "a"


def test_cannot_delete_default_with_multiple_profiles(isolated_settings):
    service, _ = isolated_settings
    service.set_default_credential_id("default")
    can_delete, message = service.can_delete_profile(
        "default",
        ["default", "other"],
    )
    assert can_delete is False
    assert "predeterminada" in message.lower()


def test_can_delete_only_profile(isolated_settings):
    service, _ = isolated_settings
    service.set_default_credential_id("only")
    can_delete, _ = service.can_delete_profile("only", ["only"])
    assert can_delete is True
