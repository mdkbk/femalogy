import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.crypto import EncryptedText
from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    # onboarding answers; real logged data overrides these
    avg_cycle_length: Mapped[int | None] = mapped_column(Integer)
    avg_period_length: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    periods: Mapped[list["Period"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Period.start_date"
    )
    checkins: Mapped[list["CheckIn"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Period(Base):
    __tablename__ = "periods"
    __table_args__ = (UniqueConstraint("user_id", "start_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # she told us the gap before this period was one real long cycle, not a missed log
    gap_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="periods")


class CheckIn(Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    mood: Mapped[int | None] = mapped_column(Integer)  # 1-5
    energy: Mapped[int | None] = mapped_column(Integer)  # 1-5
    sleep_quality: Mapped[int | None] = mapped_column(Integer)  # 1-5
    symptoms: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(EncryptedText(4000))
    phase_at_checkin: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="checkins")
