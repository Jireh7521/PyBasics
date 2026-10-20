from functools import lru_cache
import secrets

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_INSECURE_SECRETS = {
    "",
    "change-me",
    "changeme",
    "secret",
    "secret-key",
    "change-this-to-a-long-random-string",
}


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./pybasics_dev.db"
    # Convenient for local development only; production validation rejects it.
    # Generate an ephemeral development key instead of embedding a fixed secret.
    # Set SECRET_KEY in the local .env file if sessions should survive restarts.
    secret_key: str = secrets.token_urlsafe(32)
    access_token_expire_minutes: int = 720
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_environment(self):
        environment = self.app_env.strip().lower()
        if environment not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production.")

        if environment == "production":
            if "secret_key" not in self.model_fields_set:
                raise ValueError(
                    "SECRET_KEY must be explicitly configured when APP_ENV=production."
                )
            secret = self.secret_key.strip()
            if len(secret) < 32 or secret.lower() in _INSECURE_SECRETS:
                raise ValueError(
                    "SECRET_KEY is unsafe for production; provide a unique random secret "
                    "of at least 32 characters."
                )
            if "database_url" not in self.model_fields_set or not self.database_url.strip():
                raise ValueError(
                    "DATABASE_URL must be explicitly configured when APP_ENV=production."
                )
            if self.database_url.strip().lower().startswith("sqlite"):
                raise ValueError(
                    "DATABASE_URL must use a production database, not SQLite, when APP_ENV=production."
                )
            if "cors_origins" not in self.model_fields_set:
                raise ValueError(
                    "CORS_ORIGINS must be explicitly configured when APP_ENV=production."
                )
            origins = self._parse_origins(self.cors_origins)
            if not origins:
                raise ValueError(
                    "CORS_ORIGINS must contain at least one explicit frontend origin in production."
                )
            if "*" in origins:
                raise ValueError(
                    "CORS_ORIGINS cannot contain '*' when APP_ENV=production."
                )

        return self

    @staticmethod
    def _parse_origins(value: str) -> list[str]:
        return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = self._parse_origins(self.cors_origins)
        if "*" in origins and self.is_production:
            # Defensive guard in case settings validation is bypassed in future.
            raise ValueError("Wildcard CORS origins are not allowed in production.")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
