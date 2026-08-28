"""Seed demo users so the frontend can log in without a signup flow.

Run with: ``python -m app.seed``
"""

from sqlmodel import Session, select

from app.core.database import get_engine, init_db
from app.core.security import hash_password
from app.models.entities import User

DEMO_USERS: tuple[tuple[str, str, str], ...] = (
    ("queen@goldqueen.dev", "Gold Queen", "QueenDemo123!"),
    ("squire@goldqueen.dev", "Royal Squire", "SquireDemo123!"),
)


def seed_demo_users() -> list[str]:
    """Create the demo accounts if they do not exist. Returns created emails."""
    init_db()
    created: list[str] = []

    with Session(get_engine()) as session:
        for email, display_name, password in DEMO_USERS:
            existing = session.exec(select(User).where(User.email == email)).first()
            if existing is not None:
                continue

            session.add(
                User(
                    email=email,
                    display_name=display_name,
                    password_hash=hash_password(password),
                )
            )
            created.append(email)

        session.commit()

    return created


if __name__ == "__main__":
    created = seed_demo_users()
    if created:
        print(f"Created demo users: {', '.join(created)}")
    else:
        print("Demo users already present.")
