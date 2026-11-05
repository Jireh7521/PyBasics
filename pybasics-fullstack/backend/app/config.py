from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEVELOPMENT_SECRET = "dev-only-insecure-key-change-me"
_LOCAL_CORS_ORIGINS = "http://127.0.0.1:8000,http://localhost:8000"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "production"
    database_url: str = "sqlite:///./pybasics_dev.db"
    secret_key: str = _DEVELOPMENT_SECRET
    access_token_expire_minutes: int = 720
    cors_origins: str = ""

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "test", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, or production.")
        return normalized

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_lifetime(cls, value: int) -> int:
        if value < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        configured = self.cors_origins.strip()
        if not configured:
            if self.environment == "production":
                return []
            configured = _LOCAL_CORS_ORIGINS

        return list(
            dict.fromkeys(
                origin.strip().rstrip("/")
                for origin in configured.split(",")
                if origin.strip()
            )
        )

    @model_validator(mode="after")
    def validate_runtime_configuration(self):
        if self.environment != "production":
            return self

        if (
            self.secret_key == _DEVELOPMENT_SECRET
            or len(self.secret_key.encode("utf-8")) < 32
        ):
            raise ValueError(
                "Production requires SECRET_KEY to be a unique random value "
                "containing at least 32 UTF-8 bytes."
            )

        if not self.database_url.startswith(
            ("postgresql://", "postgresql+psycopg2://")
        ):
            raise ValueError(
                "Production requires DATABASE_URL to point to PostgreSQL; "
                "the local SQLite default is not allowed."
            )

        origins = self.cors_origin_list
        if not origins:
            raise ValueError(
                "Production requires CORS_ORIGINS to list the frontend origin(s)."
            )
        if "*" in origins:
            raise ValueError(
                "Wildcard CORS origins are not allowed in this application."
            )

        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "Production CORS origins must be HTTPS origins without paths, "
                    "credentials, queries, or fragments."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
