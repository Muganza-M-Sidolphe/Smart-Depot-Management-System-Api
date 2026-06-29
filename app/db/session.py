import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def describe_database() -> str:
    """Human-readable location of the configured database.

    For SQLite this resolves the relative path to an absolute file path so it
    is obvious which file the server/scripts actually use.
    """
    url = settings.database_url
    prefix = "sqlite:///"
    if url.startswith(prefix):
        path = url[len(prefix):]
        return f"{url}  ->  {os.path.abspath(path)}"
    return url


class Base(DeclarativeBase):
    pass
