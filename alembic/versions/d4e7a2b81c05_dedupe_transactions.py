"""dedupe transactions and unique Pluggy id per account

Revision ID: d4e7a2b81c05
Revises: c7a1b5e0d942
Create Date: 2026-10-07 18:30:00.000000

Deletes extra rows that share ``(account_id, pluggy_transaction_id)``, then
extra rows that share ``(account_id, description, amount, transaction_date)``.
Each group keeps the oldest ``id``. Amounts match after quantizing to cents,
so ``8500`` and ``8500.00`` are the same copy. Sync also skips that
description, cent amount, and date when a later fetch mints a new Pluggy id.
Downgrade drops
``uq_transactions_account_pluggy_id`` and does not restore deleted rows.
"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision: str = "d4e7a2b81c05"
down_revision: str | None = "c7a1b5e0d942"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_transactions_account_pluggy_id"


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _has_unique(table: str, name: str) -> bool:
    if table not in _table_names():
        return False
    inspector = sa.inspect(op.get_bind())
    names = {item["name"] for item in inspector.get_unique_constraints(table)}
    names.update(
        item["name"] for item in inspector.get_indexes(table) if item.get("unique")
    )
    return name in names


def _transactions():
    return sa.table(
        "transactions",
        sa.column("id", sa.Integer),
        sa.column("account_id", sa.Integer),
        sa.column("pluggy_transaction_id", sa.String),
        sa.column("description", sa.String),
        sa.column("amount", sa.Numeric),
        sa.column("transaction_date", sa.Date),
    )


def _load_rows(table: sa.Table) -> list[sa.Row[tuple[object, ...]]]:
    return list(op.get_bind().execute(sa.select(table).order_by(table.c.id)).fetchall())


def _amount_key(value: object) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def _date_key(value: object) -> str:
    if hasattr(value, "isoformat"):
        return str(value.isoformat())[:10]
    return str(value)[:10]


def _delete_extras(
    table: sa.Table,
    rows: list[sa.Row[tuple[object, ...]]],
    key_of,
) -> None:
    grouped: dict[tuple[object, ...], list[sa.Row[tuple[object, ...]]]] = {}
    for row in rows:
        grouped.setdefault(key_of(row), []).append(row)
    extra_ids = [
        row.id for group in grouped.values() if len(group) > 1 for row in group[1:]
    ]
    if not extra_ids:
        return
    op.get_bind().execute(sa.delete(table).where(table.c.id.in_(extra_ids)))


def _dedupe_transactions() -> None:
    if "transactions" not in _table_names():
        return
    table = _transactions()
    _delete_extras(
        table,
        _load_rows(table),
        lambda row: (row.account_id, row.pluggy_transaction_id),
    )
    _delete_extras(
        table,
        _load_rows(table),
        lambda row: (
            row.account_id,
            row.description,
            _amount_key(row.amount),
            _date_key(row.transaction_date),
        ),
    )


def upgrade() -> None:
    _dedupe_transactions()
    if "transactions" not in _table_names() or _has_unique(
        "transactions", CONSTRAINT_NAME
    ):
        return
    with op.batch_alter_table("transactions") as batch:
        batch.create_unique_constraint(
            CONSTRAINT_NAME, ["account_id", "pluggy_transaction_id"]
        )


def downgrade() -> None:
    # Deleted copies stay deleted.
    if not _has_unique("transactions", CONSTRAINT_NAME):
        return
    with op.batch_alter_table("transactions") as batch:
        batch.drop_constraint(CONSTRAINT_NAME, type_="unique")
