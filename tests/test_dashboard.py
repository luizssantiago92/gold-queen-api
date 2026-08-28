"""Dashboard aggregation tests (RF03)."""

from datetime import date

from fastapi.testclient import TestClient


def test_overview_is_empty_before_any_sync(auth_client: TestClient) -> None:
    body = auth_client.get("/v1/dashboard/overview").json()
    assert body["total_balance"] == "0.00"
    assert body["banks"] == []


def test_overview_consolidates_connected_banks(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})
    auth_client.post("/v1/connections/sync", json={"item_id": "item-omega"})

    body = auth_client.get("/v1/dashboard/overview").json()
    assert len(body["banks"]) == 2
    assert float(body["total_balance"]) > 0

    total_share = sum(bank["share_percentage"] for bank in body["banks"])
    assert 99.0 <= total_share <= 101.0


def test_overview_reports_income_and_expenses(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

    body = auth_client.get("/v1/dashboard/overview").json()
    assert float(body["month_income"]) > 0
    assert float(body["month_expenses"]) > 0


def test_categories_breakdown_sums_to_one_hundred(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

    body = auth_client.get("/v1/dashboard/categories").json()
    assert body["categories"]

    total_share = sum(item["share_percentage"] for item in body["categories"])
    assert 99.0 <= total_share <= 101.0


def test_monthly_series_is_flat_at_zero_before_any_sync(auth_client: TestClient) -> None:
    body = auth_client.get("/v1/dashboard/monthly-series").json()

    assert len(body["points"]) == date.today().day
    assert body["total_expenses"] == "0.00"
    assert {point["cumulative_expenses"] for point in body["points"]} == {"0.00"}


def test_monthly_series_never_decreases_and_ends_on_the_month_total(
    auth_client: TestClient,
) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

    body = auth_client.get("/v1/dashboard/monthly-series").json()
    amounts = [float(point["cumulative_expenses"]) for point in body["points"]]

    assert amounts == sorted(amounts)
    assert amounts[-1] > 0
    assert body["total_expenses"] == body["points"][-1]["cumulative_expenses"]

    overview = auth_client.get("/v1/dashboard/overview").json()
    assert body["total_expenses"] == overview["month_expenses"]


def test_monthly_series_covers_the_month_day_by_day(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

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
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

    body = auth_client.get("/v1/dashboard/transactions?page=1&limit=5").json()
    assert len(body["items"]) <= 5
    assert body["total"] >= len(body["items"])

    first = body["items"][0]
    assert "is_guarded" in first
    assert first["institution_name"]


def test_transactions_second_page_differs(auth_client: TestClient) -> None:
    auth_client.post("/v1/connections/sync", json={"item_id": "item-alpha"})

    page_one = auth_client.get("/v1/dashboard/transactions?page=1&limit=5").json()
    page_two = auth_client.get("/v1/dashboard/transactions?page=2&limit=5").json()

    ids_one = {item["id"] for item in page_one["items"]}
    ids_two = {item["id"] for item in page_two["items"]}
    assert not ids_one & ids_two
