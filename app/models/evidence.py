import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, BigInteger, Float, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("attempts.id"), nullable=False)
    # type: video | image | document | audio | link
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # status: uploading | scanning | indexed | rejected
    status: Mapped[str] = mapped_column(String(50), default="uploading")
    file_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    s3_key: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)  # for link type
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array string
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="evidence")
