import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth_dependency import require_roles
from app.models.user import User
from app.repositories.proposal_repository import ProposalRepository
from app.schemas.proposal_schema import ProposalListEnvelope, ProposalOut
from app.services.proposal_service import ProposalService
from app.services.proposal_storage_service import ProposalStorageService
from app.utils.response import success_response

router = APIRouter(prefix="/api/agent", tags=["Agent proposals"])

_AGENT = Depends(require_roles("agent"))


def _parse_submission_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw.strip()[:10])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid submission_date") from exc


def _parse_ocr_json(raw: str | None) -> dict | list | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ocr_extracted_data must be valid JSON",
        ) from exc
    if parsed is not None and not isinstance(parsed, (dict, list)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ocr_extracted_data must be a JSON object or array",
        )
    return parsed


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
def create_proposal(
    document: UploadFile = File(..., description="Photo or scan of the proposal document"),
    fa_number: str = Form(..., min_length=1, max_length=120),
    policy_type: str = Form(..., min_length=1, max_length=120),
    submission_date: str = Form(..., description="ISO date YYYY-MM-DD"),
    note: str | None = Form(None, max_length=8000),
    ocr_extracted_data: str | None = Form(
        None,
        description="JSON string from mobile OCR (object or array)",
    ),
    db: Session = Depends(get_db),
    current_user: User = _AGENT,
):
    sub_date = _parse_submission_date(submission_date)
    ocr_payload = _parse_ocr_json(ocr_extracted_data)
    try:
        proposal = ProposalService(db).create_with_document(
            creator_id=current_user.id,
            note=note,
            fa_number=fa_number,
            policy_type=policy_type,
            submission_date=sub_date,
            document=document,
            ocr_extracted_data=ocr_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return success_response(
        message="Proposal created",
        data={"proposal": ProposalOut.model_validate(proposal)},
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/proposals")
def list_my_proposals(
    limit: int = Query(50, ge=1, le=100),
    cursor_created_at: datetime | None = Query(None),
    cursor_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = _AGENT,
):
    if (cursor_created_at is None) ^ (cursor_id is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cursor_created_at and cursor_id must be sent together",
        )

    items, total, has_more = ProposalService(db).list_mine_keyset(
        current_user.id,
        limit=limit,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
    )

    next_ca: datetime | None = None
    next_cid: int | None = None
    if has_more and items:
        tail = items[-1]
        next_ca = tail.created_at
        next_cid = tail.id

    envelope = ProposalListEnvelope(
        items=[ProposalOut.model_validate(p) for p in items],
        total=total,
        has_more=has_more,
        next_cursor_created_at=next_ca,
        next_cursor_id=next_cid,
    )
    return success_response(message="Proposals fetched", data=envelope.model_dump())


@router.get("/proposals/{proposal_id}")
def get_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = _AGENT,
):
    proposal = ProposalRepository(db).get_owned(proposal_id, current_user.id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return success_response(message="Proposal fetched", data={"proposal": ProposalOut.model_validate(proposal)})


@router.get("/proposals/{proposal_id}/documents/{document_id}/file")
def download_document(
    proposal_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = _AGENT,
):
    repo = ProposalRepository(db)
    doc = repo.get_document_owned(proposal_id, document_id, current_user.id)
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
