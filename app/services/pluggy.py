"""Pluggy Open Finance client (Sandbox).

Flow implemented here:
1. ``POST /auth`` with CLIENT_ID/CLIENT_SECRET to obtain a 2h API key.
2. ``POST /connect_token`` to hand a 30 min scoped token to the frontend widget.
3. ``GET /accounts`` and ``GET /transactions`` to sync the connected item.

When credentials are absent the client switches to a deterministic sandbox
simulator so the API stays fully demoable offline (portfolio friendly).
"""

import hashlib
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamError

_API_KEY_TTL = timedelta(hours=1, minutes=45)

_SANDBOX_INSTITUTIONS = ("Banco Itau", "Nubank", "Bradesco")
_SANDBOX_MERCHANTS = (
    ("Padaria do Reino", "Food"),
    ("Taberna do Dragao", "Food"),
    ("Carruagem Express", "Transport"),
    ("Aluguel do Castelo", "Housing"),
    ("Boticario Real", "Health"),
    ("Academia de Cavaleiros", "Education"),
    ("Teatro do Bardo", "Entertainment"),
    ("Mercado de Sedas", "Shopping"),
    ("Taxas do Reino", "Bills"),
    ("Soldo Real", "Income"),
)


class PluggyAccount:
    def __init__(self, account_id: str, name: str, balance: Decimal, currency: str, account_type: str):
        self.account_id = account_id
        self.name = name
        self.balance = balance
        self.currency = currency
        self.account_type = account_type


class PluggyTransaction:
    def __init__(self, transaction_id: str, description: str, amount: Decimal, transaction_date: date):
        self.transaction_id = transaction_id
        self.description = description
        self.amount = amount
        self.transaction_date = transaction_date


class PluggyClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._api_key: str | None = None
        self._api_key_expires_at: datetime | None = None

    @property
    def enabled(self) -> bool:
        return self._settings.pluggy_enabled

    async def _authenticate(self, client: httpx.AsyncClient) -> str:
        now = datetime.now(UTC)
        if self._api_key and self._api_key_expires_at and now < self._api_key_expires_at:
            return self._api_key

        response = await client.post(
            f"{self._settings.pluggy_base_url}/auth",
            json={
                "clientId": self._settings.pluggy_client_id,
                "clientSecret": self._settings.pluggy_client_secret,
            },
        )
        if response.status_code >= 400:
            raise UpstreamError(f"Pluggy authentication failed: {response.text}")

        self._api_key = response.json()["apiKey"]
        self._api_key_expires_at = now + _API_KEY_TTL
        return self._api_key

    async def create_connect_token(self, client_user_id: str) -> str:
        """Return a 30 min token for the Pluggy Connect widget."""
        if not self.enabled:
            return _simulated_connect_token(client_user_id)

        async with httpx.AsyncClient(timeout=20.0) as client:
            api_key = await self._authenticate(client)
            response = await client.post(
                f"{self._settings.pluggy_base_url}/connect_token",
                headers={"X-API-KEY": api_key},
                json={"options": {"clientUserId": client_user_id}},
            )
            if response.status_code >= 400:
                raise UpstreamError(f"Pluggy connect token failed: {response.text}")
            return response.json()["accessToken"]

    async def fetch_item(self, item_id: str) -> dict[str, Any]:
        if not self.enabled:
            return {"id": item_id, "connector": {"name": _simulated_institution(item_id)}, "status": "UPDATED"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            api_key = await self._authenticate(client)
            response = await client.get(
                f"{self._settings.pluggy_base_url}/items/{item_id}",
                headers={"X-API-KEY": api_key},
            )
            if response.status_code >= 400:
                raise UpstreamError(f"Pluggy item fetch failed: {response.text}")
            return response.json()

    async def fetch_accounts(self, item_id: str) -> list[PluggyAccount]:
        if not self.enabled:
            return _simulated_accounts(item_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            api_key = await self._authenticate(client)
            response = await client.get(
                f"{self._settings.pluggy_base_url}/accounts",
                headers={"X-API-KEY": api_key},
                params={"itemId": item_id},
            )
            if response.status_code >= 400:
                raise UpstreamError(f"Pluggy accounts fetch failed: {response.text}")

            return [
                PluggyAccount(
                    account_id=item["id"],
                    name=item.get("name") or item.get("marketingName") or "Account",
                    balance=Decimal(str(item.get("balance", 0))),
                    currency=item.get("currencyCode", "BRL"),
                    account_type=item.get("type", "BANK"),
                )
                for item in response.json().get("results", [])
            ]

    async def fetch_transactions(self, account_id: str) -> list[PluggyTransaction]:
        if not self.enabled:
            return _simulated_transactions(account_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            api_key = await self._authenticate(client)
            response = await client.get(
                f"{self._settings.pluggy_base_url}/transactions",
                headers={"X-API-KEY": api_key},
                params={"accountId": account_id, "pageSize": 100},
            )
            if response.status_code >= 400:
                raise UpstreamError(f"Pluggy transactions fetch failed: {response.text}")

            transactions: list[PluggyTransaction] = []
            for item in response.json().get("results", []):
                raw_date = str(item.get("date", ""))[:10]
                try:
                    parsed_date = date.fromisoformat(raw_date)
                except ValueError:
                    parsed_date = date.today()
                transactions.append(
                    PluggyTransaction(
                        transaction_id=item["id"],
                        description=item.get("description") or "Transaction",
                        amount=Decimal(str(item.get("amount", 0))),
                        transaction_date=parsed_date,
                    )
                )
            return transactions


def _seed_for(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)


def _simulated_connect_token(client_user_id: str) -> str:
    digest = hashlib.sha256(f"{client_user_id}:{date.today()}".encode()).hexdigest()
    return f"sandbox-connect-token-{digest[:32]}"


def _simulated_institution(item_id: str) -> str:
    return _SANDBOX_INSTITUTIONS[_seed_for(item_id) % len(_SANDBOX_INSTITUTIONS)]


def _simulated_accounts(item_id: str) -> list[PluggyAccount]:
    rng = random.Random(_seed_for(item_id))
    institution = _simulated_institution(item_id)
    return [
        PluggyAccount(
            account_id=f"{item_id}-checking",
            name=f"{institution} Checking",
            balance=Decimal(rng.randrange(50_000, 400_000)) / Decimal(100),
            currency="BRL",
            account_type="BANK",
        )
    ]


def _simulated_transactions(account_id: str) -> list[PluggyTransaction]:
    rng = random.Random(_seed_for(account_id))
    today = date.today()
    transactions: list[PluggyTransaction] = []

    for index in range(rng.randrange(12, 20)):
        merchant, _category = _SANDBOX_MERCHANTS[rng.randrange(len(_SANDBOX_MERCHANTS))]
        is_income = merchant == "Soldo Real"
        cents = rng.randrange(1_500, 90_000) if not is_income else rng.randrange(200_000, 500_000)
        amount = Decimal(cents) / Decimal(100)
        transactions.append(
            PluggyTransaction(
                transaction_id=f"{account_id}-tx-{index}",
                description=merchant,
                amount=amount if is_income else -amount,
                transaction_date=today - timedelta(days=rng.randrange(0, 27)),
            )
        )
    return transactions


def get_pluggy_client() -> PluggyClient:
    return PluggyClient()
