from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def create_db_and_tables() -> None:
    from app.models.appointment import Appointment  # noqa: F401
    from app.models.idempotency import IdempotencyRecord  # noqa: F401

    from app.models.quo_webhook_event import QuoWebhookEvent  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _add_missing_sqlite_columns()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_sqlite_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "appointments" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("appointments")}
    required_columns = {
        "sync_status": "VARCHAR(12) DEFAULT 'PENDING' NOT NULL",
        "sync_error": "TEXT",
        "sync_attempts": "INTEGER DEFAULT 0 NOT NULL",
        "last_sync_at": "DATETIME",
        "repair_order_id": "INTEGER",
    }
    with engine.begin() as connection:
        for column_name, ddl in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE appointments ADD COLUMN {column_name} {ddl}"))
        connection.execute(text("UPDATE appointments SET sync_status = 'PENDING' WHERE sync_status = 'pending_sync'"))
        connection.execute(text("UPDATE appointments SET sync_status = 'SYNCED' WHERE sync_status = 'synced'"))
        connection.execute(text("UPDATE appointments SET sync_status = 'FAILED' WHERE sync_status = 'failed'"))
