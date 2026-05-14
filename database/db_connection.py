"""
Database connection — PostgreSQL connection and session factory.
Use with SQLAlchemy or raw psycopg2. Set DATABASE_URL in .env.
"""
import os
from contextlib import contextmanager
from typing import Generator

# Optional: SQLAlchemy
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, Session

# Default for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/smartriver",
)


@contextmanager
def get_connection():
    """
    Context manager for a raw database connection.
    Use for one-off queries or migrations.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except ImportError:
        raise RuntimeError("Install psycopg2-binary for PostgreSQL support")


# Optional: SQLAlchemy engine and session
# engine = create_engine(DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# def get_db() -> Generator[Session, None, None]:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
