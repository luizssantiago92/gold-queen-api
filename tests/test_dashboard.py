"""Dashboard aggregation tests (RF03)."""

import re
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session

from app.models.entities import Account, BankConnection, Transaction, require_id
from app.services.treasury import (
    build_ai_summary,
    daily_cumulative_expenses,
    expenses_by_category,
    is_card_bill_settlement,
    month_totals,
)


def test_card_bill_payment_is_left_out_of_expenses(
    auth_client: TestClient, session: Session
) -> None:
    user_id = auth_client.get("/v1/auth/me").json()["id"]
    today = date.today()
    connection = BankConnection(
        user_id=user_id,
        pluggy_item_id="item-card-bill",
        institution_name="Pluggy Bank",
        status="UPDATED",
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    connection_id = require_id(connection.id)
    bank = Account(
        connection_id=connection_id,
        pluggy_account_id="acc-checking",
        name="Checking",
        account_type="BANK",
        balance=Decimal("1000.00"),
    )
    card = Account(
        connection_id=connection_id,
        pluggy_account_id="acc-black",
        name="Mastercard Black",
        account_type="CREDIT",
        balance=Decimal("-167.70"),
    )
    session.add(bank)
    session.add(card)
    session.commit()
    session.refresh(bank)
    session.refresh(card)
    bank_id = require_id(bank.id)
    card_id = require_id(card.id)
    purchases = (
        ("tx-netflix", "NETFLIX.COM", Decimal("-100.00")),
        ("tx-gym", "SMART FIT ACADEMIA", Decimal("-67.70")),
    )
    for pluggy_id, description, amount in purchases:
        session.add(
            Transaction(
                account_id=card_id,
                pluggy_transaction_id=pluggy_id,
                description=description,
                amount=amount,
                transaction_date=today,
            )
        )
    session.add(
        Transaction(
            account_id=bank_id,
            pluggy_transaction_id="tx-bill",
            description="PAGAMENTO FATURA CARTAO VISA",
            amount=Decimal("-167.70"),
            transaction_date=today,
        )
    )
    session.commit()

    expenses, income = month_totals(session, user_id)
    assert expenses == Decimal("167.70")
    assert income == Decimal("0.00")

    categories = expenses_by_category(session, user_id)
    assert sum((total for total, _ in categories.values()), Decimal("0")) == Decimal(
        "167.70"
    )
    assert categories["CreditCard"] == (Decimal("167.70"), 2)

    series = daily_cumulative_expenses(session, user_id, today)
    assert series[-1] == (today, Decimal("167.70"))

    summary = build_ai_summary(session, user_id)
    assert "Month expenses: R$ 167.70" in summary

    overview = auth_client.get("/v1/dashboard/overview").json()
    assert overview["month_expenses"] == "167.70"
    series_body = auth_client.get("/v1/dashboard/monthly-series").json()
    assert series_body["total_expenses"] == "167.70"
    feed = auth_client.get("/v1/dashboard/transactions?limit=20").json()
    descriptions = [item["description"] for item in feed["items"]]
    assert "PAGAMENTO FATURA CARTAO VISA" in descriptions
    assert feed["total"] == 3


def test_bill_settlement_keeps_credit_purchases() -> None:
    today = date.today()
    bank = Account(
        connection_id=1,
        pluggy_account_id="bank",
        name="Checking",
        account_type="BANK",
    )
    card = Account(
        connection_id=1,
        pluggy_account_id="card",
        name="Mastercard Black",
        account_type="CREDIT",
    )
    payment = Transaction(
        account_id=1,
        pluggy_transaction_id="bill",
        description="PAGAMENTO FATURA CARTAO VISA",
        amount=Decimal("-167.70"),
        transaction_date=today,
    )
    visa_purchase = Transaction(
        account_id=2,
        pluggy_transaction_id="visa",
        description="COMPRA VISA LOJA",
        amount=Decimal("-40.00"),
        transaction_date=today,
    )
    card_fatura = Transaction(
        account_id=2,
        pluggy_transaction_id="card-bill",
        description="PAGAMENTO FATURA",
        amount=Decimal("-10.00"),
        transaction_date=today,
    )
    visa_on_bank = Transaction(
        account_id=1,
        pluggy_transaction_id="visa-bank",
        description="COMPRA VISA LOJA",
        amount=Decimal("-40.00"),
        transaction_date=today,
    )
    incoming = Transaction(
        account_id=1,
        pluggy_transaction_id="incoming-bill",
        description="PAGAMENTO FATURA",
        amount=Decimal("167.70"),
        transaction_date=today,
    )
    assert is_card_bill_settlement(payment, bank)
    assert not is_card_bill_settlement(visa_purchase, card)
    assert not is_card_bill_settlement(card_fatura, card)
    assert not is_card_bill_settlement(visa_on_bank, bank)
    assert not is_card_bill_settlement(incoming, bank)


def test_overview_is_empty_before_any_sync(auth_client: TestClient) -> None:
    body = auth_client.get("/v1/dashboard/overview").json()
    assert body["total_balance"] == "0.00"
    assert body["banks"] == []


def test_overview_consolidates_connected_banks(auth_client: TestClient) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "22222222-2222-4222-8222-222222222222"}
    )

    body = auth_client.get("/v1/dashboard/overview").json()
    assert len(body["banks"]) == 2
    assert float(body["total_balance"]) > 0

    total_share = sum(bank["share_percentage"] for bank in body["banks"])
    assert 99.0 <= total_share <= 101.0


