"""Keep the sandbox demo feeling alive when the calendar moves forward."""

from datetime import date, timedelta

from sqlmodel import Session

from app.services.treasury import user_transactions

DEMO_EMAILS = frozenset({"queen@goldqueen.dev", "squire@goldqueen.dev"})


def refresh_demo_transaction_dates(session: Session, user_id: int) -> int:
    """Shift every transaction so the newest lands on yesterday.

    Pluggy data is insert-only; once August is in the database and September
    starts, the dashboard looks frozen. For demo accounts we slide the whole
    timeline forward instead of asking recruiters to re-sync.
    """
    rows = user_transactions(session, user_id)
    if not rows:
        return 0

    today = date.today()
    target_latest = today - timedelta(days=1)
    latest = max(transaction.transaction_date for transaction, _ in rows)

    if latest >= target_latest:
        return 0

    delta = target_latest - latest
    updated = 0
    month_start = today.replace(day=1)

    for transaction, _ in rows:
        shifted = transaction.transaction_date + delta
        if shifted > today:
            shifted = today
        if shifted < month_start:
            shifted = month_start
        if shifted != transaction.transaction_date:
            transaction.transaction_date = shifted
            session.add(transaction)
            updated += 1

    if updated:
        session.commit()
    return updated


def maybe_refresh_demo(session: Session, email: str, user_id: int) -> int:
    if email.strip().lower() not in DEMO_EMAILS:
        return 0
    return refresh_demo_transaction_dates(session, user_id)
