from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth_dependency import require_roles
from app.models.user import User
from app.repositories.proposal_repository import ProposalRepository
from app.schemas.proposal_schema import ProposalUnderwriterTableEnvelope
from app.services.proposal_storage_service import ProposalStorageService
from app.services.underwriter_proposal_service import UnderwriterProposalService
from app.utils.response import success_response

router = APIRouter(prefix="/api/underwriter", tags=["Underwriter proposals"])

_UNDERWRITER_OR_ADMIN = Depends(require_roles("underwriter", "admin"))


@router.get("/proposals")
def list_proposals_table(
    limit: int = Query(50, ge=1, le=100),
    cursor_created_at: datetime | None = Query(None),
    cursor_id: int | None = Query(None, ge=1),
    underwriter_status: str | None = Query(None, max_length=32),
    final_status: str | None = Query(None, max_length=32),
    search: str | None = Query(None, description="Case-insensitive FA number contains", max_length=120),
    db: Session = Depends(get_db),
    _uw: User = _UNDERWRITER_OR_ADMIN,
):
    if (cursor_created_at is None) ^ (cursor_id is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cursor_created_at and cursor_id must be sent together",
        )

    items, total, has_more = UnderwriterProposalService(db).list_table_keyset(
        limit=limit,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
        underwriter_status=underwriter_status,
        final_status=final_status,
        search=search,
    )

    next_ca: datetime | None = None
    next_cid: int | None = None
    if has_more and items:
        tail = items[-1]
        next_ca = tail.created_at
        next_cid = tail.id

    envelope = ProposalUnderwriterTableEnvelope(
        items=items,
        total=total,
        has_more=has_more,
        next_cursor_created_at=next_ca,
        next_cursor_id=next_cid,
    )
    return success_response(message="Proposals fetched", data=envelope.model_dump())


@router.get("/proposals/{proposal_id}")
def get_proposal_detail(
    proposal_id: int,
    db: Session = Depends(get_db),
    _uw: User = _UNDERWRITER_OR_ADMIN,
):
    detail = UnderwriterProposalService(db).get_detail(proposal_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return success_response(
        message="Proposal fetched",
        data={"proposal": detail.model_dump()},
    )


@router.get("/proposals/{proposal_id}/documents/{document_id}/file")
def download_document(
    proposal_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    _uw: User = _UNDERWRITER_OR_ADMIN,
):
    doc = ProposalRepository(db).get_document_for_underwriter(proposal_id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    storage = ProposalStorageService()
    try:
        path = storage.absolute_path(doc.storage_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on server")

    return FileResponse(
        path,
        media_type=doc.content_type,
        filename=doc.original_filename,
    )
