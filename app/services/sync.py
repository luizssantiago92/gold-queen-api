"""Open Finance synchronization: Pluggy item -> accounts -> categorized transactions."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.exceptions import ConnectionLimitError, NotFoundError
from app.models.entities import Account, BankConnection, Transaction
from app.services.ai import AIEngine
from app.services.pluggy import PluggyClient


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

    accounts = session.exec(
        select(Account).where(Account.connection_id == connection.id)
    ).all()

    for account in accounts:
        transactions = session.exec(
            select(Transaction).where(Transaction.account_id == account.id)
        ).all()
        for transaction in transactions:
            session.delete(transaction)
        session.delete(account)

    session.delete(connection)
    session.commit()


async def sync_item(
    session: Session,
    user_id: int,
    item_id: str,
    pluggy: PluggyClient,
    ai: AIEngine,
    institution_name: str | None = None,
) -> SyncResult:
    connection = session.exec(
        select(BankConnection).where(
            BankConnection.user_id == user_id,
            BankConnection.pluggy_item_id == item_id,
        )
    ).first()

    if connection is None:
        ensure_connection_quota(session, user_id)
        item = await pluggy.fetch_item(item_id)
        resolved_name = (
            institution_name
            or (item.get("connector") or {}).get("name")
            or "Unknown institution"
        )
        connection = BankConnection(
            user_id=user_id,
            pluggy_item_id=item_id,
            institution_name=resolved_name,
            status=item.get("status", "UPDATED"),
        )
        session.add(connection)
        session.commit()
        session.refresh(connection)

    accounts_synced = 0
    new_transactions: list[Transaction] = []

    for remote_account in await pluggy.fetch_accounts(item_id):
        account = session.exec(
            select(Account).where(
                Account.connection_id == connection.id,
                Account.pluggy_account_id == remote_account.account_id,
            )
        ).first()

        if account is None:
            account = Account(
                connection_id=connection.id,  # type: ignore[arg-type]
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

        known_ids = {
            row.pluggy_transaction_id
            for row in session.exec(
                select(Transaction).where(Transaction.account_id == account.id)
            ).all()
        }

        for remote_tx in await pluggy.fetch_transactions(remote_account.account_id):
            if remote_tx.transaction_id in known_ids:
                continue
            new_transactions.append(
                Transaction(
                    account_id=account.id,  # type: ignore[arg-type]
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

        for transaction in new_transactions:
            category = categories.get(transaction.pluggy_transaction_id)
            if category:
                transaction.category = category
                transaction.is_guarded = guarded
                categorized += 1
            session.add(transaction)

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
