import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Witness(Base):
    __tablename__ = "witnesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    # role: specialist | independent | timekeeper
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    # status: pending | invited | completed | rejected
    status: Mapped[str] = mapped_column(String(50), default="pending")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    organisation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expertise: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    token: Mapped[Optional[str]] = mapped_column(String(500), unique=True, nullable=True, index=True)
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="witnesses")
    statements: Mapped[list] = relationship("Statement", back_populates="witness", lazy="select")
