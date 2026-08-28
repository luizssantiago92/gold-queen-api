"""RF03 - Dashboard aggregation endpoints."""

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas.dashboard import (
    BankBalance,
    CategoriesResponse,
    CategoryBreakdown,
    MonthlySeriesPoint,
    MonthlySeriesResponse,
    OverviewResponse,
    TransactionPage,
    TransactionResponse,
)
from app.services import treasury

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=OverviewResponse)
def overview(current_user: CurrentUser, session: SessionDep) -> OverviewResponse:
    user_id: int = current_user.id  # type: ignore[assignment]

    balances = treasury.balance_by_connection(session, user_id)
    total = treasury.total_balance(session, user_id)
    expenses, income = treasury.month_totals(session, user_id)

    banks = [
        BankBalance(
            connection_id=connection.id,  # type: ignore[arg-type]
            institution_name=connection.institution_name,
            balance=balances.get(connection.id, treasury.ZERO),  # type: ignore[arg-type]
            share_percentage=treasury.share(
                balances.get(connection.id, treasury.ZERO), total  # type: ignore[arg-type]
            ),
        )
        for connection in treasury.user_connections(session, user_id)
    ]

    return OverviewResponse(
        total_balance=total,
        currency="BRL",
        banks=sorted(banks, key=lambda bank: bank.balance, reverse=True),
        month_expenses=expenses,
        month_income=income,
        reference_month=date.today().strftime("%Y-%m"),
    )


@router.get("/categories", response_model=CategoriesResponse)
def categories(current_user: CurrentUser, session: SessionDep) -> CategoriesResponse:
    user_id: int = current_user.id  # type: ignore[assignment]

    breakdown = treasury.expenses_by_category(session, user_id)
    total = sum((value for value, _ in breakdown.values()), treasury.ZERO)

    items = [
        CategoryBreakdown(
            category=category,
            total=amount,
            share_percentage=treasury.share(amount, total),
            transaction_count=count,
        )
        for category, (amount, count) in breakdown.items()
    ]

    return CategoriesResponse(
        reference_month=date.today().strftime("%Y-%m"),
        total_expenses=total,
        categories=sorted(items, key=lambda item: item.total, reverse=True),
    )


@router.get("/monthly-series", response_model=MonthlySeriesResponse)
def monthly_series(current_user: CurrentUser, session: SessionDep) -> MonthlySeriesResponse:
    user_id: int = current_user.id  # type: ignore[assignment]

    series = treasury.daily_cumulative_expenses(session, user_id)
    total = series[-1][1] if series else treasury.ZERO

    return MonthlySeriesResponse(
        reference_month=date.today().strftime("%Y-%m"),
        total_expenses=total,
        points=[
            MonthlySeriesPoint(date=day, cumulative_expenses=amount)
            for day, amount in series
        ],
    )


@router.get("/transactions", response_model=TransactionPage)
def transactions(
    current_user: CurrentUser,
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> TransactionPage:
    user_id: int = current_user.id  # type: ignore[assignment]

    rows = treasury.user_transactions(session, user_id)
    start = (page - 1) * limit
    window = rows[start : start + limit]

    return TransactionPage(
        items=[
            TransactionResponse(
                id=transaction.id,  # type: ignore[arg-type]
                description=transaction.description,
                amount=transaction.amount,
                transaction_date=transaction.transaction_date,
                category=transaction.category,
                is_guarded=transaction.is_guarded,
                institution_name=connection.institution_name,
            )
            for transaction, connection in window
        ],
        page=page,
        limit=limit,
        total=len(rows),
    )
