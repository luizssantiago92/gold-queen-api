"""Tests for portfolio display-category bucketing."""

from decimal import Decimal

from app.services.display_category import classify_display


def test_positive_amounts_are_income() -> None:
    assert classify_display("PIX RECEBIDO", Decimal("100.00")) == "Income"


def test_subscription_keywords() -> None:
    assert (
        classify_display("SPOTIFY PREMIUM", Decimal("-21.90"), ai_category="Entertainment")
        == "Subscriptions"
    )


def test_bill_keywords() -> None:
    assert classify_display("BOLETO ENERGIA ELETROBRAS", Decimal("-180.00")) == "Bills"


def test_credit_card_account_type() -> None:
    assert (
        classify_display(
            "COMPRA LOJA",
            Decimal("-50.00"),
            account_type="CREDIT",
            ai_category="Shopping",
        )
        == "CreditCard"
    )


def test_falls_back_to_ai_category() -> None:
    assert classify_display("UNKNOWN MERCHANT", Decimal("-10.00"), ai_category="Food") == "Food"
