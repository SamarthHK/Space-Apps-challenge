from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Header, Request, Response
from pydantic import Field, SecretStr, field_validator

from agri_data.workspace.accounts import csrf_token
from .schemas import DTO, Meta


class Credentials(DTO):
    login: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9][a-z0-9_.@+-]{2,99}$")
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("login", mode="before")
    @classmethod
    def normalized_login(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class Registration(Credentials):
    password: SecretStr = Field(min_length=12, max_length=1024)


class AccountUser(DTO):
    id: str
    login: str


class AccountSession(DTO):
    mode: Literal["shared", "accounts"]
    user: AccountUser | None = None
    expires_at: datetime | None = None
    csrf_token: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class SessionResponse(DTO):
    data: AccountSession
    meta: Meta


class SignInContext(DTO):
    csrf_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: datetime


class SignInContextResponse(DTO):
    data: SignInContext
    meta: Meta


router = APIRouter(prefix="/api/v1/auth")


def envelope(request, data):
    return {"data": data, "meta": {"request_id": request.state.request_id, "api_version": "v1"}}


def cookie_options(store):
    return {"path": "/api/v1", "secure": store.settings.cookie_secure,
            "httponly": True, "samesite": "strict"}


def signed_in(request, response, token, data):
    store = request.app.state.account_store
    response.set_cookie(store.session_cookie, token, max_age=store.settings.session_seconds,
                        expires=data["expires_at"].astimezone(timezone.utc), **cookie_options(store))
    response.delete_cookie(store.bootstrap_cookie, **cookie_options(store))
    return envelope(request, data)


@router.get("/session", operation_id="getSession", response_model=SessionResponse)
def session(request: Request, response: Response):
    store = request.app.state.account_store
    if store.settings.mode == "shared":
        return envelope(request, AccountSession(mode="shared"))
    token = request.cookies.get(store.session_cookie)
    account = store.session(token, required=False)
    if account:
        return envelope(request, store.output(account, token))
    if token:
        response.delete_cookie(store.session_cookie, **cookie_options(store))
    return envelope(request, AccountSession(mode="accounts"))


@router.post("/bootstrap", operation_id="createSignInContext", response_model=SignInContextResponse)
def bootstrap(request: Request, response: Response):
    store = request.app.state.account_store
    store.require_enabled()
    token, expires = store.bootstrap(request.client.host, request.cookies.get(store.bootstrap_cookie))
    response.set_cookie(store.bootstrap_cookie, token, max_age=store.settings.bootstrap_seconds,
                        expires=expires.astimezone(timezone.utc), **cookie_options(store))
    return envelope(request, {"csrf_token": csrf_token(token), "expires_at": expires})


@router.post("/register", operation_id="registerAccount", response_model=SessionResponse, status_code=201)
def register(body: Registration, request: Request, response: Response,
             csrf: str | None = Header(None, alias="X-CSRF-Token")):
    store = request.app.state.account_store
    store.require_enabled()
    token, data = store.register(
        body.login, body.password.get_secret_value(), request.cookies.get(store.bootstrap_cookie),
        csrf, request.client.host, request.cookies.get(store.session_cookie), request.state.request_id,
    )
    return signed_in(request, response, token, data)


@router.post("/login", operation_id="loginAccount", response_model=SessionResponse)
def login(body: Credentials, request: Request, response: Response,
          csrf: str | None = Header(None, alias="X-CSRF-Token")):
    store = request.app.state.account_store
    store.require_enabled()
    token, data = store.login(
        body.login, body.password.get_secret_value(), request.cookies.get(store.bootstrap_cookie),
        csrf, request.client.host, request.cookies.get(store.session_cookie),
    )
    return signed_in(request, response, token, data)


@router.post("/logout", operation_id="logoutAccount", status_code=204)
def logout(request: Request, csrf: str | None = Header(None, alias="X-CSRF-Token")):
    store = request.app.state.account_store
    store.require_enabled()
    store.logout(request.cookies.get(store.session_cookie), csrf)
    response = Response(status_code=204)
    response.delete_cookie(store.session_cookie, **cookie_options(store))
    response.delete_cookie(store.bootstrap_cookie, **cookie_options(store))
    return response
