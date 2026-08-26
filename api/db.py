import os
from pathlib import Path
from typing import Generator
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Standardize postgres:// to postgresql:// for SQLAlchemy compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, echo=False)
else:
    # Default to trace.db inside the api directory
    db_path = Path(__file__).resolve().parent / "trace.db"
    sqlite_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(
        sqlite_url, echo=False, connect_args={"check_same_thread": False}
    )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
