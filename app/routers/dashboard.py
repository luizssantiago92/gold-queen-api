"""RF03 - Dashboard aggregation endpoints."""

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.core.exceptions import NotFoundError
from app.models.entities import Account, BankConnection, Transaction, require_id
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
from app.schemas.errors import error_responses
from app.services import treasury
from app.services.demo_refresh import maybe_refresh_demo

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

_AUTH = error_responses((401, "The bearer token is missing or invalid."))


def _refresh_demo_if_needed(session: SessionDep, current_user: CurrentUser) -> None:
    maybe_refresh_demo(session, current_user.email, require_id(current_user.id))


def _transaction_response(
    transaction: Transaction,
    account: Account,
    connection: BankConnection,
) -> TransactionResponse:
    return TransactionResponse(
        id=require_id(transaction.id),
        description=transaction.description,
        amount=transaction.amount,
        transaction_date=transaction.transaction_date,
        category=transaction.category,
        display_category=treasury.display_category_for(transaction, account),
        is_guarded=transaction.is_guarded,
        institution_name=connection.institution_name,
        account_name=account.name,
    )


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="Consolidated balance",
    description=(
        "Return the total balance, each bank share, and this month's "
        "income and expenses."
    ),
    responses=_AUTH,
)
def overview(current_user: CurrentUser, session: SessionDep) -> OverviewResponse:
    user_id = require_id(current_user.id)
    _refresh_demo_if_needed(session, current_user)

    balances = treasury.balance_by_connection(session, user_id)
    total = treasury.total_balance(session, user_id)
    expenses, income = treasury.month_totals(session, user_id)

    banks = []
    for connection in treasury.user_connections(session, user_id):
        connection_id = require_id(connection.id)
        balance = balances.get(connection_id, treasury.ZERO)
        banks.append(
            BankBalance(
                connection_id=connection_id,
                institution_name=connection.institution_name,
                balance=balance,
                share_percentage=treasury.share(balance, total),
            )
        )

    return OverviewResponse(
        total_balance=total,
        currency="BRL",
        banks=sorted(banks, key=lambda bank: bank.balance, reverse=True),
        month_expenses=expenses,
        month_income=income,
        reference_month=date.today().strftime("%Y-%m"),
    )


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    summary="Spending by category",
    description="Return this month's expenses grouped into display categories.",
    responses=_AUTH,
)
def categories(current_user: CurrentUser, session: SessionDep) -> CategoriesResponse:
    user_id = require_id(current_user.id)
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


@router.get(
    "/monthly-series",
    response_model=MonthlySeriesResponse,
    summary="Daily expense series",
    description="Return cumulative expenses for each elapsed day of the current month.",
    responses=_AUTH,
)
def monthly_series(
    current_user: CurrentUser, session: SessionDep
) -> MonthlySeriesResponse:
    user_id = require_id(current_user.id)
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


@router.get(
    "/transactions",
    response_model=TransactionPage,
    summary="List transactions",
    description="Return the current month's transactions, newest first.",
    responses=error_responses(
        (401, "The bearer token is missing or invalid."),
        (422, "page or limit is out of range."),
    ),
)
def transactions(
    current_user: CurrentUser,
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> TransactionPage:
    user_id = require_id(current_user.id)
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


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="Read one transaction",
    description="Return one transaction when it belongs to the current user.",
    responses=error_responses(
        (401, "The bearer token is missing or invalid."),
        (404, "No transaction with this id belongs to the current user."),
        (422, "The transaction id was not an integer."),
    ),
)
def transaction_detail(
    transaction_id: int,
    current_user: CurrentUser,
    session: SessionDep,
) -> TransactionDetailResponse:
    user_id = require_id(current_user.id)
    _refresh_demo_if_needed(session, current_user)

    row = treasury.get_transaction_for_user(session, user_id, transaction_id)
    if row is None:
        raise NotFoundError("Transaction not found.")

    transaction, account, connection = row
    base = _transaction_response(transaction, account, connection)
    return TransactionDetailResponse(
        **base.model_dump(),
        account_type=account.account_type,
        created_at=transaction.created_at,
    )
