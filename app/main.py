from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app import models  # noqa: F401


def ensure_schema() -> None:
    """Add columns introduced after the database was first created.

    ``Base.metadata.create_all`` only creates missing tables; it never alters
    existing ones, so newly added columns (e.g. ``users.password_hash``) need a
    lightweight, idempotent migration here.
    """
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("users")}
        if "password_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=engine)
    ensure_schema()

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
