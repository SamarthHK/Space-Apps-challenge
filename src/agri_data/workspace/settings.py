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
