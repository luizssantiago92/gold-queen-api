"""RF01 - Open Finance bank connection management."""

from fastapi import APIRouter

from app.api.deps import AIDep, CurrentUser, PluggyDep, SessionDep
from app.core.config import get_settings
from app.schemas.connections import (
    ConnectionResponse,
    ConnectTokenResponse,
    SyncRequest,
    SyncResponse,
)
from app.services import sync as sync_service
from app.services.treasury import user_connections

router = APIRouter(prefix="/v1/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionResponse])
def list_connections(current_user: CurrentUser, session: SessionDep):
    return user_connections(session, current_user.id)  # type: ignore[arg-type]


@router.post("/connect", response_model=ConnectTokenResponse)
async def create_connect_token(
    current_user: CurrentUser,
    session: SessionDep,
    pluggy: PluggyDep,
) -> ConnectTokenResponse:
    """Issue a Pluggy Connect token, enforcing the Free plan quota first."""
    used = sync_service.ensure_connection_quota(session, current_user.id)  # type: ignore[arg-type]
    token = await pluggy.create_connect_token(str(current_user.id))

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
    sync_service.delete_connection(
        session,
        current_user.id,  # type: ignore[arg-type]
        connection_id,
    )


@router.post("/sync", response_model=SyncResponse)
async def sync_connection(
    payload: SyncRequest,
    current_user: CurrentUser,
    session: SessionDep,
    pluggy: PluggyDep,
    ai: AIDep,
) -> SyncResponse:
    result = await sync_service.sync_item(
        session=session,
        user_id=current_user.id,  # type: ignore[arg-type]
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
