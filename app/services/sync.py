"""Open Finance synchronization: Pluggy item -> accounts -> categorized transactions."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import anyio
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.core.config import get_settings
from app.core.exceptions import ConnectionLimitError, NotFoundError
from app.models.entities import Account, BankConnection, Transaction, require_id
from app.services.ai import AIEngine
from app.services.pluggy import PluggyClient, PluggyTransaction

logger = logging.getLogger(__name__)


class SyncResult:
    def __init__(
        self,
        connection: BankConnection,
        accounts_synced: int,
        transactions_synced: int,
        transactions_categorized: int,
        guarded: bool,
    ) -> None:
        self.connection = connection
        self.accounts_synced = accounts_synced
        self.transactions_synced = transactions_synced
        self.transactions_categorized = transactions_categorized
        self.guarded = guarded


def count_connections(session: Session, user_id: int) -> int:
    return len(
        session.exec(
            select(BankConnection).where(BankConnection.user_id == user_id)
        ).all()
    )


def ensure_connection_quota(session: Session, user_id: int) -> int:
    """Enforce the Free plan limit and return how many connections are in use."""
    limit = get_settings().max_bank_connections
    used = count_connections(session, user_id)
    if used >= limit:
        raise ConnectionLimitError(
            f"The Free plan allows up to {limit} bank connections. "
            "Remove one before linking another bank."
        )
    return used


def delete_connection(session: Session, user_id: int, connection_id: int) -> None:
    """Unlink a bank and erase everything derived from it.

    Without this the Free plan quota is a one-way door: after three banks the
    user can never link a fourth, even to replace one. Rows are removed
    child-first because the schema has no cascade.
    """
    connection = session.exec(
        select(BankConnection).where(
            BankConnection.id == connection_id,
            BankConnection.user_id == user_id,
        )
    ).first()

    if connection is None:
        raise NotFoundError("Bank connection not found.")

    account_ids = [
        account.id
        for account in session.exec(
            select(Account).where(Account.connection_id == connection.id)
        ).all()
    ]

    # Issued as explicit statements, one level at a time. Queuing per-row deletes
    # instead would let the unit of work emit them in any order, and Postgres
    # rejects removing an account while its transactions still reference it.
    if account_ids:
        session.execute(
            delete(Transaction).where(col(Transaction.account_id).in_(account_ids))
        )
        session.execute(delete(Account).where(col(Account.id).in_(account_ids)))

    session.delete(connection)
    session.commit()


def _connection_for_sync(
    session: Session, user_id: int, item_id: str
) -> BankConnection | None:
    """Return this user's row, or 404 when another user already linked the item.

    A missing row means the item has not been claimed yet. Callers must still
    confirm the Pluggy ``clientUserId`` before inserting one. The 404 matches
    a missing connection so the response does not reveal that the item exists.
    """
    rows = session.exec(
        select(BankConnection).where(BankConnection.pluggy_item_id == item_id)
    ).all()
    if not rows:
        return None
    for row in rows:
        if row.user_id == user_id:
            return row
    logger.warning("Rejected sync of item %s: not owned by user %s", item_id, user_id)
    raise NotFoundError("Bank connection not found.")


def _ensure_pluggy_item_owner(
    item: dict[str, Any], user_id: int, item_id: str, pluggy: PluggyClient
) -> None:
    """A first sync may claim an item only when Pluggy says it belongs to this user.

    Connect tokens are issued with ``clientUserId`` set to the user id, and
    Pluggy copies that onto the item. The offline simulator has no tenant, so
    it cannot prove ownership; rows already stored are still checked above.
    """
    if not pluggy.enabled:
        return
    owner = item.get("clientUserId")
    if owner is not None and str(owner).strip() == str(user_id):
        return
    logger.warning(
        "Rejected sync of item %s: clientUserId does not match user %s",
        item_id,
        user_id,
    )
    raise NotFoundError("Bank connection not found.")


def _dedupe_remote_transactions(
    remote: list[PluggyTransaction],
) -> list[PluggyTransaction]:
    """Keep the first copy when one fetch repeats a Pluggy transaction id.

    Cursor pages can overlap. Rows already stored are not visible for an id
    that this payload is about to insert, so a repeated id would land twice.
    """
    seen: set[str] = set()
    unique: list[PluggyTransaction] = []
    for item in remote:
        if item.transaction_id in seen:
            continue
        seen.add(item.transaction_id)
        unique.append(item)
    return unique


def _oldest_by_pluggy_id(rows: list[Transaction]) -> dict[str, Transaction]:
    """Map each Pluggy id to the row the migration would keep."""
    known: dict[str, Transaction] = {}
    for row in rows:
        current = known.get(row.pluggy_transaction_id)
        if current is None or (
            row.id is not None and current.id is not None and row.id < current.id
        ):
            known[row.pluggy_transaction_id] = row
    return known


def _apply_remote_fields(stored: Transaction, remote: PluggyTransaction) -> bool:
    """Refresh Pluggy fields. The stored category stays put."""
    changed = False
    if stored.description != remote.description:
        stored.description = remote.description
        changed = True
    if stored.amount != remote.amount:
        stored.amount = remote.amount
        changed = True
    if stored.transaction_date != remote.transaction_date:
        stored.transaction_date = remote.transaction_date
        changed = True
    return changed


def _persist_new_transaction(session: Session, row: Transaction) -> None:
    """Insert a row, or update the stored one when the unique key already won.

    The select above this call is the upsert. The savepoint covers a second
    sync that inserts the same pair between that select and this flush. That
    race is rejected only after ``uq_transactions_account_pluggy_id`` exists.
    """
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:
        # A failed flush inside the savepoint already drops the pending row.
        if row in session:
            session.expunge(row)
        stored = session.exec(
            select(Transaction).where(
                Transaction.account_id == row.account_id,
                Transaction.pluggy_transaction_id == row.pluggy_transaction_id,
            )
        ).first()
        if stored is None:
            raise
        stored.description = row.description
        stored.amount = row.amount
        stored.transaction_date = row.transaction_date
        session.add(stored)


def _on_event_loop(func: Any, /, *args: Any) -> Any:
    """Run one async Pluggy call on the server loop and wait on this thread.

    Sync handlers run in FastAPI's threadpool so the synchronous session and
    Gemini client never touch the loop. Pluggy is already async HTTP, so only
    that call goes back.
    """
    return anyio.from_thread.run(func, *args)


def sync_item(
    session: Session,
    user_id: int,
    item_id: UUID,
    pluggy: PluggyClient,
    ai: AIEngine,
    institution_name: str | None = None,
) -> SyncResult:
    item_ref = str(item_id)
    connection = _connection_for_sync(session, user_id, item_ref)

    if connection is None:
        ensure_connection_quota(session, user_id)
        item = _on_event_loop(pluggy.fetch_item, item_id)
        _ensure_pluggy_item_owner(item, user_id, item_ref, pluggy)
        resolved_name = (
            institution_name
            or (item.get("connector") or {}).get("name")
            or "Unknown institution"
        )
        connection = BankConnection(
            user_id=user_id,
            pluggy_item_id=item_ref,
            institution_name=resolved_name,
            status=item.get("status", "UPDATED"),
        )
        session.add(connection)
        session.commit()
        session.refresh(connection)

    accounts_synced = 0
    new_transactions: list[Transaction] = []
    connection_id = require_id(connection.id)

    for remote_account in _on_event_loop(pluggy.fetch_accounts, item_id):
        account = session.exec(
            select(Account).where(
                Account.connection_id == connection_id,
                Account.pluggy_account_id == remote_account.account_id,
            )
        ).first()

        if account is None:
            account = Account(
                connection_id=connection_id,
                pluggy_account_id=remote_account.account_id,
                name=remote_account.name,
                account_type=remote_account.account_type,
                balance=remote_account.balance,
                currency=remote_account.currency,
            )
        else:
            account.balance = remote_account.balance
            account.updated_at = datetime.now(UTC)

        session.add(account)
        session.commit()
        session.refresh(account)
        accounts_synced += 1
        account_id = require_id(account.id)

        known = _oldest_by_pluggy_id(
            list(
                session.exec(
                    select(Transaction).where(Transaction.account_id == account_id)
                ).all()
            )
        )

        for remote_tx in _dedupe_remote_transactions(
            _on_event_loop(pluggy.fetch_transactions, remote_account.account_id)
        ):
            stored = known.get(remote_tx.transaction_id)
            if stored is not None:
                if _apply_remote_fields(stored, remote_tx):
                    session.add(stored)
                continue
            new_transactions.append(
                Transaction(
                    account_id=account_id,
                    pluggy_transaction_id=remote_tx.transaction_id,
                    description=remote_tx.description,
                    amount=remote_tx.amount,
                    transaction_date=remote_tx.transaction_date,
                )
            )

    guarded = False
    categorized = 0
    if new_transactions:
        payload: list[tuple[str, str, Decimal]] = [
            (tx.pluggy_transaction_id, tx.description, tx.amount)
            for tx in new_transactions
        ]
        categories, guarded = ai.categorize(payload)

        # Flush refreshed rows before the per-row savepoint, so a conflict
        # rolls back only the new insert.
        session.flush()
        for transaction in new_transactions:
            category = categories.get(transaction.pluggy_transaction_id)
            if category:
                transaction.category = category
                transaction.is_guarded = guarded
                categorized += 1
            _persist_new_transaction(session, transaction)

        session.commit()

    connection.last_synced_at = datetime.now(UTC)
    connection.status = "UPDATED"
    session.add(connection)
    session.commit()
    session.refresh(connection)

    return SyncResult(
        connection=connection,
        accounts_synced=accounts_synced,
        transactions_synced=len(new_transactions),
        transactions_categorized=categorized,
        guarded=guarded,
    )
