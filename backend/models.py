import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    national_id: Mapped[str] = mapped_column(String(20), unique=True)
    location: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farms: Mapped[list["Farm"]] = relationship(back_populates="farmer")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="farmer")


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farmers.id"))
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    acreage: Mapped[float] = mapped_column(Float)
    crop_type: Mapped[str] = mapped_column(String(50))
    season: Mapped[str] = mapped_column(String(20))        # e.g. "2027A"
    premium_amount: Mapped[float] = mapped_column(Float)   # KES paid by farmer
    payout_amount: Mapped[float] = mapped_column(Float)    # KES paid out on drought
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farmer: Mapped["Farmer"] = relationship(back_populates="farms")
    monitoring_cycles: Mapped[list["MonitoringCycle"]] = relationship(back_populates="farm")
    transactions: Mapped[list["MpesaTransaction"]] = relationship(back_populates="farm")


class MpesaTransaction(Base):
    __tablename__ = "mpesa_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_type: Mapped[str] = mapped_column(String(10))        # STK | B2C
    checkout_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # B2C
    phone_number: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Float)
    mpesa_receipt_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | success | failed
    farm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("farms.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm: Mapped["Farm | None"] = relationship(back_populates="transactions")


class MonitoringCycle(Base):
    __tablename__ = "monitoring_cycles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id"))
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ndvi_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    drought_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    payout_initiated: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    farm: Mapped["Farm"] = relationship(back_populates="monitoring_cycles")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farmers.id"))
    channel: Mapped[str] = mapped_column(String(20))       # sms or whatsapp
    phone_number: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | sent | failed
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farmer: Mapped["Farmer"] = relationship(back_populates="notifications")
