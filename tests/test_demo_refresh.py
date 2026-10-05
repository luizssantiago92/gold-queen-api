"""Tests for demo transaction date refresh."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password
from app.models.entities import Account, BankConnection, Transaction, User, require_id
from app.services.demo_refresh import maybe_refresh_demo, refresh_demo_transaction_dates


def _seed_transaction(
    session: Session,
    user: User,
    transaction_date: date,
) -> None:
    connection = BankConnection(
        user_id=require_id(user.id),
        pluggy_item_id="item-demo",
        institution_name="Pluggy Bank",
        status="UPDATED",
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)

    account = Account(
        connection_id=require_id(connection.id),
        pluggy_account_id="acc-demo",
        name="Checking",
        balance=Decimal("1000.00"),
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    session.add(
        Transaction(
            account_id=require_id(account.id),
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

    updated = refresh_demo_transaction_dates(session, require_id(user.id))
    assert updated == 1

    transaction = session.exec(
        select(Transaction).where(Transaction.pluggy_transaction_id == "tx-demo")
    ).first()
    assert transaction is not None
    assert transaction.transaction_date.month == date.today().month
    assert transaction.transaction_date <= date.today()


def test_login_refreshes_demo_dates_and_dashboard_reads_do_not(
    client: TestClient, session: Session
) -> None:
    password = "QueenDemo123!"
    user = User(
        email="queen@goldqueen.dev",
        display_name="Queen",
        password_hash=hash_password(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    stale = date.today().replace(day=1) - timedelta(days=40)
    _seed_transaction(session, user, stale)

    client.headers.update(
        {"Authorization": f"Bearer {create_access_token(str(require_id(user.id)))}"}
    )
    assert client.get("/v1/dashboard/overview").status_code == 200
    session.expire_all()
    untouched = session.exec(
        select(Transaction).where(Transaction.pluggy_transaction_id == "tx-demo")
    ).one()
    assert untouched.transaction_date == stale

    login = client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert login.status_code == 200
    session.expire_all()
    shifted = session.exec(
        select(Transaction).where(Transaction.pluggy_transaction_id == "tx-demo")
    ).one()
    assert shifted.transaction_date != stale
    assert shifted.transaction_date.month == date.today().month


def test_maybe_refresh_ignores_non_demo_users(session: Session) -> None:
    user = User(email="knight@goldqueen.dev", display_name="Knight", password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)

    stale = date.today().replace(day=1) - timedelta(days=10)
    _seed_transaction(session, user, stale)

    assert maybe_refresh_demo(session, user.email, require_id(user.id)) == 0
