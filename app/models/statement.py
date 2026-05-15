import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    witness_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("witnesses.id"), nullable=True)
    steward_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("stewards.id"), nullable=True)
    # kind: witness | timekeeper | steward | cover_letter
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    fields_jsonb: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON of statement fields
    signature_png: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # base64 or S3 key
    pdf_s3_key: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="statements")
    witness: Mapped[Optional["Witness"]] = relationship("Witness", back_populates="statements")
    steward: Mapped[Optional["Steward"]] = relationship("Steward", back_populates="statements")
