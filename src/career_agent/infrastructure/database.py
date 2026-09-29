"""PostgreSQL connection, sessions, and declarative-model primitives."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from career_agent.core.config import get_settings


class Base(DeclarativeBase):
    """Base class shared by all SQLAlchemy persistence models."""


@lru_cache
def create_database_engine() -> Engine:
    """Create an engine with stale-connection checking enabled."""

    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def create_session_factory() -> sessionmaker[Session]:
    """Create sessions that callers can use for one unit of work."""

    return sessionmaker(bind=create_database_engine(), autoflush=False, expire_on_commit=False)


def get_database_session() -> Generator[Session, None, None]:
    """Provide one database session to a FastAPI request and always close it."""

    session = create_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> None:
    """Raise a SQLAlchemy error if PostgreSQL cannot answer a trivial query."""

    with create_database_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
