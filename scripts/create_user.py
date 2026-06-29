"""Create or reset a login user.

Run from the SAME directory you start the server from, so it writes to the
same SQLite database the API reads:

    python -m scripts.create_user
    python -m scripts.create_user --email boss@depot.rw --password "Secret123" --role admin

If the email already exists, its password and role are updated.
"""

import argparse

from app.core.config import settings
from app.core.roles import Role, normalize_role
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.main import ensure_schema
from app.models.business import User
from app.services import auth_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or reset a login user")
    parser.add_argument("--name", default="Admin User")
    parser.add_argument("--email", default="admin@smartdepot.rw")
    parser.add_argument("--password", default="Admin@12345")
    parser.add_argument(
        "--role",
        default=Role.OWNER.value,
        help="One of: " + ", ".join(role.value for role in Role),
    )
    parser.add_argument("--phone", default=None)
    args = parser.parse_args()

    role = normalize_role(args.role)

    Base.metadata.create_all(bind=engine)
    ensure_schema()

    db = SessionLocal()
    try:
        user = auth_service.get_user_by_email(db, args.email)
        if user is None:
            user = User(name=args.name, email=args.email.lower(), role=role, phone=args.phone)
            db.add(user)
            action = "Created"
        else:
            user.role = role
            action = "Updated"
        user.status = "active"
        user.password_hash = hash_password(args.password)
        db.commit()
        db.refresh(user)
        print(f"{action} user '{user.email}' (role={user.role}) in database: {settings.database_url}")
        print(f"Login with email='{user.email}' password='{args.password}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
