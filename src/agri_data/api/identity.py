"""Thin identity routes; the service owns transactions and authorization."""

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.security import APIKeyCookie

from agri_data.services import identity
from agri_data.services.errors import ServiceError
from .schemas import CsrfContext, LoginRequest, Profile, ProfilePatch, Session

SESSION_COOKIE = "agri_session"
CONTEXT_COOKIE = "agri_csrf_context"
session_cookie = APIKeyCookie(name=SESSION_COOKIE, scheme_name="SessionCookie", auto_error=False)
context_cookie = APIKeyCookie(name=CONTEXT_COOKIE, scheme_name="CsrfContextCookie", auto_error=False)


def reject_query(request: Request):
    if request.query_params:
        raise ServiceError(422, "unexpected_query", "This resource does not accept query parameters")


router = APIRouter(prefix="/api/v1", dependencies=[Depends(reject_query)])


def browser_origin(origin: str | None = Header(default=None, alias="Origin")):
    """Service validation returns a stable 403 when this required origin is absent."""


def browser_csrf(
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
):
    """Service validation returns a stable 403 for absent or invalid CSRF proof."""


browser_write = [Depends(browser_origin), Depends(browser_csrf)]
authenticated = [Depends(session_cookie)]


def set_cookie(response, settings, name, value, max_age):
    response.set_cookie(
        name, value, max_age=max_age, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )


def clear_cookie(response, settings, name):
    response.delete_cookie(
        name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )


@router.get("/auth/csrf", response_model=CsrfContext, dependencies=[Depends(browser_origin)])
def csrf(request: Request, response: Response):
    settings = request.app.state.settings
    token = identity.bootstrap(
        settings, request.headers.get("origin"),
        request.client.host if request.client else "unknown",
        request.cookies.get(CONTEXT_COOKIE),
    )
    set_cookie(response, settings, CONTEXT_COOKIE, token, settings.csrf_seconds)
    return {"csrf_token": identity.csrf_token(token)}


@router.post(
    "/auth/session", response_model=Session,
    dependencies=[Depends(context_cookie), *browser_write],
)
def login(body: LoginRequest, request: Request, response: Response):
    settings = request.app.state.settings
    token, session = identity.authenticate(
        settings, body.login, body.password.get_secret_value(),
        request.cookies.get(CONTEXT_COOKIE), request.headers.get("x-csrf-token"),
        request.headers.get("origin"), request.client.host if request.client else "unknown",
        request.cookies.get(SESSION_COOKIE),
    )
    set_cookie(response, settings, SESSION_COOKIE, token, settings.session_seconds)
    clear_cookie(response, settings, CONTEXT_COOKIE)
    return session


@router.get("/auth/session", response_model=Session, dependencies=authenticated)
def current_session(request: Request):
    return identity.get_session(
        request.app.state.settings, request.cookies.get(SESSION_COOKIE)
    )


@router.delete("/auth/session", status_code=204, dependencies=[*authenticated, *browser_write])
def logout(request: Request):
    settings = request.app.state.settings
    identity.logout(
        settings, request.cookies.get(SESSION_COOKIE),
        request.headers.get("x-csrf-token"), request.headers.get("origin"),
    )
    response = Response(status_code=204)
    clear_cookie(response, settings, SESSION_COOKIE)
    clear_cookie(response, settings, CONTEXT_COOKIE)
    return response


@router.get("/me/profile", response_model=Profile, dependencies=authenticated)
def profile(request: Request):
    return identity.get_profile(
        request.app.state.settings, request.cookies.get(SESSION_COOKIE)
    )


@router.patch(
    "/me/profile", response_model=Profile, dependencies=[*authenticated, *browser_write],
)
def save_profile(body: ProfilePatch, request: Request):
    return identity.update_profile(
        request.app.state.settings, request.cookies.get(SESSION_COOKIE),
        request.headers.get("x-csrf-token"), request.headers.get("origin"), body,
    )
