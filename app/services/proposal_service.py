from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.proposal import Proposal, ProposalDocument
from app.repositories.proposal_repository import ProposalRepository
from app.schemas.proposal_document_upload import ProposalDocumentUploadBundle, ProposalDocumentUploadItem
from app.services.proposal_storage_service import ProposalStorageService


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
        document_bundle: ProposalDocumentUploadBundle,
        ocr_extracted_data: dict | list | None,
    ) -> Proposal:
        items = document_bundle.items
        if not items:
            raise ValueError("At least one document file is required")

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
            for index, item in enumerate(items):
                rel_path, size = self._storage.persist_upload(item.file, proposal.id)
                rel_paths.append(rel_path)
                per_doc_ocr = ocr_extracted_data if index == 0 else None
                doc = ProposalDocument(
                    proposal_id=proposal.id,
                    section_type=item.section_type,
                    document_type=item.document_type,
                    side=item.side,
                    nominee_index=item.nominee_index,
                    document_group_id=item.document_group_id,
                    storage_path=rel_path,
                    original_filename=(item.file.filename or "upload")[:255],
                    content_type=(item.file.content_type or "application/octet-stream")
                    .split(";")[0]
                    .strip()[:120],
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
