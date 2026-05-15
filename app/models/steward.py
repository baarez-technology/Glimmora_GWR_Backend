import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Steward(Base):
    __tablename__ = "stewards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    organisation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # status: pending | completed
    status: Mapped[str] = mapped_column(String(50), default="pending")
    token: Mapped[Optional[str]] = mapped_column(String(500), unique=True, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="stewards")
    statements: Mapped[list] = relationship("Statement", back_populates="steward", lazy="select")
