from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/analytics"
)

engine = create_engine(
    DATABASE_URL,
    # ── Connection pool tuning ──────────────────────────────────────────────
    # pool_size: number of persistent connections kept open.
    # max_overflow: extra connections allowed when pool_size is exhausted.
    # pool_pre_ping: test connections before use (detects stale/closed conns).
    # pool_recycle: recycle connections after N seconds (avoids PG timeout).
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)