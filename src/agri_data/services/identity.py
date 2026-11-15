"""Revocable opaque sessions, CSRF and profile persistence on PostgreSQL."""

import hashlib
import hmac
import re
import secrets
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
import psycopg
from psycopg import sql

from .database import connect
from .errors import ServiceError

PASSWORDS = PasswordHasher()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
PROFILE_FIELDS = (
    "name", "kannada_name", "phone", "village", "taluk", "district", "state",
    "soil_health_card_no", "farmer_category", "preferred_language",
    "risk_tolerance", "primary_objective",
)


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token):
    return hmac.new(token.encode(), b"agri-session-csrf-v1", hashlib.sha256).hexdigest()


def valid_cookie(token):
    return isinstance(token, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is not None


def reject_session():
    raise ServiceError(401, "unauthenticated", "A valid session is required")


def require_origin(settings, origin):
    if origin not in settings.allowed_origins:
        raise ServiceError(403, "origin_denied", "Request origin is not allowed")


def require_csrf(token, supplied):
    if not valid_cookie(token) or not supplied or not hmac.compare_digest(
        csrf_token(token).encode(), supplied.encode("utf-8")
    ):
        raise ServiceError(403, "csrf_invalid", "CSRF verification failed")


def create_account(settings, login, password):
    login = login.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.@+-]{2,99}", login):
        raise ValueError("Login must be 3-100 ASCII identifier characters")
    if not 12 <= len(password) <= 1024:
        raise ValueError("Password must contain 12-1024 characters")
    user_id = uuid4()
    try:
        with connect(settings) as connection:
            connection.execute(
                "INSERT INTO users (id,login,password_hash) VALUES (%s,%s,%s)",
                (user_id, login, PASSWORDS.hash(password)),
            )
            connection.execute(
                "INSERT INTO farmer_profiles (id,user_id) VALUES (%s,%s)",
                (uuid4(), user_id),
            )
            connection.execute(
                "INSERT INTO profile_revisions (profile_id,version,snapshot) "
                "SELECT id,version,to_jsonb(farmer_profiles) FROM farmer_profiles WHERE user_id=%s",
                (user_id,),
            )
    except psycopg.errors.UniqueViolation:
        raise ServiceError(409, "login_exists", "That login is already provisioned") from None
    return str(user_id)


def consume_limit(settings, bucket):
    bucket = digest(bucket)
    with connect(settings) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (bucket,))
        connection.execute(
            "DELETE FROM login_attempts WHERE bucket=%s AND "
            "attempted_at <= clock_timestamp() - %s * interval '1 second'",
            (bucket, settings.login_window_seconds),
        )
        count = connection.execute(
            "SELECT count(*) AS n FROM login_attempts WHERE bucket=%s", (bucket,)
        ).fetchone()["n"]
        if count >= settings.login_attempt_limit:
            raise ServiceError(
                429, "rate_limited", "Too many authentication attempts",
                {"Retry-After": str(settings.login_window_seconds)},
            )
        connection.execute("INSERT INTO login_attempts (bucket) VALUES (%s)", (bucket,))


def new_session(connection, user_id, seconds):
    token = secrets.token_urlsafe(32)
    row = connection.execute(
        "INSERT INTO auth_sessions (token_hash,user_id,expires_at) "
        "VALUES (%s,%s,clock_timestamp() + %s * interval '1 second') "
        "RETURNING expires_at",
        (digest(token), user_id, seconds),
    ).fetchone()
    return token, row["expires_at"]


def bootstrap(settings, origin, peer, previous_token=None):
    require_origin(settings, origin)
    consume_limit(settings, f"bootstrap:{peer}")
    with connect(settings) as connection:
        if valid_cookie(previous_token):
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash=%s AND user_id IS NULL",
                (digest(previous_token),),
            )
        token, _ = new_session(connection, None, settings.csrf_seconds)
    return token


