"""Pluggy Open Finance client (Sandbox).

Flow implemented here:
1. ``POST /auth`` with CLIENT_ID/CLIENT_SECRET to obtain a 2h API key.
2. ``POST /connect_token`` to hand a 30 min scoped token to the frontend widget.
3. ``GET /accounts`` and ``GET /v2/transactions`` to sync the connected item.
   The v1 transactions endpoint was retired and now answers 410, so the newer
   cursor-paginated one is the only option.

When credentials are absent the client switches to a deterministic sandbox
simulator so the API stays fully demoable offline (portfolio friendly).
"""

import hashlib
import logging
import random
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamError

logger = logging.getLogger(__name__)

# Keys Pluggy (or a proxy in front of it) may echo back. The client sees a
# generic message; the log keeps the status and a redacted body.
_JSON_SECRET = re.compile(
    r'(?i)("(?:api[_-]?key|client[_-]?secret|access[_-]?token|authorization|password|secret)"\s*:\s*)"(?:[^"\\]|\\.)*"'
)
_ASSIGNMENT_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token|authorization|password|secret)\b(\s*[:=]\s*)\S+"
)
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")
_LOG_BODY_LIMIT = 500

_API_KEY_TTL = timedelta(hours=1, minutes=45)

_MAX_TRANSACTION_PAGES = 50

_SANDBOX_INSTITUTIONS = ("Banco Itau", "Nubank", "Bradesco")
_SANDBOX_MERCHANTS = (
    "Padaria do Reino",
    "Taberna do Dragao",
    "Carruagem Express",
    "Aluguel do Castelo",
    "Boticario Real",
    "Academia de Cavaleiros",
    "Teatro do Bardo",
    "Loja de Sedas",
    "Taxas do Reino",
)

_SANDBOX_SALARY = "Soldo Real"


def _canonical_item_id(item_id: UUID | str) -> str:
    """Return the canonical UUID text.

    ``str(UUID(...))`` is only hex and hyphens, so it cannot rewrite the
    request path the way ``../webhooks`` would.
    """
    return str(UUID(str(item_id)))


def _item_url(base_url: str, item_id: UUID | str) -> str:
    return f"{base_url.rstrip('/')}/items/{_canonical_item_id(item_id)}"


def _redact_upstream_body(body: str) -> str:
    redacted = _JSON_SECRET.sub(r'\1"[redacted]"', body)
    redacted = _ASSIGNMENT_SECRET.sub(r"\1\2[redacted]", redacted)
    redacted = _BEARER.sub("Bearer [redacted]", redacted)
    if len(redacted) > _LOG_BODY_LIMIT:
        return redacted[:_LOG_BODY_LIMIT] + "..."
    return redacted


def _fail_upstream(operation: str, response: httpx.Response) -> None:
    """Log the upstream failure without secrets and raise a generic error."""
    logger.warning(
        "Pluggy %s failed with status %s: %s",
        operation,
        response.status_code,
        _redact_upstream_body(response.text),
    )
    raise UpstreamError(f"Pluggy {operation} failed.")


class PluggyAccount:
    def __init__(
        self,
        account_id: str,
        name: str,
        balance: Decimal,
        currency: str,
        account_type: str,
    ):
        self.account_id = account_id
        self.name = name
        self.balance = balance
        self.currency = currency
        self.account_type = account_type


class PluggyTransaction:
    def __init__(
        self,
        transaction_id: str,
        description: str,
        amount: Decimal,
        transaction_date: date,
    ):
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
        if (
            self._api_key
            and self._api_key_expires_at
            and now < self._api_key_expires_at
        ):
            return self._api_key

        response = await client.post(
            f"{self._settings.pluggy_base_url}/auth",
            json={
                "clientId": self._settings.pluggy_client_id,
                "clientSecret": self._settings.pluggy_client_secret,
            },
        )
        if response.status_code >= 400:
            _fail_upstream("authentication", response)

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
                _fail_upstream("connect token", response)
            return response.json()["accessToken"]

    async def fetch_item(self, item_id: UUID) -> dict[str, Any]:
        item_ref = _canonical_item_id(item_id)
        if not self.enabled:
            return {
                "id": item_ref,
                "connector": {"name": _simulated_institution(item_ref)},
                "status": "UPDATED",
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            api_key = await self._authenticate(client)
            response = await client.get(
                _item_url(self._settings.pluggy_base_url, item_ref),
                headers={"X-API-KEY": api_key},
            )
            if response.status_code >= 400:
                _fail_upstream("item fetch", response)
            return response.json()

    async def fetch_accounts(self, item_id: UUID) -> list[PluggyAccount]:
        item_ref = _canonical_item_id(item_id)
        if not self.enabled:
            return _simulated_accounts(item_ref)

        async with httpx.AsyncClient(timeout=30.0) as client:
            api_key = await self._authenticate(client)
            response = await client.get(
                f"{self._settings.pluggy_base_url}/accounts",
                headers={"X-API-KEY": api_key},
                params={"itemId": item_ref},
            )
            if response.status_code >= 400:
                _fail_upstream("accounts fetch", response)

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

        transactions: list[PluggyTransaction] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            api_key = await self._authenticate(client)
            headers = {"X-API-KEY": api_key}
            url = f"{self._settings.pluggy_base_url}/v2/transactions"
            # v2 accepts accountId only; it rejects pageSize and limit outright.
            params: dict[str, Any] | None = {"accountId": account_id}

            # The bound stops a malformed cursor from looping forever; it is far
            # above what a demo account holds.
            for _ in range(_MAX_TRANSACTION_PAGES):
                response = await client.get(url, headers=headers, params=params)
                if response.status_code >= 400:
                    _fail_upstream("transactions fetch", response)

                payload = response.json()
                for item in payload.get("results", []):
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

                # Pagination arrives as "next": an absolute URL to the following
                # page, already carrying the cursor, or null on the last page.
                next_page = payload.get("next")
                if not next_page:
                    break
                url, params = str(next_page), None

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
    first_day = today.replace(day=1)

    # One guaranteed salary credit so the demo always shows income against expenses.
    transactions: list[PluggyTransaction] = [
        PluggyTransaction(
            transaction_id=f"{account_id}-tx-salary",
            description=_SANDBOX_SALARY,
            amount=Decimal(rng.randrange(400_000, 700_000)) / Decimal(100),
            transaction_date=first_day,
        )
    ]

    max_days_back = (today - first_day).days
    for index in range(rng.randrange(12, 20)):
        merchant = _SANDBOX_MERCHANTS[rng.randrange(len(_SANDBOX_MERCHANTS))]
        amount = Decimal(rng.randrange(1_500, 90_000)) / Decimal(100)
        transactions.append(
            PluggyTransaction(
                transaction_id=f"{account_id}-tx-{index}",
                description=merchant,
                amount=-amount,
                transaction_date=today
                - timedelta(days=rng.randrange(0, max_days_back + 1)),
            )
        )
    return transactions


def get_pluggy_client() -> PluggyClient:
    return PluggyClient()
