"""Wipe all data and recreate empty tables.

Drops every table and rebuilds the schema for the configured DATABASE_URL,
then prints the result. Requires confirmation so it cannot wipe data by
accident:

    python -m scripts.reset_db --yes

After resetting, create a login user with:

    python -m scripts.create_user --role owner
"""

import argparse

from sqlalchemy import func, select

from app.db.session import Base, SessionLocal, describe_database, engine
from app.main import ensure_schema
from app import models  # noqa: F401  (registers the tables on Base.metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Drop and recreate all database tables")
    parser.add_argument("--yes", action="store_true", help="Confirm the destructive reset")
    args = parser.parse_args()

    print(f"Database: {describe_database()}")

    if not args.yes:
        print("Refusing to wipe data without --yes.")
        print("This would erase ALL data in the database shown above.")
        print("Re-run with:  python -m scripts.reset_db --yes")
        raise SystemExit(1)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema()

    db = SessionLocal()
    try:
        user_count = db.scalar(select(func.count(models.User.id)))
    finally:
        db.close()

    print("Database reset complete.")
    print(f"Users remaining: {user_count}")
    print("Next: python -m scripts.create_user --role owner")


if __name__ == "__main__":
    main()
