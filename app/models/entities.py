"""SQLModel entities backing the Gold Queen treasury."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

# SQLModel 0.0.45 maps a plain datetime to TIMESTAMP WITH TIME ZONE.
# The initial migration created TIMESTAMP WITHOUT TIME ZONE. Keep that
# storage so this upgrade does not rewrite existing columns. Writers still
# pass aware UTC values; SQLAlchemy stores the UTC clock time.
_STORED_DATETIME = DateTime(timezone=False)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def require_id(value: int | None) -> int:
    """Return a primary key after the row has been flushed.

    SQLModel types table ids as optional because they are filled on insert.
    Callers that already loaded or refreshed a row use this to narrow the type.
    A missing id is a programming error, not a client-facing response.
    """
    if value is None:
        raise RuntimeError("Persisted row is missing a primary key.")
    return value


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    password_hash: str
    created_at: datetime = Field(default_factory=_utcnow, sa_type=_STORED_DATETIME)


class BankConnection(SQLModel, table=True):
    """A Pluggy item: one bank linked by the user through Open Finance."""

    __tablename__ = "bank_connections"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    pluggy_item_id: str = Field(index=True)
    institution_name: str
    status: str = Field(default="PENDING")
    last_synced_at: datetime | None = Field(default=None, sa_type=_STORED_DATETIME)
    created_at: datetime = Field(default_factory=_utcnow, sa_type=_STORED_DATETIME)


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: int | None = Field(default=None, primary_key=True)
    connection_id: int = Field(foreign_key="bank_connections.id", index=True)
    pluggy_account_id: str = Field(index=True)
    name: str
    account_type: str = Field(default="BANK")
    balance: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(default="BRL")
    updated_at: datetime = Field(default_factory=_utcnow, sa_type=_STORED_DATETIME)


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    pluggy_transaction_id: str = Field(index=True)
    description: str
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    transaction_date: date = Field(index=True)
    category: str = Field(default="Uncategorized")
    # True when the AI output passed strict schema validation.
    is_guarded: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow, sa_type=_STORED_DATETIME)


class ChatCache(SQLModel, table=True):
    """Same question, same day, zero extra tokens."""

    __tablename__ = "chat_cache"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    question_hash: str = Field(index=True)
    question: str
    answer: str
    usage_date: date = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow, sa_type=_STORED_DATETIME)


class ChatUsage(SQLModel, table=True):
    """Daily token-bucket counter that survives process restarts."""

    __tablename__ = "chat_usage"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    usage_date: date = Field(index=True)
    request_count: int = Field(default=0)


class DemoChatUsage(SQLModel, table=True):
    """Per-visitor daily quota for a shared demo account.

    Normal accounts keep a single ``chat_usage`` row. The public demo is one
    user seen by many visitors, so its counter is split by client address.
    A new table (not a new column) is created by ``create_all`` on startup,
    which leaves databases that already exist able to boot.
    """

    __tablename__ = "demo_chat_usage"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    subject_key: str = Field(index=True)
    usage_date: date = Field(index=True)
    request_count: int = Field(default=0)
