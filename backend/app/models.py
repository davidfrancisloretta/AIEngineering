from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# -----------------------------------------------
# Campaign Metrics (existing)
# -----------------------------------------------
class CampaignMetrics(Base):
    __tablename__ = "campaign_metrics"

    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String, index=True)
    impressions = Column(Integer)
    clicks = Column(Integer)
    views = Column(Integer)
    conversions = Column(Integer)

    ttr = Column(Float)  # Click-Through Rate
    vtr = Column(Float)  # View-Through Rate
    cvr = Column(Float)  # Conversion Rate


# -----------------------------------------------
# Users
# -----------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)


# -----------------------------------------------
# Rave API config (per user)
# -----------------------------------------------
class ApiConfig(Base):
    __tablename__ = "api_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    rave_public_key = Column(String)
    rave_secret_key = Column(String)
    updated_at = Column(DateTime, default=_now)


# -----------------------------------------------
# Rave transactions (fetched from Flutterwave)
# -----------------------------------------------
class RaveTransaction(Base):
    __tablename__ = "rave_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rave_id = Column(Integer, unique=True, index=True)
    transaction_ref = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String)
    status = Column(String)
    payment_type = Column(String)
    customer_email = Column(String)
    customer_name = Column(String)
    data_yaml = Column(Text)
    fetched_at = Column(DateTime, default=_now)
