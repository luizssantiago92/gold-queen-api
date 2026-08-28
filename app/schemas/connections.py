"""Open Finance connection payloads (RF01)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConnectTokenResponse(BaseModel):
    """Short-lived token consumed by the Pluggy Connect widget in the frontend."""

    connect_token: str
    expires_in_minutes: int = 30
    connections_used: int
    connections_limit: int


class SyncRequest(BaseModel):
    """Sent by the frontend after the Pluggy widget reports success."""

    item_id: str = Field(min_length=1, description="Pluggy item id returned by the widget")
    institution_name: str | None = None


class ConnectionResponse(BaseModel):
    id: int
    pluggy_item_id: str
    institution_name: str
    status: str
    last_synced_at: datetime | None


class SyncResponse(BaseModel):
    connection: ConnectionResponse
    accounts_synced: int
    transactions_synced: int
    transactions_categorized: int
    guarded: bool
