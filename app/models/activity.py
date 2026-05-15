import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ActivityRow(Base):
    __tablename__ = "activity_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_hhmm: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "14:30"
    end_hhmm: Mapped[str] = mapped_column(String(10), nullable=False)
    activity_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    witness1_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("witnesses.id"), nullable=True)
    witness2_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("witnesses.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="activity_rows")


class RestRow(Base):
    __tablename__ = "rest_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_hhmm: Mapped[str] = mapped_column(String(10), nullable=False)
    end_hhmm: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    witness1_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("witnesses.id"), nullable=True)
    witness2_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("witnesses.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="rest_rows")
