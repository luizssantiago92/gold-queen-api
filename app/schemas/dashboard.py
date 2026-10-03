"""Dashboard payloads (RF03)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BankBalance(BaseModel):
    connection_id: int
    institution_name: str
    balance: Decimal
    share_percentage: float


class OverviewResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total_balance": "2330.78",
                    "currency": "BRL",
                    "banks": [
                        {
                            "connection_id": 1,
                            "institution_name": "Nubank",
                            "balance": "1430.20",
                            "share_percentage": 61.36,
                        }
                    ],
                    "month_expenses": "845.10",
                    "month_income": "3200.00",
                    "reference_month": "2026-08",
                }
            ]
        }
    )

    total_balance: Decimal
    currency: str
    banks: list[BankBalance]
    month_expenses: Decimal
    month_income: Decimal
    reference_month: str


class CategoryBreakdown(BaseModel):
    category: str
    total: Decimal
    share_percentage: float
    transaction_count: int


class CategoriesResponse(BaseModel):
    reference_month: str
    total_expenses: Decimal
    categories: list[CategoryBreakdown]


class MonthlySeriesPoint(BaseModel):
    date: date
    cumulative_expenses: Decimal


class MonthlySeriesResponse(BaseModel):
    reference_month: str
    total_expenses: Decimal
    points: list[MonthlySeriesPoint]


class TransactionResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 12,
                    "description": "Padaria do Reino",
                    "amount": "-42.90",
                    "transaction_date": "2026-08-24",
                    "category": "Food",
                    "display_category": "Food",
                    "is_guarded": True,
                    "institution_name": "Pluggy Bank",
                    "account_name": "Pluggy Bank Checking",
                }
            ]
        }
    )

    id: int
    description: str
    amount: Decimal
    transaction_date: date
    category: str
    display_category: str
    is_guarded: bool
    institution_name: str
    account_name: str


class TransactionDetailResponse(TransactionResponse):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 12,
                    "description": "Padaria do Reino",
                    "amount": "-42.90",
                    "transaction_date": "2026-08-24",
                    "category": "Food",
                    "display_category": "Food",
                    "is_guarded": True,
                    "institution_name": "Pluggy Bank",
                    "account_name": "Pluggy Bank Checking",
                    "account_type": "BANK",
                    "created_at": "2026-08-24T12:00:00Z",
                }
            ]
        }
    )

    account_type: str
    created_at: datetime


class TransactionPage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 12,
                            "description": "Padaria do Reino",
                            "amount": "-42.90",
                            "transaction_date": "2026-08-24",
                            "category": "Food",
                            "display_category": "Food",
                            "is_guarded": True,
                            "institution_name": "Pluggy Bank",
                            "account_name": "Pluggy Bank Checking",
                        }
                    ],
                    "page": 1,
                    "limit": 20,
                    "total": 38,
                }
            ]
        }
    )

    items: list[TransactionResponse]
    page: int
    limit: int
    total: int
