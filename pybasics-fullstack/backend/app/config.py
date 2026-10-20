import secrets
from functools import lru_cache

from pydantic import Field, model_validator
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
    app_env: str
    database_url: str
    # Never embed a fixed secret; local runs get an ephemeral key.
    # Set SECRET_KEY in the local .env file if sessions should survive restarts.
    secret_key: str = Field(default_factory=secrets.token_urlsafe)
    access_token_expire_minutes: int
    cors_origins: str

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
            if not self.database_url.strip():
                raise ValueError(
                    "DATABASE_URL must be explicitly configured when APP_ENV=production."
                )
            if self.database_url.strip().lower().startswith("sqlite"):
                raise ValueError(
                    "DATABASE_URL must use a production database, not SQLite, when APP_ENV=production."
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
