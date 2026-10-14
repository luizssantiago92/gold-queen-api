"""Transactions placed in the Queen and Queen's Tips prompts.

The rows returned here are the same rows named under "Transactions used" in
the prompt. A bank card-bill settlement is left out, matching the expense
totals. At most ``SOURCE_LIMIT`` rows are included.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.models.entities import Account, Transaction, require_id
from app.services.treasury import (
    display_category_for,
    is_card_bill_settlement,
    month_bounds,
    user_transaction_rows,
)

SOURCE_LIMIT = 20

# Questions that name a count of largest expenses, after accent folding.
_LARGEST_EXPENSE = re.compile(
    r"maior(?:es)? (?:gasto|despesa)s?"
    r"|maiores transac"
    r"|largest expenses?"
    r"|biggest expenses?"
    r"|largest transactions?"
    r"|biggest transactions?"
)
_COUNT = re.compile(r"\b(\d{1,2})\b")
_TOKEN = re.compile(r"[a-z0-9]{4,}")

# Words that show up in treasury questions and would otherwise match nothing
# useful, or match almost every row.
_GENERIC_TOKENS = frozenset(
    {
        "about",
        "com",
        "como",
        "conta",
        "contas",
        "despesa",
        "despesas",
        "expense",
        "expenses",
        "gastei",
        "gasto",
        "gastos",
        "maior",
        "maiores",
        "meu",
        "minha",
        "minhas",
        "month",
        "para",
        "qual",
        "quais",
        "this",
        "transacao",
        "transacoes",
        "transaction",
        "transactions",
        "what",
        "with",
    }
)


@dataclass(frozen=True)
class GroundedTransaction:
    id: int
    date: date
    description: str
    amount: Decimal
    category: str
    account: str


def fold_text(text: str) -> str:
    """Casefold and strip accents so `transações` and `transacoes` match."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return without_marks.casefold()


def select_grounding_sources(
    session: Session,
    user_id: int,
    question: str | None = None,
) -> list[GroundedTransaction]:
    """Return the current-month rows that ground this answer.

    A largest-expense question returns that many expenses, biggest first.
    A question that names a merchant, category, or account returns those
    rows. Any other treasury question returns the movements behind the month
    totals, largest absolute amount first. Card-bill settlements are omitted
    in every case.
    """
    start, end = month_bounds()
    candidates: list[GroundedTransaction] = []
    for transaction, account, _connection in user_transaction_rows(
        session, user_id, start, end
    ):
        if is_card_bill_settlement(transaction, account):
            continue
        candidates.append(_to_source(transaction, account))

    if question is not None and asks_for_largest_expense(question):
        count = _requested_count(question)
        expenses = [row for row in candidates if row.amount < 0]
        expenses.sort(key=_expense_rank)
        return expenses[:count]

    if question is not None:
        matched = _matching(candidates, question)
        if matched:
            return matched[:SOURCE_LIMIT]

    ranked = sorted(candidates, key=_amount_rank)
    return ranked[:SOURCE_LIMIT]


def largest_expense_answer(sources: list[GroundedTransaction], locale: str) -> str:
    """Name the selected expenses without calling the model.

    A largest-expense question is already decided by these rows. Waiting on
    the provider is what turned a 30 second timeout, retried three times,
    into a generic unavailable reply.
    """
    if not sources:
        if locale == "pt":
            return "Não há gasto registrado neste mês."
        return "There is no expense recorded this month."
    if len(sources) == 1:
        row = sources[0]
        money = _money(row.amount)
        if locale == "pt":
            return (
                "O maior gasto deste mês foi "
                f"{row.description}, {money}, na conta {row.account}."
            )
        return (
            "The largest expense this month was "
            f"{row.description}, {money}, on account {row.account}."
        )
    listed = "; ".join(
        f"{row.description}, {_money(row.amount)}, {row.account}" for row in sources
    )
    if locale == "pt":
        return f"Os {len(sources)} maiores gastos deste mês foram: {listed}."
    return f"The {len(sources)} largest expenses this month were: {listed}."


def _money(amount: Decimal) -> str:
    return f"R$ {abs(amount):.2f}"


def format_grounding_block(sources: list[GroundedTransaction]) -> str:
    """Render the prompt section that lists exactly ``sources``."""
    if not sources:
        return "Transactions used:\n- none"
    lines = [
        (
            f"- id={item.id} date={item.date.isoformat()} "
            f'description="{_quote(item.description)}" '
            f"amount={item.amount} category={item.category} "
            f'account="{_quote(item.account)}"'
        )
        for item in sources
    ]
    return "Transactions used:\n" + "\n".join(lines)


def _to_source(transaction: Transaction, account: Account) -> GroundedTransaction:
    return GroundedTransaction(
        id=require_id(transaction.id),
        date=transaction.transaction_date,
        description=transaction.description,
        amount=transaction.amount.quantize(Decimal("0.01")),
        category=display_category_for(transaction, account),
        account=account.name,
    )


def asks_for_largest_expense(question: str) -> bool:
    """True when the question asks for the largest expense or expenses."""
    return _LARGEST_EXPENSE.search(fold_text(question)) is not None


def _requested_count(question: str) -> int:
    match = _COUNT.search(fold_text(question))
    if match is None:
        return 1
    return min(SOURCE_LIMIT, max(1, int(match.group(1))))


def _expense_rank(row: GroundedTransaction) -> tuple[Decimal, int, int]:
    return (row.amount, -row.date.toordinal(), -row.id)


def _amount_rank(row: GroundedTransaction) -> tuple[Decimal, int, int]:
    return (-abs(row.amount), -row.date.toordinal(), -row.id)


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(fold_text(text)))


def _matching(
    rows: list[GroundedTransaction], question: str
) -> list[GroundedTransaction]:
    needles = _tokens(question) - _GENERIC_TOKENS
    if not needles:
        return []
    scored: list[tuple[int, Decimal, GroundedTransaction]] = []
    for row in rows:
        haystack = _tokens(f"{row.description} {row.category} {row.account}")
        overlap = needles & haystack
        if overlap:
            scored.append((len(overlap), abs(row.amount), row))
    scored.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            -item[2].date.toordinal(),
            -item[2].id,
        )
    )
    return [item[2] for item in scored]


def _quote(value: str) -> str:
    return value.replace('"', "'")
