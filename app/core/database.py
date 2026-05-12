import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.schema import CreateColumn

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _column_sql(column) -> str:
    return str(CreateColumn(column).compile(dialect=engine.dialect)).strip()


def _create_all_idempotent() -> None:
    """Run create_all; tolerate duplicate table/index if DB already partially synced."""
    try:
        Base.metadata.create_all(bind=engine)
    except ProgrammingError as exc:
        msg = str(exc.orig or exc).lower()
        if "already exists" in msg:
            logger.warning("create_all skipped (object already exists): %s", exc.orig or exc)
            return
        raise


def create_missing_tables_and_columns() -> None:
    """Safe dev sync: create missing tables and add simple missing columns only."""
    from app.models import proposal, refresh_token, role, user  # noqa: F401

    _create_all_idempotent()

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            existing_columns = {column["name"] for column in inspector.get_columns(table.name)}

            for column in table.columns:
                if column.name in existing_columns:
                    continue

                if not column.nullable and column.default is None and column.server_default is None:
                    logger.warning(
                        "Skipping non-null missing column without default: %s.%s",
                        table.name,
                        column.name,
                    )
                    continue

                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN {_column_sql(column)}'
                logger.info("Adding missing column: %s.%s", table.name, column.name)
                connection.execute(text(ddl))
