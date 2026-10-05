"""Authentication endpoints backed by JWT."""

from fastapi import APIRouter, Request, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    RegistrationDisabledError,
)
from app.core.login_rate_limit import enforce_login_rate_limit
from app.core.security import (
    UNKNOWN_EMAIL_BCRYPT_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.entities import User, require_id
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.errors import error_responses
from app.services.demo_refresh import maybe_refresh_demo

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description=(
        "Register an email and password and return the new user. "
        "Public signup can be closed."
    ),
    responses=error_responses(
        (403, "Public signup is closed."),
        (409, "This email is already registered."),
        (422, "The body failed validation."),
    ),
)
def register(payload: RegisterRequest, session: SessionDep) -> User:
    if not get_settings().registration_enabled:
        raise RegistrationDisabledError("Registration is disabled.")

    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise ConflictError("This email is already registered.")

    user = User(
        email=str(payload.email),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in",
    description="Exchange an email and password for a bearer token.",
    responses=error_responses(
        (401, "The email or password is wrong."),
        (422, "The body failed validation."),
        (429, "Too many login attempts. Retry-After says when to try again."),
    ),
)
def login(
    payload: LoginRequest, session: SessionDep, request: Request
) -> TokenResponse:
    enforce_login_rate_limit(request)
    user = session.exec(select(User).where(User.email == payload.email)).first()
    # Unknown emails still pay for a bcrypt check so the response time does not
    # reveal whether the address is registered.
    stored_hash = user.password_hash if user is not None else UNKNOWN_EMAIL_BCRYPT_HASH
    password_matches = verify_password(payload.password, stored_hash)
    if user is None or not password_matches:
        raise AuthenticationError("Invalid email or password.")

    maybe_refresh_demo(session, user.email, require_id(user.id))

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        expires_in_minutes=get_settings().jwt_expire_minutes,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Read the current user",
    description="Return the user identified by the bearer token.",
    responses=error_responses((401, "The bearer token is missing or invalid.")),
)
def me(current_user: CurrentUser) -> User:
    return current_user
