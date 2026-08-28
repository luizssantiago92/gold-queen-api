"""Treasury analytics shared by the dashboard and the AI advisor."""

from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.entities import Account, BankConnection, Transaction

ZERO = Decimal("0.00")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def month_bounds(reference: date | None = None) -> tuple[date, date]:
    today = reference or date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    return first_day, next_month


def user_connections(session: Session, user_id: int) -> list[BankConnection]:
    return list(
        session.exec(
            select(BankConnection).where(BankConnection.user_id == user_id)
        ).all()
    )


def user_accounts(session: Session, user_id: int) -> list[tuple[Account, BankConnection]]:
    rows = session.exec(
        select(Account, BankConnection)
        .join(BankConnection, Account.connection_id == BankConnection.id)  # type: ignore[arg-type]
        .where(BankConnection.user_id == user_id)
    ).all()
    return [(account, connection) for account, connection in rows]


def user_transactions(
    session: Session,
    user_id: int,
    start: date | None = None,
    end: date | None = None,
) -> list[tuple[Transaction, BankConnection]]:
    statement = (
        select(Transaction, BankConnection)
        .join(Account, Transaction.account_id == Account.id)  # type: ignore[arg-type]
        .join(BankConnection, Account.connection_id == BankConnection.id)  # type: ignore[arg-type]
        .where(BankConnection.user_id == user_id)
    )
    if start is not None:
        statement = statement.where(Transaction.transaction_date >= start)
    if end is not None:
        statement = statement.where(Transaction.transaction_date < end)

    rows = session.exec(statement.order_by(Transaction.transaction_date.desc())).all()  # type: ignore[attr-defined]
    return [(transaction, connection) for transaction, connection in rows]


def total_balance(session: Session, user_id: int) -> Decimal:
    return _quantize(
        sum((account.balance for account, _ in user_accounts(session, user_id)), ZERO)
    )


def balance_by_connection(session: Session, user_id: int) -> dict[int, Decimal]:
    balances: dict[int, Decimal] = {}
    for account, connection in user_accounts(session, user_id):
        if connection.id is None:
            continue
        balances[connection.id] = balances.get(connection.id, ZERO) + account.balance
    return {key: _quantize(value) for key, value in balances.items()}


def month_totals(session: Session, user_id: int) -> tuple[Decimal, Decimal]:
    """Return ``(expenses, income)`` for the current month as positive amounts."""
    start, end = month_bounds()
    expenses = ZERO
    income = ZERO
    for transaction, _ in user_transactions(session, user_id, start, end):
        if transaction.amount < 0:
            expenses += -transaction.amount
        else:
            income += transaction.amount
    return _quantize(expenses), _quantize(income)


def expenses_by_category(session: Session, user_id: int) -> dict[str, tuple[Decimal, int]]:
    """Return ``category -> (total_expense, transaction_count)`` for this month."""
    start, end = month_bounds()
    breakdown: dict[str, tuple[Decimal, int]] = {}
    for transaction, _ in user_transactions(session, user_id, start, end):
        if transaction.amount >= 0:
            continue
        total, count = breakdown.get(transaction.category, (ZERO, 0))
        breakdown[transaction.category] = (total + -transaction.amount, count + 1)
    return {key: (_quantize(total), count) for key, (total, count) in breakdown.items()}


def share(value: Decimal, total: Decimal) -> float:
    if total <= ZERO:
        return 0.0
    return round(float(value / total) * 100, 2)


def build_ai_summary(session: Session, user_id: int) -> str:
    """Compact treasury snapshot handed to the AI as grounding context.

    The product rules are included because users ask about them directly, and
    without them the model invents plausible-sounding limits.
    """
    settings = get_settings()

    balance = total_balance(session, user_id)
    expenses, income = month_totals(session, user_id)
    categories = expenses_by_category(session, user_id)
    connections = user_connections(session, user_id)

    ranked = sorted(categories.items(), key=lambda item: item[1][0], reverse=True)
    category_lines = "\n".join(
        f"- {category}: R$ {total} ({count} transactions)"
        for category, (total, count) in ranked[:8]
    ) or "- no expenses recorded this month"

    bank_lines = "\n".join(
        f"- {connection.institution_name}" for connection in connections
    ) or "- no banks connected yet"

    reference = date.today().strftime("%Y-%m")
    return (
        "Product rules (authoritative, never contradict them):\n"
        f"- The free plan allows up to {settings.max_bank_connections} bank connections.\n"
        f"- The user may ask the Gold Queen {settings.chat_daily_limit} questions per day.\n"
        "\n"
        f"Reference month: {reference}\n"
        f"Total balance across banks: R$ {balance}\n"
        f"Month income: R$ {income}\n"
        f"Month expenses: R$ {expenses}\n"
        f"Connected banks ({len(connections)} of "
        f"{settings.max_bank_connections}):\n{bank_lines}\n"
        f"Expenses by category:\n{category_lines}"
    )
