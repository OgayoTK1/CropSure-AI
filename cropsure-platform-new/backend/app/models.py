"""SQLAlchemy ORM models."""

import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Date,
    ForeignKey, JSON, Enum, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _uuid():
    return str(uuid.uuid4())


class PolicyStatus(str, PyEnum):
    pending_payment = "pending_payment"
    active = "active"
    expired = "expired"
    payment_failed = "payment_failed"


class PayoutStatus(str, PyEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Farm(Base):
    __tablename__ = "farms"

    id = Column(String, primary_key=True, default=_uuid)
    farmer_name = Column(String(200), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    polygon_geojson = Column(JSON, nullable=False)
    area_acres = Column(Float, nullable=False)
    crop_type = Column(String(50), nullable=False)
    village = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    policies = relationship("Policy", back_populates="farm", cascade="all, delete-orphan")
    ndvi_readings = relationship("NDVIReading", back_populates="farm", cascade="all, delete-orphan")
    payouts = relationship("Payout", back_populates="farm", cascade="all, delete-orphan")
    baseline = relationship("Baseline", back_populates="farm", uselist=False, cascade="all, delete-orphan")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String, primary_key=True, default=_uuid)
    farm_id = Column(String, ForeignKey("farms.id"), nullable=False, index=True)
    season_start = Column(Date, nullable=False)
    season_end = Column(Date, nullable=False)
    premium_paid_kes = Column(Float, nullable=False)
    coverage_amount_kes = Column(Float, nullable=False)
    status = Column(Enum(PolicyStatus), default=PolicyStatus.pending_payment, nullable=False)
    mpesa_checkout_id = Column(String(100))
    mpesa_reference = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="policies")
    payouts = relationship("Payout", back_populates="policy", cascade="all, delete-orphan")


class NDVIReading(Base):
    __tablename__ = "ndvi_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farm_id = Column(String, ForeignKey("farms.id"), nullable=False, index=True)
    reading_date = Column(Date, nullable=False)
    ndvi_value = Column(Float, nullable=False)
    ndvi_zscore = Column(Float)
    stress_type = Column(String(30))
    confidence = Column(Float)
    cloud_contaminated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="ndvi_readings")


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(String, primary_key=True, default=_uuid)
    policy_id = Column(String, ForeignKey("policies.id"), nullable=False)
    farm_id = Column(String, ForeignKey("farms.id"), nullable=False, index=True)
    payout_amount_kes = Column(Float, nullable=False)
    stress_type = Column(String(30), nullable=False)
    explanation_en = Column(Text)
    explanation_sw = Column(Text)
    mpesa_conversation_id = Column(String(100))
    mpesa_transaction_id = Column(String(100))
    status = Column(Enum(PayoutStatus), default=PayoutStatus.pending, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    policy = relationship("Policy", back_populates="payouts")
    farm = relationship("Farm", back_populates="payouts")


class Baseline(Base):
    __tablename__ = "baselines"

    farm_id = Column(String, ForeignKey("farms.id"), primary_key=True)
    baseline_data = Column(JSON, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="baseline")
