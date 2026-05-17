import re
from collections import defaultdict
from typing import Any

from fastapi import UploadFile
from starlette.datastructures import FormData, UploadFile as StarletteUploadFile

from app.schemas.proposal_document_upload import ProposalDocumentUploadBundle

_RE_APPLICATION = re.compile(r"^application_documents\[(\d+)\]\[(file|document_type)\]$")
_RE_APPLICANT = re.compile(r"^applicant_documents\[(\d+)\]\[(file|document_type|side)\]$")
_RE_NOMINEE = re.compile(r"^nominees\[(\d+)\]\[documents\]\[(\d+)\]\[(file|document_type|side)\]$")
_RE_GUARDIAN = re.compile(r"^guardian_documents\[(\d+)\]\[(file|document_type|side)\]$")


def _is_upload(value: Any) -> bool:
    return isinstance(value, (UploadFile, StarletteUploadFile))


def _slot_key(section: str, index: int, nominee_index: int | None = None) -> tuple:
    return (section, index, nominee_index)


class _Slot:
    __slots__ = ("file", "document_type", "side")

    def __init__(self) -> None:
        self.file: UploadFile | None = None
        self.document_type: str | None = None
        self.side: str | None = None


def parse_proposal_documents_from_form(form: FormData) -> ProposalDocumentUploadBundle:

    application: dict[int, _Slot] = defaultdict(_Slot)
    applicant: dict[int, _Slot] = defaultdict(_Slot)
    nominee: dict[tuple[int, int], _Slot] = defaultdict(_Slot)
    guardian: dict[int, _Slot] = defaultdict(_Slot)

    for key, value in form.multi_items():
        m = _RE_APPLICATION.match(key)
        if m:
            idx = int(m.group(1))
            field = m.group(2)
            slot = application[idx]
            if field == "file" and _is_upload(value):
                slot.file = value  # type: ignore[assignment]
            elif field == "document_type" and isinstance(value, str):
                slot.document_type = value.strip()
            continue

        m = _RE_APPLICANT.match(key)
        if m:
            idx = int(m.group(1))
            field = m.group(2)
            slot = applicant[idx]
            if field == "file" and _is_upload(value):
                slot.file = value  # type: ignore[assignment]
            elif field == "document_type" and isinstance(value, str):
                slot.document_type = value.strip()
            elif field == "side" and isinstance(value, str):
                slot.side = value.strip() or None
            continue

        m = _RE_NOMINEE.match(key)
        if m:
            nom_idx = int(m.group(1))
            doc_idx = int(m.group(2))
            field = m.group(3)
            slot = nominee[(nom_idx, doc_idx)]
            if field == "file" and _is_upload(value):
                slot.file = value  # type: ignore[assignment]
            elif field == "document_type" and isinstance(value, str):
                slot.document_type = value.strip()
            elif field == "side" and isinstance(value, str):
                slot.side = value.strip() or None
            continue

        m = _RE_GUARDIAN.match(key)
        if m:
            idx = int(m.group(1))
            field = m.group(2)
            slot = guardian[idx]
            if field == "file" and _is_upload(value):
                slot.file = value  # type: ignore[assignment]
            elif field == "document_type" and isinstance(value, str):
                slot.document_type = value.strip()
            elif field == "side" and isinstance(value, str):
                slot.side = value.strip() or None
            continue

    from app.services.proposal_document_validation_service import ProposalDocumentValidationService

    return ProposalDocumentValidationService.build_bundle(
        application_slots=application,
        applicant_slots=applicant,
        nominee_slots=nominee,
        guardian_slots=guardian,
    )
