import pytest
from pydantic import ValidationError

from app.config import Settings


def development_settings(**overrides):
    values = {
        "app_env": "development",
        "database_url": "sqlite:///./pybasics_dev.db",
        "access_token_expire_minutes": 720,
        "cors_origins": "http://localhost:8000,http://127.0.0.1:8000",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def production_settings(**overrides):
    values = {
        "app_env": "production",
        "database_url": "postgresql://user:password@db.example.test:5432/pybasics",
        "secret_key": "a-unique-production-secret-that-is-at-least-32-chars",
        "access_token_expire_minutes": 720,
        "cors_origins": "https://learn.example.test, https://admin.example.test/",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_development_configuration_is_not_wildcard():
    settings = development_settings()

    assert settings.app_env == "development"
    assert settings.code_execution_enabled is False
    assert settings.database_url.startswith("sqlite:///")
    assert settings.cors_origin_list == [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


def test_development_secret_is_generated_and_not_a_fixed_placeholder():
    first = development_settings()
    second = development_settings()

    assert len(first.secret_key) >= 32
    assert first.secret_key != second.secret_key
    assert first.secret_key.lower() not in {
        "change-me",
        "changeme",
        "secret",
        "secret-key",
    }


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
        ({"secret_key": ""}, "SECRET_KEY"),
        ({"secret_key": "short"}, "SECRET_KEY"),
        ({"database_url": ""}, "DATABASE_URL"),
        ({"database_url": "sqlite:///./pybasics_dev.db"}, "not SQLite"),
        ({"cors_origins": ""}, "CORS_ORIGINS"),
        ({"code_execution_enabled": True}, "CODE_EXECUTION_ENABLED"),
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
            access_token_expire_minutes=720,
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_implicit_database_url():
    with pytest.raises(ValidationError, match="database_url"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="a-unique-production-secret-that-is-at-least-32-chars",
            access_token_expire_minutes=720,
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_implicit_cors_origins():
    with pytest.raises(ValidationError, match="cors_origins"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql://user:password@db.example.test:5432/pybasics",
            access_token_expire_minutes=720,
            secret_key="a-unique-production-secret-that-is-at-least-32-chars",
        )


def test_invalid_environment_is_rejected():
    with pytest.raises(ValidationError, match="APP_ENV"):
        development_settings(app_env="prod")
