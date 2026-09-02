"""RF03 - Dashboard aggregation endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas.dashboard import (
    BankBalance,
    CategoriesResponse,
    CategoryBreakdown,
    MonthlySeriesPoint,
    MonthlySeriesResponse,
    OverviewResponse,
    TransactionDetailResponse,
    TransactionPage,
    TransactionResponse,
)
from app.models.entities import Account, BankConnection, Transaction
from app.services import treasury
from app.services.demo_refresh import maybe_refresh_demo

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


def _refresh_demo_if_needed(session: SessionDep, current_user: CurrentUser) -> None:
    maybe_refresh_demo(session, current_user.email, current_user.id)  # type: ignore[arg-type]


def _transaction_response(
    transaction: Transaction,
    account: Account,
    connection: BankConnection,
) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,  # type: ignore[arg-type]
        description=transaction.description,
        amount=transaction.amount,
        transaction_date=transaction.transaction_date,
        category=transaction.category,
        display_category=treasury.display_category_for(transaction, account),
        is_guarded=transaction.is_guarded,
        institution_name=connection.institution_name,
        account_name=account.name,
    )


@router.get("/overview", response_model=OverviewResponse)
def overview(current_user: CurrentUser, session: SessionDep) -> OverviewResponse:
    user_id: int = current_user.id  # type: ignore[assignment]
    _refresh_demo_if_needed(session, current_user)

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
    _refresh_demo_if_needed(session, current_user)

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
    _refresh_demo_if_needed(session, current_user)

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
    _refresh_demo_if_needed(session, current_user)

    start, end = treasury.month_bounds()
    rows = treasury.user_transaction_rows(session, user_id, start, end)
    start_index = (page - 1) * limit
    window = rows[start_index : start_index + limit]

    return TransactionPage(
        items=[
            _transaction_response(transaction, account, connection)
            for transaction, account, connection in window
        ],
        page=page,
        limit=limit,
        total=len(rows),
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
def transaction_detail(
    transaction_id: int,
    current_user: CurrentUser,
    session: SessionDep,
) -> TransactionDetailResponse:
    user_id: int = current_user.id  # type: ignore[assignment]
    _refresh_demo_if_needed(session, current_user)

    row = treasury.get_transaction_for_user(session, user_id, transaction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    transaction, account, connection = row
    base = _transaction_response(transaction, account, connection)
    return TransactionDetailResponse(
        **base.model_dump(),
        account_type=account.account_type,
        created_at=transaction.created_at,
    )
