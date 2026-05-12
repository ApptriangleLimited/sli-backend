from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProposalDocumentOut(BaseModel):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    ocr_extracted_data: dict | list | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalOut(BaseModel):
    id: int
    created_by_id: int
    note: str | None
    fa_number: str
    policy_type: str
    submission_date: date
    ocr_status: str
    underwriter_status: str
    final_status: str
    created_at: datetime
    updated_at: datetime
    documents: list[ProposalDocumentOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProposalListEnvelope(BaseModel):
    items: list[ProposalOut]
    total: int
    has_more: bool
    next_cursor_created_at: datetime | None = None
    next_cursor_id: int | None = None


class ProposalCreatorBriefOut(BaseModel):
    id: int
    name: str
    email: str


class ProposalTableRowOut(BaseModel):
    """Underwriter queue / table row; no document payloads."""

    id: int
    creator: ProposalCreatorBriefOut
    note: str | None
    fa_number: str
    policy_type: str
    submission_date: date
    ocr_status: str
    underwriter_status: str
    final_status: str
    created_at: datetime
    updated_at: datetime
    document_count: int


class ProposalUnderwriterTableEnvelope(BaseModel):
    items: list[ProposalTableRowOut]
    total: int
    has_more: bool
    next_cursor_created_at: datetime | None = None
    next_cursor_id: int | None = None


class ProposalUnderwriterDetailOut(BaseModel):
    """Full proposal for underwriter review (documents include OCR payloads)."""

    id: int
    creator: ProposalCreatorBriefOut
    note: str | None
    fa_number: str
    policy_type: str
    submission_date: date
    ocr_status: str
    underwriter_status: str
    final_status: str
    created_at: datetime
    updated_at: datetime
    documents: list[ProposalDocumentOut] = Field(default_factory=list)
