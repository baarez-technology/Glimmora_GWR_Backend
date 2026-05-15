import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Clarification(Base):
    __tablename__ = "clarifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    witness_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("witnesses.id"), nullable=True)
    raised_by_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    # status: open | responded | closed
    status: Mapped[str] = mapped_column(String(50), default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="clarifications")
    messages: Mapped[list] = relationship("ClarificationMessage", back_populates="clarification", lazy="select")


class ClarificationMessage(Base):
    __tablename__ = "clarification_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clarification_id: Mapped[str] = mapped_column(String(36), ForeignKey("clarifications.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    clarification: Mapped["Clarification"] = relationship("Clarification", back_populates="messages")
