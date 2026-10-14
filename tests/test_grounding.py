"""Transaction sources returned with Queen answers (RF04, RF05)."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.ai_guardrails import QueenTips
from app.core.config import get_settings
from app.models.entities import Account, BankConnection, Transaction, require_id
from app.providers.base import Completion
from app.services.ai import AIEngine
from app.services.grounding import (
    SOURCE_LIMIT,
    GroundedTransaction,
    format_grounding_block,
    largest_expense_answer,
    select_grounding_sources,
)
from app.services.treasury import build_ai_summary


def _seed_card_bill(auth_client: TestClient, session: Session) -> None:
    user_id = auth_client.get("/v1/auth/me").json()["id"]
    today = date.today()
    connection = BankConnection(
        user_id=user_id,
        pluggy_item_id="item-sources",
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
    rows = (
        (card_id, "tx-netflix", "NETFLIX.COM", Decimal("-100.00")),
        (card_id, "tx-gym", "SMART FIT ACADEMIA", Decimal("-67.70")),
        (bank_id, "tx-bill", "PAGAMENTO FATURA CARTAO VISA", Decimal("-167.70")),
    )
    for account_id, pluggy_id, description, amount in rows:
        session.add(
            Transaction(
                account_id=account_id,
                pluggy_transaction_id=pluggy_id,
                description=description,
                amount=amount,
                transaction_date=today,
            )
        )
    session.commit()


def test_largest_expense_question_omits_the_card_bill(
    auth_client: TestClient, session: Session
) -> None:
    _seed_card_bill(auth_client, session)
    user_id = auth_client.get("/v1/auth/me").json()["id"]

    selected = select_grounding_sources(session, user_id, "Qual foi meu maior gasto?")
    assert len(selected) == 1
    assert selected[0].description == "NETFLIX.COM"
    assert selected[0].amount == Decimal("-100.00")
    assert selected[0].category == "CreditCard"
    assert selected[0].account == "Mastercard Black"
    assert format_grounding_block(selected) == (
        "Transactions used:\n"
        f"- id={selected[0].id} date={selected[0].date.isoformat()} "
        'description="NETFLIX.COM" '
        f"amount={selected[0].amount} category={selected[0].category} "
        f'account="{selected[0].account}"'
    )

    body = auth_client.post(
        "/v1/chat/query",
        json={"question": "Qual foi meu maior gasto?", "locale": "pt"},
    ).json()
    assert body["sources"] == [
        {
            "id": selected[0].id,
            "date": date.today().isoformat(),
            "description": "NETFLIX.COM",
            "amount": "-100.00",
            "category": "CreditCard",
            "account": "Mastercard Black",
        }
    ]
    assert body["answer"] == (
        "O maior gasto deste mês foi NETFLIX.COM, R$ 100.00, na conta Mastercard Black."
    )

    cached = auth_client.post(
        "/v1/chat/query",
        json={"question": "Qual foi meu maior gasto?", "locale": "pt"},
    ).json()
    assert cached["from_cache"] is True
    assert cached["sources"] == body["sources"]


def test_three_largest_expenses_keep_that_count(
    auth_client: TestClient, session: Session
) -> None:
    user_id = auth_client.get("/v1/auth/me").json()["id"]
    today = date.today()
    connection = BankConnection(
        user_id=user_id,
        pluggy_item_id="item-top",
        institution_name="Pluggy Bank",
        status="UPDATED",
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    account = Account(
        connection_id=require_id(connection.id),
        pluggy_account_id="acc-card",
        name="Card",
        account_type="CREDIT",
        balance=Decimal("0"),
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    account_id = require_id(account.id)
    for index, amount in enumerate(("10.00", "40.00", "30.00", "20.00"), start=1):
        session.add(
            Transaction(
                account_id=account_id,
                pluggy_transaction_id=f"tx-{index}",
                description=f"LOJA {index}",
                amount=Decimal(f"-{amount}"),
                transaction_date=today,
            )
        )
    session.commit()

    selected = select_grounding_sources(
        session, user_id, "Quais foram minhas 3 maiores transações?"
    )
    assert [row.amount for row in selected] == [
        Decimal("-40.00"),
        Decimal("-30.00"),
        Decimal("-20.00"),
    ]


def test_a_named_merchant_is_the_only_source(
    auth_client: TestClient, session: Session
) -> None:
    _seed_card_bill(auth_client, session)
    user_id = auth_client.get("/v1/auth/me").json()["id"]
    selected = select_grounding_sources(session, user_id, "Quanto gastei na Netflix?")
    assert [row.description for row in selected] == ["NETFLIX.COM"]


def test_general_question_uses_month_rows_except_the_bill_and_caps_them(
    auth_client: TestClient, session: Session
) -> None:
    user_id = auth_client.get("/v1/auth/me").json()["id"]
    today = date.today()
    connection = BankConnection(
        user_id=user_id,
        pluggy_item_id="item-cap",
        institution_name="Pluggy Bank",
        status="UPDATED",
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    account = Account(
        connection_id=require_id(connection.id),
        pluggy_account_id="acc-cap",
        name="Checking",
        account_type="BANK",
        balance=Decimal("0"),
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    account_id = require_id(account.id)
    for index in range(1, SOURCE_LIMIT + 2):
        session.add(
            Transaction(
                account_id=account_id,
                pluggy_transaction_id=f"tx-cap-{index}",
                description=f"MERCADORIA {index}",
                amount=Decimal(f"-{index}.00"),
                transaction_date=today,
            )
        )
    session.commit()

    selected = select_grounding_sources(session, user_id, "Como protejo meu ouro?")
    assert len(selected) == SOURCE_LIMIT
    assert selected[0].amount == Decimal(f"-{SOURCE_LIMIT + 1}.00")
    assert all(row.amount != Decimal("-1.00") for row in selected)

    generic = select_grounding_sources(session, user_id, "What about my expenses?")
    assert [row.id for row in generic] == [row.id for row in selected]


def test_queen_tips_sources_omit_the_card_bill(
    auth_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def guarded(
        self: AIEngine, summary: str, locale: str = "en"
    ) -> tuple[QueenTips, bool]:
        user_id = auth_client.get("/v1/auth/me").json()["id"]
        rows = select_grounding_sources(session, user_id)
        block = format_grounding_block(rows)
        expected = f"{build_ai_summary(session, user_id)}\n\n{block}"
        assert summary == expected
        assert [row.description for row in rows] == [
            "NETFLIX.COM",
            "SMART FIT ACADEMIA",
        ]
        return (
            QueenTips(
                critical_expense="Netflix",
                management_status="steady",
                smart_guidance="cut it",
            ),
            True,
        )

    monkeypatch.setattr(AIEngine, "queen_tips", guarded)
    _seed_card_bill(auth_client, session)
    body = auth_client.get("/v1/advisor/queen-tips").json()
    descriptions = [item["description"] for item in body["sources"]]
    assert descriptions == ["NETFLIX.COM", "SMART FIT ACADEMIA"]
    for item in body["sources"]:
        assert set(item) == {
            "id",
            "date",
            "description",
            "amount",
            "category",
            "account",
        }
        assert item["category"] == "CreditCard"
        assert item["account"] == "Mastercard Black"

    cached = auth_client.get("/v1/advisor/queen-tips").json()
    assert cached["from_cache"] is True
    assert cached["sources"] == body["sources"]


def test_off_topic_and_failed_model_return_no_sources(
    auth_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_card_bill(auth_client, session)
    refused = auth_client.post(
        "/v1/chat/query",
        json={"question": "Qual é a capital da França?"},
    ).json()
    assert refused["sources"] == []

    def broken(
        self: AIEngine, question: str, summary: str, locale: str = "en"
    ) -> tuple[str, bool]:
        return "A magia dos oraculos esta indisponivel.", False

    monkeypatch.setattr(AIEngine, "chat", broken)
    failed = auth_client.post(
        "/v1/chat/query",
        json={"question": "Como protejo meu ouro?"},
    ).json()
    assert failed["sources"] == []
    assert failed["from_cache"] is False


def test_enabled_chat_prompt_names_the_grounding_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    recorded: list[dict[str, str]] = []

    class _Recording:
        name = "recording"

        def complete(
            self,
            messages: list[dict[str, str]],
            temperature: float,
            max_tokens: int | None,
        ) -> Completion:
            recorded.extend(messages)
            return Completion(
                content="The leak is Netflix.", model="fake", provider=self.name
            )

        def health(self) -> bool:
            return True

    block = (
        "Transactions used:\n"
        '- id=12 date=2026-08-24 description="NETFLIX.COM" '
        'amount=-100.00 category=CreditCard account="Mastercard Black"'
    )
    question = "Qual foi meu maior gasto?"
    summary = f"Month expenses: R$ 100.00\n\n{block}"
    answer, answered = AIEngine(_Recording()).chat(question, summary, "pt")
    assert answered is True
    assert answer == "The leak is Netflix."
    assert recorded[-1]["content"] == (
        f"Treasury context:\n{summary}\n\n"
        "When you mention a movement, use only the transactions listed "
        "under Transactions used. Do not invent movements.\n\n"
        f"Subject's question: {question}"
    )


def test_largest_expense_does_not_call_the_model(
    auth_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(
        self: AIEngine, question: str, summary: str, locale: str = "en"
    ) -> tuple[str, bool]:
        raise AssertionError("largest expense must not call the model")

    monkeypatch.setattr(AIEngine, "chat", forbidden)
    _seed_card_bill(auth_client, session)
    body = auth_client.post(
        "/v1/chat/query",
        json={"question": "Qual foi meu maior gasto?", "locale": "pt"},
    ).json()
    assert body["answer"] == (
        "O maior gasto deste mês foi NETFLIX.COM, R$ 100.00, na conta Mastercard Black."
    )
    assert body["sources"][0]["description"] == "NETFLIX.COM"
    assert body["sources"][0]["amount"] == "-100.00"
    assert body["from_cache"] is False
    assert body["remaining_requests"] == get_settings().chat_daily_limit - 1

    cached = auth_client.post(
        "/v1/chat/query",
        json={"question": "Qual foi meu maior gasto?", "locale": "pt"},
    ).json()
    assert cached["from_cache"] is True
    assert cached["answer"] == body["answer"]
    assert cached["sources"] == body["sources"]
    assert cached["remaining_requests"] == body["remaining_requests"]


def test_largest_expense_without_rows_does_not_call_the_model(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(
        self: AIEngine, question: str, summary: str, locale: str = "en"
    ) -> tuple[str, bool]:
        raise AssertionError("largest expense must not call the model")

    monkeypatch.setattr(AIEngine, "chat", forbidden)
    body = auth_client.post(
        "/v1/chat/query",
        json={"question": "What was my biggest expense?", "locale": "en"},
    ).json()
    assert body["answer"] == "There is no expense recorded this month."
    assert body["sources"] == []


def test_other_treasury_questions_still_call_the_model(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def answer(
        self: AIEngine, question: str, summary: str, locale: str = "en"
    ) -> tuple[str, bool]:
        seen.append(question)
        return "Guard the gold.", True

    monkeypatch.setattr(AIEngine, "chat", answer)
    body = auth_client.post(
        "/v1/chat/query",
        json={"question": "Como protejo meu ouro?", "locale": "pt"},
    ).json()
    assert seen == ["Como protejo meu ouro?"]
    assert body["answer"] == "Guard the gold."


def test_three_largest_expenses_are_named_without_the_model() -> None:
    today = date.today()
    rows = [
        GroundedTransaction(1, today, "LOJA 2", Decimal("-40.00"), "Shopping", "Card"),
        GroundedTransaction(2, today, "LOJA 3", Decimal("-30.00"), "Shopping", "Card"),
        GroundedTransaction(3, today, "LOJA 4", Decimal("-20.00"), "Shopping", "Card"),
    ]
    assert largest_expense_answer(rows, "pt") == (
        "Os 3 maiores gastos deste mês foram: "
        "LOJA 2, R$ 40.00, Card; LOJA 3, R$ 30.00, Card; LOJA 4, R$ 20.00, Card."
    )
