from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    UPDATED = "updated"
    CANCELLED = "cancelled"


class SyncStatus(StrEnum):
    PENDING = "pending_sync"
    SYNCED = "synced"
    FAILED = "failed"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shopware_appointment_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    repair_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_year: Mapped[int | None] = mapped_column(nullable=True)
    vehicle_make: Mapped[str | None] = mapped_column(String(120), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_description: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus),
        default=AppointmentStatus.SCHEDULED,
        index=True,
    )
    sync_status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), default=SyncStatus.PENDING, index=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_tools: Mapped[str | None] = mapped_column(Text, nullable=True)
    parts_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    communication_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
