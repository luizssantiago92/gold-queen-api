"""Tests for demo transaction date refresh."""

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.models.entities import Account, BankConnection, Transaction, User
from app.services.demo_refresh import maybe_refresh_demo, refresh_demo_transaction_dates


def _seed_transaction(
    session: Session,
    user: User,
    transaction_date: date,
) -> None:
    connection = BankConnection(
        user_id=user.id,  # type: ignore[arg-type]
        pluggy_item_id="item-demo",
        institution_name="Pluggy Bank",
        status="UPDATED",
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)

    account = Account(
        connection_id=connection.id,  # type: ignore[arg-type]
        pluggy_account_id="acc-demo",
        name="Checking",
        balance=Decimal("1000.00"),
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    session.add(
        Transaction(
            account_id=account.id,  # type: ignore[arg-type]
            pluggy_transaction_id="tx-demo",
            description="Demo purchase",
            amount=Decimal("-10.00"),
            transaction_date=transaction_date,
            category="Shopping",
            is_guarded=False,
        )
    )
    session.commit()


def test_refresh_shifts_stale_dates_into_current_month(session: Session) -> None:
    user = User(email="queen@goldqueen.dev", display_name="Queen", password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)

    stale = date.today().replace(day=1) - timedelta(days=10)
    _seed_transaction(session, user, stale)

    updated = refresh_demo_transaction_dates(session, user.id)  # type: ignore[arg-type]
    assert updated == 1

    transaction = session.exec(
        select(Transaction).where(Transaction.pluggy_transaction_id == "tx-demo")
    ).first()
    assert transaction is not None
    assert transaction.transaction_date.month == date.today().month
    assert transaction.transaction_date <= date.today()


def test_maybe_refresh_ignores_non_demo_users(session: Session) -> None:
    user = User(email="knight@goldqueen.dev", display_name="Knight", password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)

    stale = date.today().replace(day=1) - timedelta(days=10)
    _seed_transaction(session, user, stale)

    assert maybe_refresh_demo(session, user.email, user.id) == 0  # type: ignore[arg-type]
