from dataclasses import dataclass

from fastapi import UploadFile


@dataclass(frozen=True, slots=True)
class ProposalDocumentUploadItem:
    """One validated file slot from multipart create proposal."""

    file: UploadFile
    section_type: str
    document_type: str
    side: str | None
    nominee_index: int | None
    document_group_id: str | None


@dataclass(frozen=True, slots=True)
class ProposalDocumentUploadBundle:
    """Ordered document uploads for persistence (application → applicant → nominee → guardian)."""

    items: tuple[ProposalDocumentUploadItem, ...]
