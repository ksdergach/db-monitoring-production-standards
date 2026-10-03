import pytest
from cryptography.fernet import Fernet

from app import crypto
from app.app import create_app
from app.config import is_production, settings


@pytest.fixture(autouse=True)
def _reset_fernet():
    crypto.reset_for_tests()
    yield
    crypto.reset_for_tests()


@pytest.mark.parametrize(
    "secret_key",
    [
        "",
        "dev-secret",
        "change-me-to-something-random",
        "x" * 31,
    ],
)
def test_production_rejects_weak_secret_key(monkeypatch, secret_key):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())

    with pytest.raises(RuntimeError) as exc_info:
        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": secret_key,
            }
        )

    if secret_key:
        assert secret_key not in str(exc_info.value)


def test_production_accepts_32_character_secret(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())

    secret_key = "x" * 32

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": secret_key,
        }
    )

    assert app.config["SECRET_KEY"] == secret_key


def test_development_allows_dev_secret(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "dev-secret",
        }
    )

    assert app.config["SECRET_KEY"] == "dev-secret"


def test_production_requires_fernet_key(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("FERNET_KEY", raising=False)
    crypto.reset_for_tests()

    with pytest.raises(crypto.FernetKeyMissing):
        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "x" * 32,
            }
        )


def test_is_production_prefers_environment(monkeypatch):
    monkeypatch.setattr(settings, "FLASK_ENV", "production")
    monkeypatch.setenv("FLASK_ENV", "development")

    assert is_production() is False


def test_is_production_falls_back_to_settings(monkeypatch):
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setattr(settings, "FLASK_ENV", "production")

    assert is_production() is True
