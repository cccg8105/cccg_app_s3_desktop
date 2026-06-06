"""Tests de CredentialStore."""


import pytest

from app_s3.domain.models import CredentialProfile
from app_s3.infrastructure.credential_store import CredentialStore


@pytest.fixture
def isolated_store(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(
        "app_s3.infrastructure.credential_store.credentials_file",
        lambda: data_dir / "credentials.enc",
    )
    monkeypatch.setattr(
        "app_s3.infrastructure.credential_store.salt_file",
        lambda: data_dir / ".salt",
    )
    monkeypatch.setattr(
        "app_s3.infrastructure.credential_store.verifier_file",
        lambda: data_dir / ".verifier",
    )
    return CredentialStore()


def test_setup_and_unlock(isolated_store):
    store = isolated_store
    store.setup("master-password-123")
    assert store.is_initialized()

    store.lock()
    profiles = store.unlock("master-password-123")
    assert profiles == []


def test_save_and_load_profiles(isolated_store):
    store = isolated_store
    store.setup("secret")
    profile = CredentialProfile(
        alias="test",
        access_key_id="AKIATEST",
        secret_access_key="secretkey",
        region="us-east-1",
    )
    store.save_profiles([profile])

    store.lock()
    loaded = store.unlock("secret")
    assert len(loaded) == 1
    assert loaded[0].alias == "test"
    assert loaded[0].access_key_id == "AKIATEST"


def test_wrong_password_raises(isolated_store):
    store = isolated_store
    store.setup("correct")
    store.lock()
    from app_s3.domain.exceptions import UnlockError

    with pytest.raises(UnlockError):
        store.unlock("wrong")
