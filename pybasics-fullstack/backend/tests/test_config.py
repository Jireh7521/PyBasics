import pytest
from pydantic import ValidationError

from app.config import Settings


def production_settings(**overrides):
    values = {
        "app_env": "production",
        "database_url": "postgresql://user:password@db.example.test:5432/pybasics",
        "secret_key": "a-unique-production-secret-that-is-at-least-32-chars",
        "cors_origins": "https://learn.example.test, https://admin.example.test/",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_development_defaults_are_convenient_and_not_wildcard():
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.database_url.startswith("sqlite:///")
    assert settings.cors_origin_list == [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


def test_production_accepts_explicit_safe_configuration():
    settings = production_settings()

    assert settings.is_production is True
    assert settings.cors_origin_list == [
        "https://learn.example.test",
        "https://admin.example.test",
    ]


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"secret_key": None}, "SECRET_KEY"),
        ({"secret_key": "short"}, "SECRET_KEY"),
        ({"secret_key": "dev-only-insecure-key-change-me"}, "SECRET_KEY"),
        ({"database_url": ""}, "DATABASE_URL"),
        ({"cors_origins": ""}, "CORS_ORIGINS"),
        ({"cors_origins": "*"}, "cannot contain '*'"),
        ({"cors_origins": "https://learn.example.test,*"}, "cannot contain '*'"),
    ],
)
def test_production_rejects_missing_or_unsafe_configuration(overrides, message):
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)


def test_production_rejects_implicit_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql://user:password@db.example.test:5432/pybasics",
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_implicit_database_url():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="a-unique-production-secret-that-is-at-least-32-chars",
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_implicit_cors_origins():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql://user:password@db.example.test:5432/pybasics",
            secret_key="a-unique-production-secret-that-is-at-least-32-chars",
        )


def test_invalid_environment_is_rejected():
    with pytest.raises(ValidationError, match="APP_ENV"):
        Settings(_env_file=None, app_env="prod")