def test_overview_reports_income_and_expenses(auth_client: TestClient) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    body = auth_client.get("/v1/dashboard/overview").json()
    assert float(body["month_income"]) > 0
    assert float(body["month_expenses"]) > 0


def test_categories_breakdown_sums_to_one_hundred(auth_client: TestClient) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    body = auth_client.get("/v1/dashboard/categories").json()
    assert body["categories"]

    total_share = sum(item["share_percentage"] for item in body["categories"])
    assert 99.0 <= total_share <= 101.0


def test_monthly_series_is_flat_at_zero_before_any_sync(
    auth_client: TestClient,
) -> None:
    body = auth_client.get("/v1/dashboard/monthly-series").json()

    assert len(body["points"]) == date.today().day
    assert body["total_expenses"] == "0.00"
    assert {point["cumulative_expenses"] for point in body["points"]} == {"0.00"}


def test_monthly_series_never_decreases_and_ends_on_the_month_total(
    auth_client: TestClient,
) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    body = auth_client.get("/v1/dashboard/monthly-series").json()
    amounts = [float(point["cumulative_expenses"]) for point in body["points"]]

    assert amounts == sorted(amounts)
    assert amounts[-1] > 0
    assert body["total_expenses"] == body["points"][-1]["cumulative_expenses"]

    overview = auth_client.get("/v1/dashboard/overview").json()
    assert body["total_expenses"] == overview["month_expenses"]


def test_monthly_series_covers_the_month_day_by_day(auth_client: TestClient) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    body = auth_client.get("/v1/dashboard/monthly-series").json()
    today = date.today()

    assert body["reference_month"] == today.strftime("%Y-%m")
    assert body["points"][0]["date"] == today.replace(day=1).isoformat()
    assert body["points"][-1]["date"] == today.isoformat()


def test_monthly_series_requires_authentication(client: TestClient) -> None:
    assert client.get("/v1/dashboard/monthly-series").status_code == 401


def test_transactions_are_paginated_and_carry_guardrail_flag(
    auth_client: TestClient,
) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    body = auth_client.get("/v1/dashboard/transactions?page=1&limit=5").json()
    assert len(body["items"]) <= 5
    assert body["total"] >= len(body["items"])

    first = body["items"][0]
    assert "is_guarded" in first
    assert first["institution_name"]


def test_transaction_pages_use_sql_offset_and_count(
    auth_client: TestClient, session: Session
) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )
    statements: list[str] = []

    def _capture(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(session.get_bind(), "before_cursor_execute", _capture)
    try:
        body = auth_client.get("/v1/dashboard/transactions?page=2&limit=5").json()
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", _capture)

    rendered = "\n".join(statements).lower()
    assert "limit" in rendered
    assert "offset" in rendered
    assert "count" in rendered
    assert body["page"] == 2
    assert body["limit"] == 5
    assert body["total"] >= len(body["items"])
    assert isinstance(body["items"], list)


def test_transaction_created_at_includes_a_timezone_offset(
    auth_client: TestClient,
) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )
    listing = auth_client.get("/v1/dashboard/transactions?page=1&limit=1").json()
    transaction_id = listing["items"][0]["id"]
    created_at = auth_client.get(f"/v1/dashboard/transactions/{transaction_id}").json()[
        "created_at"
    ]
    assert re.search(r"(Z|[+-]\d{2}:\d{2})$", created_at)


def test_transactions_second_page_differs(auth_client: TestClient) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    page_one = auth_client.get("/v1/dashboard/transactions?page=1&limit=5").json()
    page_two = auth_client.get("/v1/dashboard/transactions?page=2&limit=5").json()

    ids_one = {item["id"] for item in page_one["items"]}
    ids_two = {item["id"] for item in page_two["items"]}
    assert not ids_one & ids_two


def test_transaction_detail_returns_extended_fields(auth_client: TestClient) -> None:
    auth_client.post(
        "/v1/connections/sync", json={"item_id": "11111111-1111-4111-8111-111111111111"}
    )

    listing = auth_client.get("/v1/dashboard/transactions?page=1&limit=1").json()
    transaction_id = listing["items"][0]["id"]

    body = auth_client.get(f"/v1/dashboard/transactions/{transaction_id}").json()
    assert body["id"] == transaction_id
    assert body["display_category"]
    assert body["account_name"]
    assert body["account_type"]
    assert body["created_at"]
