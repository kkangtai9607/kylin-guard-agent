from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import AppConfig, get_config


def build_engine(config: AppConfig) -> Engine:
    url = config.database.url
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    if url.startswith("sqlite"):
        timeout = config.database.busy_timeout_ms

        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={timeout}")
            cursor.close()

    return engine


engine = build_engine(get_config())
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
