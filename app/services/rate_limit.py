"""Daily token bucket for Gold Queen interactions (RF05).

The counter lives in PostgreSQL so the quota survives restarts and multiple
workers, which an in-memory ``lru_cache`` alone could not guarantee.

Consumption is one statement: insert the first request, or increment an
existing row only while it is still under the limit. A unique constraint on
the usage key makes that statement safe when two requests arrive together.
"""

from datetime import date

from sqlalchemy import Table, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.core.locale import DEFAULT_LOCALE, Locale
from app.models.entities import ChatUsage, DemoChatUsage

QUEEN_QUOTA_MESSAGES: dict[Locale, str] = {
    "en": (
        "The Queen must retire to her chambers to balance the royal treasury. "
        "Return in 24 hours for new counsel about your gold."
    ),
    "pt": (
        "A Rainha precisa recolher-se aos seus aposentos para balancear "
        "o tesouro real. "
        "Retorne em 24 horas para novos conselhos sobre o seu ouro."
    ),
}


def _as_table(model: type[ChatUsage] | type[DemoChatUsage]) -> Table:
    table = vars(model).get("__table__")
    if not isinstance(table, Table):
        raise RuntimeError("Usage model is missing a table.")
    return table


def _table_for(subject_key: str) -> Table:
    if subject_key:
        return _as_table(DemoChatUsage)
    return _as_table(ChatUsage)


def _dialect_insert(session: Session, table: Table):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(table)
    if dialect == "sqlite":
        return sqlite_insert(table)
    raise RuntimeError(f"Unsupported database dialect: {dialect}")


def _filters(
    table: Table, user_id: int, usage_date: date, subject_key: str
) -> dict[str, object]:
    values: dict[str, object] = {"user_id": user_id, "usage_date": usage_date}
    if "subject_key" in table.c:
        values["subject_key"] = subject_key
    return values


def _conflict_columns(table: Table) -> list[str]:
    if "subject_key" in table.c:
        return ["user_id", "subject_key", "usage_date"]
    return ["user_id", "usage_date"]


def _current_count(
    session: Session,
    table: Table,
    user_id: int,
    usage_date: date,
    subject_key: str,
) -> int:
    statement = select(table.c.request_count)
    for column, value in _filters(table, user_id, usage_date, subject_key).items():
        statement = statement.where(table.c[column] == value)
    found = session.exec(statement).first()
    if found is None:
        return 0
    return int(found)


def remaining_requests(session: Session, user_id: int, subject_key: str = "") -> int:
    limit = get_settings().chat_daily_limit
    count = _current_count(
        session, _table_for(subject_key), user_id, date.today(), subject_key
    )
    return max(limit - count, 0)


def refund_request(session: Session, user_id: int, subject_key: str = "") -> int:
    """Give a consumed interaction back when the model never answered."""
    limit = get_settings().chat_daily_limit
    table = _table_for(subject_key)
    today = date.today()
    statement = update(table).values(request_count=table.c.request_count - 1)
    for column, value in _filters(table, user_id, today, subject_key).items():
        statement = statement.where(table.c[column] == value)
    statement = statement.where(table.c.request_count > 0).returning(
        table.c.request_count
    )
    new_count = session.execute(statement).scalar_one_or_none()
    session.commit()
    count = 0 if new_count is None else int(new_count)
    return max(limit - count, 0)


def consume_request(
    session: Session,
    user_id: int,
    locale: Locale = DEFAULT_LOCALE,
    subject_key: str = "",
) -> int:
    """Consume one daily interaction or raise ``RateLimitError``."""
    limit = get_settings().chat_daily_limit
    table = _table_for(subject_key)
    today = date.today()
    inserted = _dialect_insert(session, table).values(
        request_count=1,
        **_filters(table, user_id, today, subject_key),
    )
    statement = inserted.on_conflict_do_update(
        index_elements=_conflict_columns(table),
        set_={"request_count": table.c.request_count + 1},
        where=table.c.request_count < limit,
    ).returning(table.c.request_count)
    new_count = session.execute(statement).scalar_one_or_none()
    session.commit()
    if new_count is None:
        raise RateLimitError(QUEEN_QUOTA_MESSAGES[locale])
    return max(limit - int(new_count), 0)
