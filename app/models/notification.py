from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_is_read", "user_id", "is_read"),
        Index("ix_notifications_reference", "reference_type", "reference_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="notifications_received")
    actor = relationship("User", foreign_keys=[actor_user_id], back_populates="notifications_triggered")
