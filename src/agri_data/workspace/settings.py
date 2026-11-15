from dataclasses import dataclass, field
import os
import re


@dataclass(frozen=True)
class WorkspaceSettings:
    dsn: str = field(repr=False)
    database: str
    user: str
    schema: str
    workspace_id: str

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        names = ("DATABASE_URL", "DATABASE_NAME", "DATABASE_USER", "SCHEMA", "ID")
        values = [environ.get("AGRI_WORKSPACE_" + name, "").strip() for name in names]
        if not any(values):
            return None
        if not all(values):
            raise ValueError("Supply all AGRI_WORKSPACE database, schema and ID settings together")
        dsn, database, user, schema, identifier = values
        if not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("Workspace storage requires PostgreSQL")
        if not re.fullmatch(r"agri_[a-z0-9_]{1,58}", schema):
            raise ValueError("Use an explicit agri_* workspace schema")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", identifier):
            raise ValueError("Workspace ID must be a stable 1-64 character identifier")
        return cls(dsn, database, user, schema, identifier)


@dataclass(frozen=True)
class AccountSettings:
    mode: str = "shared"
    cookie_secure: bool = False
    session_seconds: int = 43200
    bootstrap_seconds: int = 600
    login_attempt_limit: int = 12
    login_window_seconds: int = 900

    def __post_init__(self):
        if self.mode not in ("shared", "accounts"):
            raise ValueError("AGRI_AUTH_MODE must be shared or accounts")
        if not 60 <= self.session_seconds <= 604800:
            raise ValueError("Account sessions must expire within 60-604800 seconds")
        if not 1 <= self.login_attempt_limit <= 100:
            raise ValueError("Account login attempt limit must be between 1 and 100")

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        secure = environ.get("AGRI_AUTH_COOKIE_SECURE", "false")
        if secure not in ("true", "false"):
            raise ValueError("AGRI_AUTH_COOKIE_SECURE must be true or false")
        try:
            seconds = int(environ.get("AGRI_AUTH_SESSION_SECONDS", "43200"))
        except ValueError:
            raise ValueError("AGRI_AUTH_SESSION_SECONDS must be an integer") from None
        return cls(mode=environ.get("AGRI_AUTH_MODE", "shared"),
                   cookie_secure=secure == "true", session_seconds=seconds)
