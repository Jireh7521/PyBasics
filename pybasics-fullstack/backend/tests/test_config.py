import pytest
from pydantic import ValidationError

from app.config import Settings


def test_missing_environment_fails_closed(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(ValidationError, match="Production requires SECRET_KEY"):
        Settings(_env_file=None)


def test_development_configuration_has_local_defaults():
    settings = Settings(_env_file=None, environment="development")

    assert settings.environment == "development"
    assert settings.database_url.startswith("sqlite:///")
    assert settings.cors_origin_list == [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]


def test_production_rejects_the_development_secret():
    with pytest.raises(ValidationError, match="Production requires SECRET_KEY"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://user:password@db.example.test/pybasics",
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_a_weak_secret():
    with pytest.raises(ValidationError, match="at least 32 UTF-8 bytes"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://user:password@db.example.test/pybasics",
            secret_key="too-short",
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_a_repetitive_low_entropy_secret():
    with pytest.raises(ValidationError, match="at least 32 UTF-8 bytes"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://user:password@db.example.test/pybasics",
            secret_key="a" * 64,
            cors_origins="https://learn.example.test",
        )


def test_production_rejects_the_sqlite_development_database():
    with pytest.raises(ValidationError, match="requires DATABASE_URL"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="strong-test-secret-value-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            cors_origins="https://learn.example.test",
        )


def test_production_requires_explicit_cors_origins():
    with pytest.raises(ValidationError, match="requires CORS_ORIGINS"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://user:password@db.example.test/pybasics",
            secret_key="strong-test-secret-value-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="Wildcard CORS"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://user:password@db.example.test/pybasics",
            secret_key="strong-test-secret-value-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            cors_origins="*",
        )


def test_production_accepts_strong_secret_database_and_https_origins():
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql://user:password@db.example.test/pybasics",
        secret_key="a-unique-random-production-secret-with-more-than-32-bytes",
        cors_origins="https://learn.example.test,https://admin.example.test",
    )

    assert settings.environment == "production"
    assert settings.cors_origin_list == [
        "https://learn.example.test",
        "https://admin.example.test",
    ]


def test_cors_parser_trims_values_and_removes_duplicates():
    settings = Settings(
        _env_file=None,
        cors_origins=" http://localhost:8000, http://localhost:8000/ ",
    )

    assert settings.cors_origin_list == ["http://localhost:8000"]
