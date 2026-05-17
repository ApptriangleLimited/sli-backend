from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        Index("ix_proposals_creator_created", "created_by_id", "created_at"),
        # submission_date: use index=True on column only (avoids duplicate ix_proposals_submission_date)
        Index("ix_proposals_underwriter_status", "underwriter_status"),
        Index("ix_proposals_ocr_status", "ocr_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fa_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    policy_type: Mapped[str] = mapped_column(String(120), nullable=False)
    submission_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ocr_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    underwriter_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    final_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    creator = relationship("User", back_populates="proposals_created")
    documents = relationship(
        "ProposalDocument",
        back_populates="proposal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProposalDocument(Base):
    __tablename__ = "proposal_documents"
    __table_args__ = (Index("ix_proposal_documents_proposal_id", "proposal_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"), nullable=False)
    section_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="application", index=True
    )
    document_type: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="application_form", index=True
    )
    side: Mapped[str | None] = mapped_column(String(16), nullable=True)
    nominee_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_extracted_data: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    proposal = relationship("Proposal", back_populates="documents")
