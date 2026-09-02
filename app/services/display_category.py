"""Portfolio-friendly spending buckets derived from description and account type.

The AI still stores the closed vocabulary in ``transaction.category``; this layer
maps rows into labels users expect on a fintech dashboard (subscriptions, bills,
credit-card payments, and so on) without re-running Gemini.
"""

from __future__ import annotations

import re
from decimal import Decimal

DISPLAY_CATEGORIES = (
    "Subscriptions",
    "Bills",
    "AutoDebit",
    "CreditCard",
    "Food",
    "Housing",
    "Transport",
    "Health",
    "Shopping",
    "Income",
    "Transfer",
    "Other",
)

_SUBSCRIPTION = re.compile(
    r"spotify|netflix|amazon prime|disney|hbo|apple\.com|google storage|assinatura",
    re.I,
)
_BILLS = re.compile(
    r"boleto|energia|eletrobras|light|vivo|tim|claro|oi |sabesp|copel|cemig|água|agua",
    re.I,
)
_AUTO_DEBIT = re.compile(r"debito automatico|débito automático|da convenio|convênio", re.I)
_CREDIT_CARD = re.compile(
    r"fatura|cartao|cartão|visa|mastercard|nubank.*card|pagamento fat",
    re.I,
)
_FOOD = re.compile(r"padaria|restaurante|ifood|uber eats|rappi|mercado|supermerc", re.I)
_HOUSING = re.compile(r"condominio|condomínio|aluguel|iptu", re.I)
_TRANSPORT = re.compile(r"uber|99app|posto|combust|estacion", re.I)
_HEALTH = re.compile(r"farmacia|farmácia|academia|smart fit|hospital|clinica", re.I)
_SHOPPING = re.compile(r"magazine|mercadoria|loja|shop|amazon(?! prime)", re.I)
_TRANSFER = re.compile(r"pix|ted |doc |transferencia|transferência", re.I)


def classify_display(
    description: str,
    amount: Decimal,
    *,
    account_type: str = "BANK",
    ai_category: str = "Other",
) -> str:
    text = description.strip()
    if amount > 0:
        return "Income"

    if account_type.upper() in {"CREDIT", "CREDIT_CARD"} and amount < 0:
        return "CreditCard"

    for pattern, label in (
        (_SUBSCRIPTION, "Subscriptions"),
        (_BILLS, "Bills"),
        (_AUTO_DEBIT, "AutoDebit"),
        (_CREDIT_CARD, "CreditCard"),
        (_FOOD, "Food"),
        (_HOUSING, "Housing"),
        (_TRANSPORT, "Transport"),
        (_HEALTH, "Health"),
        (_SHOPPING, "Shopping"),
        (_TRANSFER, "Transfer"),
    ):
        if pattern.search(text):
            return label

    # Fall back to the AI bucket when no keyword matched.
    mapping = {
        "Food": "Food",
        "Transport": "Transport",
        "Housing": "Housing",
        "Health": "Health",
        "Education": "Other",
        "Entertainment": "Subscriptions",
        "Shopping": "Shopping",
        "Bills": "Bills",
        "Income": "Income",
        "Transfer": "Transfer",
    }
    return mapping.get(ai_category, "Other")
