"""Dashboard payloads (RF03)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class BankBalance(BaseModel):
    connection_id: int
    institution_name: str
    balance: Decimal
    share_percentage: float


class OverviewResponse(BaseModel):
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
    id: int
    description: str
    amount: Decimal
    transaction_date: date
    category: str
    is_guarded: bool
    institution_name: str


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    page: int
    limit: int
    total: int
