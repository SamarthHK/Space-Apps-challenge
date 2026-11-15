"""Private scopes and revocable sessions, using the authenticated donor's patterns."""

from dataclasses import replace
from hashlib import sha256
import hmac
import re
import secrets
from threading import BoundedSemaphore
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from psycopg import sql
from psycopg.types.json import Jsonb

from .errors import WorkspaceError, WorkspaceUnavailable
from .fields import FieldStore
from .store import WorkspaceStore


PASSWORDS = PasswordHasher()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
HASH_SLOTS = BoundedSemaphore(4)


def digest(value):
    return sha256(value.encode()).hexdigest()


def valid_token(token):
    return isinstance(token, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is not None


def csrf_token(token):
    return hmac.new(token.encode(), b"agri-private-workspace-csrf-v1", "sha256").hexdigest()


def require_csrf(token, supplied):
    if not valid_token(token) or not supplied or not hmac.compare_digest(
        csrf_token(token).encode(), supplied.encode("utf-8")
    ):
        raise WorkspaceError(403, "csrf_invalid", "CSRF verification failed")


class AccountStore:
    def __init__(self, workspace, data_settings, settings):
        self.workspace = workspace
        self.data_settings = data_settings
        self.settings = settings
        self.fields = FieldStore(workspace, data_settings)
        if settings.mode == "accounts" and not self.fields.configured():
            raise ValueError("Private accounts require separate workspace/canonical schemas in the same database")

    @property
    def deployment_id(self):
        return self.workspace.settings.workspace_id

    @property
    def cookie_suffix(self):
        return digest(f"{self.workspace.settings.schema}:{self.deployment_id}:{self.data_settings.schema}")[:16]

    @property
    def session_cookie(self):
        return "agri_session_" + self.cookie_suffix

    @property
    def bootstrap_cookie(self):
        return "agri_csrf_" + self.cookie_suffix

    def require_enabled(self):
        if self.settings.mode != "accounts":
            raise WorkspaceError(404, "not_found", "Accounts are not enabled for this workspace")

    def ready(self):
        if not self.fields.ready():
            return False
        try:
            with self.workspace.session() as connection:
                for table in ("workspace_accounts", "workspace_sessions", "workspace_auth_limits"):
                    connection.execute(sql.SQL("SELECT 1 FROM {} LIMIT 0").format(sql.Identifier(table)))
                return connection.execute(
                    "SELECT has_table_privilege(current_user,%s,'INSERT') AS allowed",
                    (self.data_settings.schema + ".projects",),
                ).fetchone()["allowed"]
        except WorkspaceUnavailable:
            return False

    def scoped_settings(self, account):
        if (account["deployment_id"] != self.deployment_id
                or account["canonical_schema"] != self.data_settings.schema):
            raise WorkspaceUnavailable("Account ownership configuration does not match this deployment")
        return (
            replace(self.workspace.settings, workspace_id=account["workspace_id"]),
            replace(self.data_settings, project_ids=(account["project_id"],)),
        )

    def scoped_fields(self, account):
        workspace_settings, data_settings = self.scoped_settings(account)
        return FieldStore(WorkspaceStore(workspace_settings), data_settings)

    def consume_limit(self, bucket, limit, seconds):
        with self.workspace.session() as connection:
            row = connection.execute(
                "INSERT INTO workspace_auth_limits(deployment_id,bucket_hash,attempts) VALUES (%s,%s,1) "
                "ON CONFLICT(deployment_id,bucket_hash) DO UPDATE SET "
                "attempts=CASE WHEN workspace_auth_limits.window_started_at <= "
                "clock_timestamp() - %s * interval '1 second' THEN 1 "
                "ELSE least(workspace_auth_limits.attempts+1,%s) END,"
                "window_started_at=CASE WHEN workspace_auth_limits.window_started_at <= "
                "clock_timestamp() - %s * interval '1 second' THEN clock_timestamp() "
                "ELSE workspace_auth_limits.window_started_at END RETURNING attempts",
                (self.deployment_id, digest(bucket), seconds, limit + 1, seconds),
            ).fetchone()
        if row["attempts"] > limit:
            raise WorkspaceError(429, "rate_limited", "Too many authentication attempts; try again later",
                                 headers={"Retry-After": str(seconds)})

    def new_session(self, connection, user_id, seconds):
        token = secrets.token_urlsafe(32)
        row = connection.execute(
            "INSERT INTO workspace_sessions(token_hash,deployment_id,user_id,expires_at) "
            "VALUES (%s,%s,%s,clock_timestamp() + %s * interval '1 second') RETURNING expires_at",
            (digest(token), self.deployment_id, user_id, seconds),
        ).fetchone()
        return token, row["expires_at"]

    def bootstrap(self, peer, previous=None):
        self.consume_limit("bootstrap:" + peer, 120, self.settings.bootstrap_seconds)
        with self.workspace.session() as connection:
            connection.execute(
                "DELETE FROM workspace_sessions WHERE deployment_id=%s AND "
                "(expires_at<=clock_timestamp() OR (token_hash=%s AND user_id IS NULL))",
                (self.deployment_id, digest(previous) if valid_token(previous) else ""),
            )
            return self.new_session(connection, None, self.settings.bootstrap_seconds)

    def require_bootstrap(self, connection, token):
        row = connection.execute(
            "SELECT token_hash FROM workspace_sessions WHERE token_hash=%s AND deployment_id=%s "
            "AND user_id IS NULL AND revoked_at IS NULL AND expires_at>clock_timestamp() FOR UPDATE",
            (digest(token), self.deployment_id),
        ).fetchone()
        if row is None:
            raise WorkspaceError(403, "csrf_expired", "Request a new sign-in context")

    def session(self, token, *, required=True):
        row = None
        if valid_token(token):
            with self.workspace.session() as connection:
                row = connection.execute(
                    "SELECT a.user_id,a.login,a.deployment_id,a.workspace_id,a.canonical_schema,a.project_id,"
                    "s.expires_at FROM workspace_sessions s JOIN workspace_accounts a "
                    "ON a.user_id=s.user_id AND a.deployment_id=s.deployment_id "
                    "WHERE s.token_hash=%s AND s.deployment_id=%s AND a.canonical_schema=%s "
                    "AND a.active AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()",
                    (digest(token), self.deployment_id, self.data_settings.schema),
                ).fetchone()
        if row is None and required:
            raise WorkspaceError(401, "unauthenticated", "Sign in to access your private workspace")
        return row

    def output(self, account, token):
        return {
            "mode": "accounts", "user": {"id": account["user_id"], "login": account["login"]},
            "expires_at": account["expires_at"], "csrf_token": csrf_token(token),
        }

    def rotate(self, connection, account, bootstrap, previous):
        connection.execute(
            "DELETE FROM workspace_sessions WHERE token_hash=%s AND deployment_id=%s",
            (digest(bootstrap), self.deployment_id),
        )
        if valid_token(previous):
            connection.execute(
                "UPDATE workspace_sessions SET revoked_at=clock_timestamp() "
                "WHERE token_hash=%s AND deployment_id=%s AND user_id IS NOT NULL",
                (digest(previous), self.deployment_id),
            )
        token, expires = self.new_session(connection, account["user_id"], self.settings.session_seconds)
        return token, self.output({**account, "expires_at": expires}, token)

    def register(self, login, password, bootstrap, supplied_csrf, peer, previous, request_id):
        require_csrf(bootstrap, supplied_csrf)
        self.consume_limit("registration:" + peer, 10, 3600)
        with self.workspace.session() as connection:
            self.require_bootstrap(connection, bootstrap)
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                               (self.deployment_id + ":registration:" + login,))
            if connection.execute(
                "SELECT 1 FROM workspace_accounts WHERE deployment_id=%s AND login=%s",
                (self.deployment_id, login),
            ).fetchone():
                raise WorkspaceError(409, "login_exists", "That login is already registered")
            with HASH_SLOTS:
                password_hash = PASSWORDS.hash(password)
            identifier = uuid4().hex
            account = {"user_id": identifier, "login": login, "deployment_id": self.deployment_id,
                       "workspace_id": "account_" + identifier,
                       "canonical_schema": self.data_settings.schema, "project_id": "private_" + identifier}
            connection.execute(
                "INSERT INTO workspace_profiles(workspace_id) VALUES (%s)", (account["workspace_id"],))
            self.scoped_fields(account).workspace._revision(connection, request_id)
            connection.execute(sql.SQL(
                "INSERT INTO {}(project_id,name,metadata) VALUES (%s,%s,%s)"
            ).format(self.fields.table("projects")),
                (account["project_id"], "Private agricultural workspace", Jsonb({"access_mode": "private_account"})))
            connection.execute(
                "INSERT INTO workspace_accounts(user_id,deployment_id,login,password_hash,workspace_id,"
                "canonical_schema,project_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (identifier, self.deployment_id, login, password_hash, account["workspace_id"],
                 account["canonical_schema"], account["project_id"]),
            )
            return self.rotate(connection, account, bootstrap, previous)

    def login(self, login, password, bootstrap, supplied_csrf, peer, previous):
        require_csrf(bootstrap, supplied_csrf)
        self.consume_limit("login-peer:" + peer, self.settings.login_attempt_limit * 3,
                           self.settings.login_window_seconds)
        self.consume_limit("login-account:" + login, self.settings.login_attempt_limit,
                           self.settings.login_window_seconds)
        with self.workspace.session() as connection:
            self.require_bootstrap(connection, bootstrap)
            account = connection.execute(
                "SELECT * FROM workspace_accounts WHERE deployment_id=%s AND login=%s "
                "AND canonical_schema=%s FOR UPDATE",
                (self.deployment_id, login, self.data_settings.schema),
            ).fetchone()
            with HASH_SLOTS:
                try:
                    verified = PASSWORDS.verify(account["password_hash"] if account else DUMMY_HASH, password)
                except (InvalidHashError, VerificationError):
                    verified = False
                if not verified or not account or not account["active"]:
                    raise WorkspaceError(401, "invalid_credentials", "Login or password is incorrect")
                if PASSWORDS.check_needs_rehash(account["password_hash"]):
                    connection.execute(
                        "UPDATE workspace_accounts SET password_hash=%s WHERE user_id=%s",
                        (PASSWORDS.hash(password), account["user_id"]),
                    )
            return self.rotate(connection, account, bootstrap, previous)

    def logout(self, token, supplied_csrf):
        require_csrf(token, supplied_csrf)
        self.session(token)
        with self.workspace.session() as connection:
            connection.execute(
                "UPDATE workspace_sessions SET revoked_at=clock_timestamp() WHERE token_hash=%s AND deployment_id=%s",
                (digest(token), self.deployment_id),
            )
