from datetime import date, datetime
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class ProposalDocumentOut(BaseModel):
    id: int
    section_type: str
    document_type: str
    side: str | None = None
    nominee_index: int | None = None
    document_group_id: str | None = None
    original_filename: str
    content_type: str
    size_bytes: int
    ocr_extracted_data: Any | None = Field(
        None,
        description="OCR payload as JSON (object or array). String values are parsed when possible.",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("ocr_extracted_data", mode="before")
    @classmethod
    def coerce_ocr_to_json(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                return None
            return parsed if isinstance(parsed, (dict, list)) else None
        return v


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

    @computed_field
    @property
    def ocr_by_document(self) -> list[dict[str, Any]]:
        """Per-file OCR as JSON-friendly rows for the review UI (mirrors documents[].ocr_extracted_data)."""
        return [
            {
                "document_id": d.id,
                "section_type": d.section_type,
                "document_type": d.document_type,
                "side": d.side,
                "nominee_index": d.nominee_index,
                "document_group_id": d.document_group_id,
                "original_filename": d.original_filename,
                "ocr_extracted_data": d.ocr_extracted_data,
            }
            for d in self.documents
        ]
