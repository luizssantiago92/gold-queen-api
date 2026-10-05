"""quota uniqueness and timezone-aware timestamps

Revision ID: c7a1b5e0d942
Revises: a630d3c39926
Create Date: 2026-10-05 03:20:00.000000

Existing naive timestamps are read as UTC (``AT TIME ZONE 'UTC'``). Duplicate
chat usage rows are merged by summing ``request_count`` into the oldest id,
then a unique constraint is added. No treasury rows are deleted.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7a1b5e0d942"
down_revision: str | None = "a630d3c39926"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ_USING = "{column} AT TIME ZONE 'UTC'"

_TIMESTAMP_COLUMNS: tuple[tuple[str, str, bool], ...] = (
    ("users", "created_at", False),
    ("bank_connections", "last_synced_at", True),
    ("bank_connections", "created_at", False),
    ("accounts", "updated_at", False),
    ("transactions", "created_at", False),
    ("chat_cache", "created_at", False),
)


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


def _dedupe_usage(table: str, key_columns: tuple[str, ...]) -> None:
    """Sum duplicate counters into the oldest row and delete the rest."""
    if table not in _table_names():
        return
    reflected = sa.table(
        table,
        sa.column("id", sa.Integer),
        sa.column("request_count", sa.Integer),
        *(sa.column(name) for name in key_columns),
    )
    rows = (
        op.get_bind().execute(sa.select(reflected).order_by(reflected.c.id)).fetchall()
    )
    grouped: dict[tuple[object, ...], list[sa.Row[tuple[object, ...]]]] = {}
    for row in rows:
        key = tuple(getattr(row, column) for column in key_columns)
        grouped.setdefault(key, []).append(row)
    for group in grouped.values():
        if len(group) < 2:
            continue
        keeper = group[0]
        total = sum(int(row.request_count) for row in group)
        op.get_bind().execute(
            sa.update(reflected)
            .where(reflected.c.id == keeper.id)
            .values(request_count=total)
        )
        extra_ids = [row.id for row in group[1:]]
        op.get_bind().execute(sa.delete(reflected).where(reflected.c.id.in_(extra_ids)))


def _ensure_unique(table: str, name: str, columns: tuple[str, ...]) -> None:
    if table not in _table_names() or _has_unique(table, name):
        return
    _dedupe_usage(table, columns)
    with op.batch_alter_table(table) as batch:
        batch.create_unique_constraint(name, columns)


def _drop_unique(table: str, name: str) -> None:
    if not _has_unique(table, name):
        return
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(name, type_="unique")


def _column_is_timestamptz(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    for item in inspector.get_columns(table):
        if item["name"] != column:
            continue
        return bool(getattr(item["type"], "timezone", False))
    return False


def _convert_timestamps(*, to_timestamptz: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column, nullable in _TIMESTAMP_COLUMNS:
        if table not in _table_names():
            continue
        already = _column_is_timestamptz(table, column)
        if to_timestamptz and already:
            continue
        if not to_timestamptz and not already:
            continue
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=not to_timestamptz),
            type_=sa.DateTime(timezone=to_timestamptz),
            existing_nullable=nullable,
            postgresql_using=TIMESTAMPTZ_USING.format(column=column),
        )


def _create_demo_usage_table() -> None:
    op.create_table(
        "demo_chat_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subject_key", sa.String(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "subject_key",
            "usage_date",
            name="uq_demo_chat_usage_subject_date",
        ),
    )
    op.create_index(
        "ix_demo_chat_usage_user_id", "demo_chat_usage", ["user_id"], unique=False
    )
    op.create_index(
        "ix_demo_chat_usage_subject_key",
        "demo_chat_usage",
        ["subject_key"],
        unique=False,
    )
    op.create_index(
        "ix_demo_chat_usage_usage_date",
        "demo_chat_usage",
        ["usage_date"],
        unique=False,
    )


def upgrade() -> None:
    _ensure_unique("chat_usage", "uq_chat_usage_user_date", ("user_id", "usage_date"))
    if "demo_chat_usage" not in _table_names():
        _create_demo_usage_table()
    else:
        _ensure_unique(
            "demo_chat_usage",
            "uq_demo_chat_usage_subject_date",
            ("user_id", "subject_key", "usage_date"),
        )
    _convert_timestamps(to_timestamptz=True)


def downgrade() -> None:
    # Merged quota rows stay merged. Timestamps go back to naive UTC clock time.
    # demo_chat_usage is left in place because it may predate this revision.
    _convert_timestamps(to_timestamptz=False)
    _drop_unique("demo_chat_usage", "uq_demo_chat_usage_subject_date")
    _drop_unique("chat_usage", "uq_chat_usage_user_date")
