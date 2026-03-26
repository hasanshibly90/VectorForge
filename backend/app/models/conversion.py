import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class ConversionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Conversion(Base):
    __tablename__ = "conversions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    api_key_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("api_keys.id"), nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        Enum(ConversionStatus), default=ConversionStatus.PENDING, nullable=False
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_format: Mapped[str] = mapped_column(String(10), nullable=False)
    original_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    input_path: Mapped[str] = mapped_column(String(500), nullable=False)
    output_dir_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_svg_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_bmp_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_png_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_layers_json: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_viewer_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_dxf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    layers_info: Mapped[list | None] = mapped_column(JSON, nullable=True)
    engine_used: Mapped[str | None] = mapped_column(String(20), nullable=True)

    share_token: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)

    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_billed: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="conversions")