def authenticate(settings, login, password, bootstrap_token, supplied_csrf, origin, peer,
                 previous_session=None):
    require_origin(settings, origin)
    require_csrf(bootstrap_token, supplied_csrf)
    consume_limit(settings, f"login-peer:{peer}")
    consume_limit(settings, f"login-account:{login.strip().lower()}")
    with connect(settings) as connection:
        bootstrap_row = connection.execute(
            "SELECT token_hash FROM auth_sessions WHERE token_hash=%s "
            "AND user_id IS NULL AND revoked_at IS NULL "
            "AND expires_at > clock_timestamp() FOR UPDATE",
            (digest(bootstrap_token),),
        ).fetchone()
        if not bootstrap_row:
            raise ServiceError(403, "csrf_expired", "Request a new CSRF context")
        user = connection.execute(
            "SELECT id,login,password_hash,active FROM users WHERE login=%s FOR UPDATE",
            (login.strip().lower(),),
        ).fetchone()
        try:
            verified = PASSWORDS.verify(user["password_hash"] if user else DUMMY_HASH, password)
        except (VerificationError, InvalidHashError):
            verified = False
        if not verified or not user or not user["active"]:
            raise ServiceError(401, "invalid_credentials", "Login or password is incorrect")
        if PASSWORDS.check_needs_rehash(user["password_hash"]):
            connection.execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (PASSWORDS.hash(password), user["id"]),
            )
        connection.execute(
            "DELETE FROM auth_sessions WHERE token_hash=%s", (digest(bootstrap_token),)
        )
        if valid_cookie(previous_session):
            connection.execute(
                "UPDATE auth_sessions SET revoked_at=clock_timestamp() WHERE token_hash=%s",
                (digest(previous_session),),
            )
        token, expires_at = new_session(connection, user["id"], settings.session_seconds)
    return token, {
        "user": {"id": str(user["id"]), "login": user["login"]},
        "expires_at": expires_at, "csrf_token": csrf_token(token),
    }


def session_row(connection, token, lock=False):
    if not valid_cookie(token):
        reject_session()
    row = connection.execute(
        "SELECT u.id,u.login,s.expires_at FROM auth_sessions s "
        "JOIN users u ON u.id=s.user_id "
        "WHERE s.token_hash=%s AND s.revoked_at IS NULL AND u.active "
        "AND s.expires_at > clock_timestamp()"
        + (" FOR UPDATE OF s, u" if lock else ""),
        (digest(token),),
    ).fetchone()
    if not row:
        reject_session()
    return row


def get_session(settings, token):
    with connect(settings) as connection:
        row = session_row(connection, token)
    return {
        "user": {"id": str(row["id"]), "login": row["login"]},
        "expires_at": row["expires_at"], "csrf_token": csrf_token(token),
    }


def logout(settings, token, supplied_csrf, origin):
    require_origin(settings, origin)
    require_csrf(token, supplied_csrf)
    with connect(settings) as connection:
        session_row(connection, token, lock=True)
        connection.execute(
            "UPDATE auth_sessions SET revoked_at=clock_timestamp() WHERE token_hash=%s",
            (digest(token),),
        )


def profile_output(row):
    return {key: value for key, value in row.items() if key != "user_id"}


def get_profile(settings, token):
    with connect(settings) as connection:
        user = session_row(connection, token)
        row = connection.execute(
            "SELECT * FROM farmer_profiles WHERE user_id=%s", (user["id"],)
        ).fetchone()
    if not row:
        raise ServiceError(404, "profile_not_found", "Profile is unavailable")
    return profile_output(row)


def update_profile(settings, token, supplied_csrf, origin, patch):
    require_origin(settings, origin)
    require_csrf(token, supplied_csrf)
    changes = patch.model_dump(exclude_unset=True)
    version = changes.pop("version")
    if not changes:
        raise ServiceError(422, "empty_update", "Supply at least one profile property")
    if changes.keys() - set(PROFILE_FIELDS):
        raise ServiceError(422, "invalid_update", "Unsupported profile property")
    with connect(settings) as connection:
        user = session_row(connection, token, lock=True)
        assignments = [
            sql.SQL("{}=%s").format(sql.Identifier(name)) for name in changes
        ]
        row = connection.execute(
            sql.SQL(
                "UPDATE farmer_profiles SET {}, version=version+1, "
                "updated_at=clock_timestamp() WHERE user_id=%s AND version=%s RETURNING *"
            ).format(sql.SQL(",").join(assignments)),
            (*changes.values(), user["id"], version),
        ).fetchone()
        if not row:
            raise ServiceError(409, "version_conflict", "Reload the profile before saving")
        connection.execute(
            "INSERT INTO profile_revisions (profile_id,version,snapshot) "
            "SELECT id,version,to_jsonb(farmer_profiles) FROM farmer_profiles WHERE id=%s",
            (row["id"],),
        )
    return profile_output(row)


def revoke_user_sessions(settings, login):
    with connect(settings) as connection:
        result = connection.execute(
            "UPDATE auth_sessions SET revoked_at=clock_timestamp() "
            "WHERE user_id=(SELECT id FROM users WHERE login=%s) AND revoked_at IS NULL",
            (login.strip().lower(),),
        )
        return result.rowcount
