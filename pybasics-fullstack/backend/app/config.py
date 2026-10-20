import secrets
from functools import lru_cache
from urllib.parse import urlsplit

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


def _validate_production_secret(secret: str) -> bool:
    """Reject weak-looking secrets; length alone is not a strength guarantee."""
    normalized = secret.strip().lower()
    if len(secret.strip()) < 32 or normalized in _INSECURE_SECRETS:
        return False

    # Generated secrets (for example secrets.token_hex(32)) have many distinct
    # characters. This inexpensive guard rejects long repeated/patterned values.
    if len(set(normalized)) < 12:
        return False

    # Reject short patterns repeated to fill the secret. Random secrets can
    # contain repeats, but are extremely unlikely to consist entirely of one.
    for width in range(1, min(8, len(normalized) // 2) + 1):
        pattern = normalized[:width]
        if len(normalized) % width == 0 and pattern * (len(normalized) // width) == normalized:
            return False

    return True


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
            if not _validate_production_secret(self.secret_key):
                raise ValueError(
                    "SECRET_KEY is unsafe for production; provide a unique random "
                    "secret of at least 32 characters with sufficient character diversity."
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
            for origin in origins:
                parsed = urlsplit(origin)
                try:
                    valid_port = parsed.port is None or 1 <= parsed.port <= 65535
                except ValueError:
                    valid_port = False
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                    or not valid_port
                ):
                    raise ValueError(
                        "Each production CORS origin must be an HTTPS origin "
                        "containing only a scheme, host, and optional valid port."
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
