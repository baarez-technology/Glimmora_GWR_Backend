import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_ref: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    record_title: Mapped[str] = mapped_column(String(500), nullable=False)
    organizer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # status: draft | processing | review | approved | rejected
    status: Mapped[str] = mapped_column(String(50), default="draft")
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_jsonb: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for SQLite compat
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    organizer: Mapped["User"] = relationship("User", back_populates="attempts")
    witnesses: Mapped[list] = relationship("Witness", back_populates="attempt", lazy="select")
    stewards: Mapped[list] = relationship("Steward", back_populates="attempt", lazy="select")
    activity_rows: Mapped[list] = relationship("ActivityRow", back_populates="attempt", lazy="select")
    rest_rows: Mapped[list] = relationship("RestRow", back_populates="attempt", lazy="select")
    evidence: Mapped[list] = relationship("Evidence", back_populates="attempt", lazy="select")
    statements: Mapped[list] = relationship("Statement", back_populates="attempt", lazy="select")
    clarifications: Mapped[list] = relationship("Clarification", back_populates="attempt", lazy="select")
    comments: Mapped[list] = relationship("Comment", back_populates="attempt", lazy="select")
    ai_alerts: Mapped[list] = relationship("AIAlert", back_populates="attempt", lazy="select")
