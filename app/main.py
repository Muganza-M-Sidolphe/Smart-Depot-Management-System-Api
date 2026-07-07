import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.db.session import Base, engine
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: "FastAPI"):
    if settings.enable_scheduler:
        start_scheduler()
    try:
        yield
    finally:
        if settings.enable_scheduler:
            shutdown_scheduler()


def _scalar_default_sql(column) -> str | None:
    """SQL literal for a column's scalar default, used to backfill added columns."""
    default = column.default
    if default is None or not getattr(default, "is_scalar", False):
        return None
    value = default.arg
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return None


def ensure_schema() -> None:
    """Add columns introduced after a table was first created.

    ``Base.metadata.create_all`` creates missing tables but never alters existing
    ones, so newly added model columns need this lightweight, idempotent
    migration. It compares each mapped table to the live schema and issues
    ``ALTER TABLE ... ADD COLUMN`` for anything missing (nullable, so SQLite can
    add it without a default).
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            column_type = column.type.compile(dialect=engine.dialect)
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}'
            # Backfill a default so existing rows don't get NULL in a NOT NULL column.
            literal = _scalar_default_sql(column)
            if literal is not None:
                ddl += f" DEFAULT {literal}"
            with engine.begin() as connection:
                connection.execute(text(ddl))


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
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

    # Accept both trailing-slash and non-trailing-slash forms of every route
    # (e.g. /products and /products/) without a 307 redirect. We rewrite the
    # incoming path to whichever concrete route actually exists BEFORE routing,
    # so all auth/role dependencies still run normally.
    literal_paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute) and "{" not in route.path
    }

    @app.middleware("http")
    async def normalize_trailing_slash(request, call_next):
        path = request.scope["path"]
        if path not in literal_paths and len(path) > 1:
            if path.endswith("/") and path[:-1] in literal_paths:
                request.scope["path"] = path[:-1]
            elif not path.endswith("/") and path + "/" in literal_paths:
                request.scope["path"] = path + "/"
        return await call_next(request)

    # Serve uploaded receipts (and any other uploads) as static files.
    os.makedirs(settings.upload_dir, exist_ok=True)
    app.mount(f"/{settings.upload_dir}", StaticFiles(directory=settings.upload_dir), name="uploads")

    return app


app = create_app()
