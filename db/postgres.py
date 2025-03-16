from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Tuple, Callable
from .postgres_models.base import Base


def init_db(database_url: str) -> Tuple[Engine, Callable[[], Session]]:
    """
    Create tables in the database and return a SQLAlchemy Engine and a session factory.

    Args:
        database_url (str): The connection URL for the PostgreSQL database.

    Returns:
        Tuple[Engine, Callable[[], Session]]: A tuple containing:
            - Engine: A SQLAlchemy Engine instance configured with connection pooling.
            - Callable[[], Session]: A session factory that returns a new Session.
    """
    engine: Engine = create_engine(
        database_url,
        pool_size=50,
        max_overflow=50,
        pool_timeout=10,
        pool_recycle=1200
    )

    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)
