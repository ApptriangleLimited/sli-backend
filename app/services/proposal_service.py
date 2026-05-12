from datetime import date, datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.proposal import Proposal, ProposalDocument
from app.repositories.proposal_repository import ProposalRepository
from app.services.proposal_storage_service import ProposalStorageService

# Max files per POST /api/agent/proposals (same multipart request).
MAX_PROPOSAL_DOCUMENTS_PER_REQUEST = 20


class ProposalService:
    def __init__(
        self,
        db: Session,
        storage: ProposalStorageService | None = None,
    ) -> None:
        self._db = db
        self._repo = ProposalRepository(db)
        self._storage = storage or ProposalStorageService()

    def create_with_documents(
        self,
        *,
        creator_id: int,
        note: str | None,
        fa_number: str,
        policy_type: str,
        submission_date: date,
        documents: list[UploadFile],
        ocr_extracted_data: dict | list | None,
    ) -> Proposal:
        if not documents:
            raise ValueError("At least one document file is required")
        if len(documents) > MAX_PROPOSAL_DOCUMENTS_PER_REQUEST:
            raise ValueError(
                f"At most {MAX_PROPOSAL_DOCUMENTS_PER_REQUEST} documents allowed per proposal submission",
            )

        ocr_status = "pending"
        if ocr_extracted_data is not None:
            ocr_status = "completed"

        proposal = Proposal(
            created_by_id=creator_id,
            note=note,
            fa_number=fa_number.strip(),
            policy_type=policy_type.strip(),
            submission_date=submission_date,
            ocr_status=ocr_status,
            underwriter_status="pending",
            final_status="open",
        )
        self._repo.add(proposal)

        rel_paths: list[str] = []
        try:
            for index, document in enumerate(documents):
                rel_path, size = self._storage.persist_upload(document, proposal.id)
                rel_paths.append(rel_path)
                # Single optional JSON payload (existing API): attach to first file only.
                per_doc_ocr = ocr_extracted_data if index == 0 else None
                doc = ProposalDocument(
                    proposal_id=proposal.id,
                    storage_path=rel_path,
                    original_filename=(document.filename or "upload")[:255],
                    content_type=(document.content_type or "application/octet-stream").split(";")[0].strip()[:120],
                    size_bytes=size,
                    ocr_extracted_data=per_doc_ocr,
                )
                self._repo.add_document(doc)
            self._db.commit()
        except Exception:
            self._db.rollback()
            for p in rel_paths:
                self._storage.delete_file(p)
            raise

        self._db.refresh(proposal)
        return proposal

    def list_mine_keyset(
        self,
        creator_id: int,
        *,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: int | None,
    ) -> tuple[list[Proposal], int, bool]:
        rows = self._repo.list_for_creator(
            creator_id,
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        has_more = len(rows) > limit
        page = rows[:limit]
        total = self._repo.count_for_creator(creator_id)
        return page, total, has_more
