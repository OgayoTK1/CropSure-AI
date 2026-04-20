import uuid
import enum
from datetime import datetime, date
from sqlalchemy import String, Float, Boolean, DateTime, Date, ForeignKey, Uuid, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class PolicyStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    active = "active"
    expired = "expired"
    payment_failed = "payment_failed"


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20), index=True)   # 2547XXXXXXXX
    polygon_geojson: Mapped[dict] = mapped_column(JSON)
    area_acres: Mapped[float] = mapped_column(Float)
    crop_type: Mapped[str] = mapped_column(String(50))
    village: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    policies: Mapped[list["Policy"]] = relationship(back_populates="farm")
    ndvi_readings: Mapped[list["NdviReading"]] = relationship(back_populates="farm")
    payouts: Mapped[list["Payout"]] = relationship(back_populates="farm")
    baseline: Mapped["Baseline | None"] = relationship(back_populates="farm", uselist=False)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id"))
    season_start: Mapped[datetime] = mapped_column(DateTime)
    season_end: Mapped[datetime] = mapped_column(DateTime)
    premium_paid_kes: Mapped[float] = mapped_column(Float)
    coverage_amount_kes: Mapped[float] = mapped_column(Float)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus), default=PolicyStatus.pending_payment
    )
    mpesa_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farm: Mapped["Farm"] = relationship(back_populates="policies")
    payouts: Mapped[list["Payout"]] = relationship(back_populates="policy")


class NdviReading(Base):
    __tablename__ = "ndvi_readings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id"))
    reading_date: Mapped[date] = mapped_column(Date)
    ndvi_value: Mapped[float] = mapped_column(Float)
    stress_type: Mapped[str | None] = mapped_column(String(50), nullable=True)   # drought | flood | pest | none
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_contaminated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farm: Mapped["Farm"] = relationship(back_populates="ndvi_readings")


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id"))
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id"))
    payout_amount_kes: Mapped[float] = mapped_column(Float)
    stress_type: Mapped[str] = mapped_column(String(50))
    explanation_en: Mapped[str] = mapped_column(String(500))
    explanation_sw: Mapped[str] = mapped_column(String(500))
    mpesa_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ConversationID
    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus), default=PayoutStatus.pending
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    policy: Mapped["Policy"] = relationship(back_populates="payouts")
    farm: Mapped["Farm"] = relationship(back_populates="payouts")


class Baseline(Base):
    __tablename__ = "baselines"

    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id"), primary_key=True)
    baseline_data: Mapped[dict] = mapped_column(JSON)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    farm: Mapped["Farm"] = relationship(back_populates="baseline")
