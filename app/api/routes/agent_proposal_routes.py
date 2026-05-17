import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.datastructures import FormData

from app.core.database import get_db
from app.dependencies.auth_dependency import require_roles
from app.models.user import User
from app.repositories.proposal_repository import ProposalRepository
from app.schemas.proposal_schema import ProposalListEnvelope, ProposalOut
from app.services.proposal_document_multipart_parser import parse_proposal_documents_from_form
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


def _ensure_multipart_request(request: Request, form: FormData) -> None:
    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" in content_type:
        return
    if "application/json" in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "POST /api/agent/proposals requires multipart/form-data, not application/json. "
                "Send fa_number, policy_type, submission_date, and document sections as form "
                "fields; attach files on keys like application_documents[0][file]."
            ),
        )
    if not list(form.keys()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Missing multipart form fields. Use Content-Type multipart/form-data with "
                "fa_number, policy_type, submission_date, and document section fields "
                "(not a raw JSON body)."
            ),
        )


def _form_str(form: FormData, key: str, *, required: bool = True) -> str | None:
    value = form.get(key)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{key} is required (send as a form-data text field, not JSON body)",
            )
        return None
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{key} must be a text field",
        )
    return value


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
async def create_proposal(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = _AGENT,
):
    form = await request.form()
    _ensure_multipart_request(request, form)

    fa_raw = _form_str(form, "fa_number")
    policy_raw = _form_str(form, "policy_type")
    submission_raw = _form_str(form, "submission_date")
    note_raw = _form_str(form, "note", required=False)
    ocr_raw = form.get("ocr_extracted_data")
    ocr_str = ocr_raw if isinstance(ocr_raw, str) else None

    sub_date = _parse_submission_date(submission_raw)  # type: ignore[arg-type]
    ocr_payload = _parse_ocr_json(ocr_str)

    try:
        document_bundle = parse_proposal_documents_from_form(form)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        proposal = ProposalService(db).create_with_documents(
            creator_id=current_user.id,
            note=note_raw,
            fa_number=fa_raw,  # type: ignore[arg-type]
            policy_type=policy_raw,  # type: ignore[arg-type]
            submission_date=sub_date,
            document_bundle=document_bundle,
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
