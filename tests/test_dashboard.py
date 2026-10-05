"""Dashboard aggregation tests (RF03)."""

import re
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session


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
