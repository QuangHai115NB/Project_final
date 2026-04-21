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
