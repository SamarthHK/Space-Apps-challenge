"""Explicit service configuration without scientific or database fallbacks."""

from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGRI_", env_file=".env", extra="ignore"
    )

    environment: str = "development"
    database_url: SecretStr | None = None
    database_schema: str = Field(default="agri_app", pattern=r"^[a-z][a-z0-9_]{0,62}$")
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:1080",
            "http://127.0.0.1:1080",
        ]
    )
    cookie_secure: bool = False
    session_seconds: int = Field(default=43200, ge=300, le=604800)
    csrf_seconds: int = Field(default=600, ge=60, le=3600)
    max_request_bytes: int = Field(default=1048576, ge=1024, le=104857600)
    login_attempt_limit: int = Field(default=5, ge=1, le=100)
    login_window_seconds: int = Field(default=300, ge=60, le=3600)

    @field_validator("environment")
    @classmethod
    def environment_known(cls, value: str) -> str:
        if value not in {"development", "test", "production"}:
            raise ValueError("Unknown service environment")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            try:
                url = make_url(value.get_secret_value())
            except Exception:
                raise ValueError("Invalid PostgreSQL URL") from None
            if url.drivername != "postgresql+psycopg" or not url.database:
                raise ValueError("Use an explicit postgresql+psycopg database URL")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def exact_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                parsed.port
            except ValueError:
                raise ValueError("Invalid browser origin") from None
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in origin
                or parsed.hostname in {"0.0.0.0", "::"}
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Use an exact browser origin, not a bind address")
        return origins

    @model_validator(mode="after")
    def secure_production(self):
        if self.environment == "production":
            if not self.cookie_secure or not self.database_url:
                raise ValueError("Production requires secure cookies and PostgreSQL")
            if not self.allowed_origins or any(
                not origin.startswith("https://") for origin in self.allowed_origins
            ):
                raise ValueError("Production requires explicit HTTPS origins")
        return self
