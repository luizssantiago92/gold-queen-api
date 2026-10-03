"""RF01 - Open Finance bank connection management."""

import anyio
from fastapi import APIRouter

from app.api.deps import AIDep, CurrentUser, PluggyDep, SessionDep
from app.core.config import get_settings
from app.models.entities import require_id
from app.schemas.connections import (
    ConnectionResponse,
    ConnectTokenResponse,
    SyncRequest,
    SyncResponse,
)
from app.services import sync as sync_service
from app.services.demo_access import ensure_not_demo
from app.services.treasury import user_connections

router = APIRouter(prefix="/v1/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionResponse])
def list_connections(current_user: CurrentUser, session: SessionDep):
    return user_connections(session, require_id(current_user.id))


@router.post("/connect", response_model=ConnectTokenResponse)
def create_connect_token(
    current_user: CurrentUser,
    session: SessionDep,
    pluggy: PluggyDep,
) -> ConnectTokenResponse:
    """Issue a Pluggy Connect token, enforcing the Free plan quota first.

    Plain ``def`` so the synchronous session runs in the threadpool. The
    Pluggy call is async HTTP and is scheduled back onto the event loop.
    """
    ensure_not_demo(current_user)
    user_id = require_id(current_user.id)
    used = sync_service.ensure_connection_quota(session, user_id)
    token = anyio.from_thread.run(pluggy.create_connect_token, str(user_id))

    return ConnectTokenResponse(
        connect_token=token,
        connections_used=used,
        connections_limit=get_settings().max_bank_connections,
    )


@router.delete("/{connection_id}", status_code=204)
def delete_connection(
    connection_id: int,
    current_user: CurrentUser,
    session: SessionDep,
) -> None:
    """Unlink a bank, freeing a slot in the Free plan quota."""
    ensure_not_demo(current_user)
    sync_service.delete_connection(
        session,
        require_id(current_user.id),
        connection_id,
    )


@router.post("/sync", response_model=SyncResponse)
def sync_connection(
    payload: SyncRequest,
    current_user: CurrentUser,
    session: SessionDep,
    pluggy: PluggyDep,
    ai: AIDep,
) -> SyncResponse:
    """Sync on the threadpool so Gemini's blocking client cannot stall the loop."""
    ensure_not_demo(current_user)
    result = sync_service.sync_item(
        session=session,
        user_id=require_id(current_user.id),
        item_id=payload.item_id,
        pluggy=pluggy,
        ai=ai,
        institution_name=payload.institution_name,
    )

    return SyncResponse(
        connection=ConnectionResponse.model_validate(
            result.connection, from_attributes=True
        ),
        accounts_synced=result.accounts_synced,
        transactions_synced=result.transactions_synced,
        transactions_categorized=result.transactions_categorized,
        guarded=result.guarded,
    )
