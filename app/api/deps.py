"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.database import get_session
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.models.entities import User
from app.services.ai import AIEngine, get_ai_engine
from app.services.pluggy import PluggyClient, get_pluggy_client

_bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token.")

    user_id = decode_access_token(credentials.credentials)
    user = session.get(User, int(user_id))
    if user is None:
        raise AuthenticationError("Token subject no longer exists.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
PluggyDep = Annotated[PluggyClient, Depends(get_pluggy_client)]
AIDep = Annotated[AIEngine, Depends(get_ai_engine)]
