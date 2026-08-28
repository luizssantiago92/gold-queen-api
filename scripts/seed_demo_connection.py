"""Populate a demo account with a Pluggy sandbox bank connection.

The deployed demo starts with no bank linked, so every dashboard card renders its
empty state and the portfolio shows nothing of what the project actually does.
Linking a bank normally requires the Pluggy Connect widget, which needs a human
in a browser; this script performs the same steps server-to-server instead.

    python -m scripts.seed_demo_connection --api https://gold-queen-api.onrender.com

Credentials come from the environment (see .env.example). Pluggy must be
configured, otherwise the API runs against its offline simulator and there is no
real item to sync.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

import httpx

from app.core.config import get_settings

# Documented Pluggy sandbox login. Any other value makes the item fail on purpose,
# which is how the sandbox lets you exercise error states.
SANDBOX_USER = "user-ok"
SANDBOX_PASSWORD = "password-ok"

# An item is created asynchronously: it lands in UPDATING and only exposes
# accounts once it reaches UPDATED.
POLL_ATTEMPTS = 40
POLL_INTERVAL_S = 3.0
TERMINAL_FAILURES = {"LOGIN_ERROR", "OUTDATED", "ERROR"}


class SeedError(RuntimeError):
    pass


async def _pluggy_api_key(client: httpx.AsyncClient, base_url: str) -> str:
    settings = get_settings()
    if not settings.pluggy_enabled:
        raise SeedError(
            "Pluggy credentials are missing; set PLUGGY_CLIENT_ID and "
            "PLUGGY_CLIENT_SECRET before seeding."
        )

    response = await client.post(
        f"{base_url}/auth",
        json={
            "clientId": settings.pluggy_client_id,
            "clientSecret": settings.pluggy_client_secret,
        },
    )
    if response.status_code >= 400:
        raise SeedError(f"Pluggy authentication failed: {response.text}")
    return response.json()["apiKey"]


async def _pick_sandbox_connector(
    client: httpx.AsyncClient, base_url: str, api_key: str
) -> dict[str, Any]:
    response = await client.get(
        f"{base_url}/connectors",
        headers={"X-API-KEY": api_key},
        params={"sandbox": "true"},
    )
    if response.status_code >= 400:
        raise SeedError(f"Could not list connectors: {response.text}")

    connectors = response.json().get("results", [])
    if not connectors:
        raise SeedError("Pluggy returned no sandbox connectors.")

    # Trial accounts may only create items for "Pluggy Bank"; every other sandbox
    # connector is rejected with TRIAL_CLIENT_ITEM_CREATE_NOT_ALLOWED.
    for connector in connectors:
        if connector.get("name", "").strip().lower() == "pluggy bank":
            return connector

    raise SeedError(
        "The 'Pluggy Bank' sandbox connector was not found. Available: "
        + ", ".join(sorted(c.get("name", "?") for c in connectors))
    )


async def _create_item(
    client: httpx.AsyncClient, base_url: str, api_key: str, connector: dict[str, Any]
) -> str:
    response = await client.post(
        f"{base_url}/items",
        headers={"X-API-KEY": api_key},
        json={
            "connectorId": connector["id"],
            "parameters": {"user": SANDBOX_USER, "password": SANDBOX_PASSWORD},
        },
    )
    if response.status_code >= 400:
        raise SeedError(f"Could not create the sandbox item: {response.text}")
    return response.json()["id"]


async def _await_item(
    client: httpx.AsyncClient, base_url: str, api_key: str, item_id: str
) -> None:
    for attempt in range(1, POLL_ATTEMPTS + 1):
        response = await client.get(
            f"{base_url}/items/{item_id}", headers={"X-API-KEY": api_key}
        )
        if response.status_code >= 400:
            raise SeedError(f"Could not read the item: {response.text}")

        status = response.json().get("status", "")
        print(f"  item {item_id}: {status} ({attempt}/{POLL_ATTEMPTS})")

        if status == "UPDATED":
            return
        if status in TERMINAL_FAILURES:
            raise SeedError(f"Item finished in a failed state: {status}")

        await asyncio.sleep(POLL_INTERVAL_S)

    raise SeedError("Timed out waiting for the item to finish updating.")


async def _sync_into_api(
    client: httpx.AsyncClient,
    api_url: str,
    email: str,
    password: str,
    item_id: str,
    institution_name: str,
) -> dict[str, Any]:
    login = await client.post(
        f"{api_url}/v1/auth/login", json={"email": email, "password": password}
    )
    if login.status_code >= 400:
        raise SeedError(f"Demo login failed: {login.text}")

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Enforces the free-plan quota before anything is written.
    quota = await client.post(f"{api_url}/v1/connections/connect", headers=headers)
    if quota.status_code >= 400:
        raise SeedError(f"Connection quota rejected the request: {quota.text}")

    # Categorization runs through Gemini one batch at a time, so this is slow.
    response = await client.post(
        f"{api_url}/v1/connections/sync",
        headers=headers,
        json={"item_id": item_id, "institution_name": institution_name},
        timeout=300.0,
    )
    if response.status_code >= 400:
        raise SeedError(f"Sync failed: {response.text}")
    return response.json()


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Target API URL")
    parser.add_argument("--email", default="queen@goldqueen.dev")
    parser.add_argument("--password", default="QueenDemo123!")
    args = parser.parse_args()

    api_url = args.api.rstrip("/")
    pluggy_url = get_settings().pluggy_base_url

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Authenticating against Pluggy...")
        api_key = await _pluggy_api_key(client, pluggy_url)

        connector = await _pick_sandbox_connector(client, pluggy_url, api_key)
        name = connector.get("name", "Sandbox Bank")
        print(f"Using sandbox connector: {name} (id {connector['id']})")

        item_id = await _create_item(client, pluggy_url, api_key, connector)
        print("Waiting for the sandbox item to finish updating...")
        await _await_item(client, pluggy_url, api_key, item_id)

        print(f"Syncing into {api_url} ...")
        result = await _sync_into_api(
            client, api_url, args.email, args.password, item_id, name
        )

    print(
        "Done: "
        f"{result['accounts_synced']} accounts, "
        f"{result['transactions_synced']} transactions, "
        f"{result['transactions_categorized']} categorized, "
        f"guarded={result['guarded']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except SeedError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
