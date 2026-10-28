"""
Postgres layer. Three tables:
  - transactions      : every transaction that came in
  - fraud_analysis     : the fraud engine's verdict for each transaction
  - verification_events: OTP attempts, for audit + rate-limit history
"""

from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Text, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class TransactionRow(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    merchant = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    is_new_device = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class FraudAnalysisRow(Base):
    __tablename__ = "fraud_analysis"

    transaction_id = Column(String, primary_key=True)
    score = Column(Float, nullable=False)
    decision = Column(String, nullable=False)
    reasons = Column(Text, nullable=False)       # stored as comma-joined string
    explanation = Column(Text, nullable=True)     # Claude's explanation, if generated
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationEventRow(Base):
    __tablename__ = "verification_events"

    id = Column(String, primary_key=True)         # uuid, generated at insert time
    transaction_id = Column(String, index=True, nullable=False)
    success = Column(Boolean, nullable=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Call once at startup to create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency - yields a session, always closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
