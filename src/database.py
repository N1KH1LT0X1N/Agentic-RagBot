"""
MediGuard AI — Database layer

Provides SQLAlchemy engine/session factories and the declarative Base.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

from src.settings import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


@lru_cache(maxsize=1)
def _engine():
    settings = get_settings()
    return create_engine(
        settings.postgres.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.debug,
    )


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=_engine(), autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session and commits/rolls back."""
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
