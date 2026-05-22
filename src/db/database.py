import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cv_review.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("true", "1", "yes")

engine_options = {
    "echo": SQL_ECHO,
    "future": True,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update({
        "pool_size": 20,
        "max_overflow": 30,
        "pool_recycle": 3600,
    })

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def _ensure_sqlite_user_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    columns = {
        "role": "VARCHAR(20) NOT NULL DEFAULT 'user'",
        "plan": "VARCHAR(20) NOT NULL DEFAULT 'free'",
        "premium_until": "DATETIME",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
    }
    with engine.begin() as connection:
        existing = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(users)")).fetchall()
        }
        for name, ddl in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))


def _ensure_sqlite_match_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    columns = {
        "user_review": "TEXT",
    }
    with engine.begin() as connection:
        existing = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(match_history)")).fetchall()
        }
        for name, ddl in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE match_history ADD COLUMN {name} {ddl}"))


def _ensure_sqlite_app_settings() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS app_settings ("
            "key VARCHAR(100) PRIMARY KEY, "
            "value TEXT, "
            "updated_at DATETIME)"
        ))


def init_db():
    """
    Verify connectivity, then create tables for local/dev environments.
    """
    from src.db import models  # noqa: F401

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if DATABASE_URL.startswith("sqlite"):
                print("Database connection successful! Connected to SQLite")
            else:
                result = connection.execute(text("SELECT current_database();"))
                print(f"Database connection successful! Connected to {result.fetchone()[0]}")
    except OperationalError as exc:
        print(f"Error: Unable to connect to the database - {exc}")
        raise

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_user_columns()
    _ensure_sqlite_match_columns()
    _ensure_sqlite_app_settings()

    from src.services.admin_service import seed_admin_from_env
    seed_admin_from_env(os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD"))
