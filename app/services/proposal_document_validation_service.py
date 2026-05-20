import uuid
from collections import defaultdict

from app.constants.proposal_documents import (
    APPLICANT_DOCUMENT_TYPES,
    APPLICANT_PHOTO_TYPE,
    APPLICANT_SIGNATURE_TYPE,
    MAX_APPLICANT_SIGNATURES,
    APPLICATION_DOCUMENT_TYPES,
    DOCUMENT_TYPES_WITH_SIDES,
    GUARDIAN_DOCUMENT_TYPES,
    MAX_APPLICANT_PHOTOS,
    MAX_APPLICATION_DOCUMENTS,
    MAX_NOMINEE_PHOTOS,
    MAX_NOMINEES,
    NOMINEE_DOCUMENT_TYPES,
    NOMINEE_PHOTO_TYPE,
    SECTION_APPLICATION,
    SECTION_APPLICANT,
    SECTION_GUARDIAN,
    SECTION_NOMINEE,
    SIDE_BACK,
    SIDE_FRONT,
    SIDES,
)
from app.schemas.proposal_document_upload import ProposalDocumentUploadBundle, ProposalDocumentUploadItem
from app.services.proposal_document_multipart_parser import _Slot


class ProposalDocumentValidationService:
    @staticmethod
    def build_bundle(
        *,
        application_slots: dict[int, _Slot],
        applicant_slots: dict[int, _Slot],
        nominee_slots: dict[tuple[int, int], _Slot],
        guardian_slots: dict[int, _Slot],
    ) -> ProposalDocumentUploadBundle:
        items: list[ProposalDocumentUploadItem] = []

        app_items = ProposalDocumentValidationService._parse_section_slots(
            application_slots,
            section_type=SECTION_APPLICATION,
            allowed_types=APPLICATION_DOCUMENT_TYPES,
            nominee_index=None,
            label="application_documents",
        )
        if not app_items:
            raise ValueError("At least one application document is required")
        if len(app_items) > MAX_APPLICATION_DOCUMENTS:
            raise ValueError(f"At most {MAX_APPLICATION_DOCUMENTS} application documents allowed")

        applicant_items = ProposalDocumentValidationService._parse_section_slots(
            applicant_slots,
            section_type=SECTION_APPLICANT,
            allowed_types=APPLICANT_DOCUMENT_TYPES,
            nominee_index=None,
            label="applicant_documents",
        )
        if not applicant_items:
            raise ValueError("At least one applicant document is required")
        applicant_photo_count = sum(
            1 for item in applicant_items if item.document_type == APPLICANT_PHOTO_TYPE
        )
        if applicant_photo_count > MAX_APPLICANT_PHOTOS:
            raise ValueError(f"At most {MAX_APPLICANT_PHOTOS} applicant photo allowed")
        applicant_signature_count = sum(
            1 for item in applicant_items if item.document_type == APPLICANT_SIGNATURE_TYPE
        )
        if applicant_signature_count > MAX_APPLICANT_SIGNATURES:
            raise ValueError(f"At most {MAX_APPLICANT_SIGNATURES} applicant signature allowed")
        non_identity_applicant = [
            item
            for item in applicant_items
            if item.document_type not in (APPLICANT_PHOTO_TYPE, APPLICANT_SIGNATURE_TYPE)
        ]
        if not non_identity_applicant:
            raise ValueError(
                "At least one applicant identity document is required (e.g. nid, birth_certificate); "
                "photo or signature alone is not sufficient",
            )

        nominee_items, nominee_indices, nominee_photo_count = (
            ProposalDocumentValidationService._parse_nominee_slots(nominee_slots)
        )
        if nominee_indices and max(nominee_indices) >= MAX_NOMINEES:
            raise ValueError(f"At most {MAX_NOMINEES} nominees allowed (indices 0–{MAX_NOMINEES - 1})")
        if len(nominee_indices) > MAX_NOMINEES:
            raise ValueError(f"At most {MAX_NOMINEES} nominees allowed")
        if nominee_photo_count > MAX_NOMINEE_PHOTOS:
            raise ValueError(f"At most {MAX_NOMINEE_PHOTOS} nominee photo documents allowed")

        guardian_items = ProposalDocumentValidationService._parse_section_slots(
            guardian_slots,
            section_type=SECTION_GUARDIAN,
            allowed_types=GUARDIAN_DOCUMENT_TYPES,
            nominee_index=None,
            label="guardian_documents",
        )

        items.extend(app_items)
        items.extend(applicant_items)
        items.extend(nominee_items)
        items.extend(guardian_items)

        return ProposalDocumentUploadBundle(items=tuple(items))

    @staticmethod
    def _parse_nominee_slots(
        nominee_slots: dict[tuple[int, int], _Slot],
    ) -> tuple[list[ProposalDocumentUploadItem], set[int], int]:
        if not nominee_slots:
            return [], set(), 0

        nominee_indices: set[int] = set()
        photo_count = 0
        grouped: dict[int, list[tuple[int, _Slot]]] = defaultdict(list)

        for (nom_idx, doc_idx), slot in sorted(nominee_slots.items()):
            nominee_indices.add(nom_idx)
            grouped[nom_idx].append((doc_idx, slot))

        items: list[ProposalDocumentUploadItem] = []
        for nom_idx in sorted(grouped.keys()):
            for doc_idx, slot in sorted(grouped[nom_idx], key=lambda x: x[0]):
                item = ProposalDocumentValidationService._slot_to_item(
                    slot,
                    section_type=SECTION_NOMINEE,
                    allowed_types=NOMINEE_DOCUMENT_TYPES,
                    nominee_index=nom_idx,
                    label=f"nominees[{nom_idx}][documents][{doc_idx}]",
                )
                if item.document_type == NOMINEE_PHOTO_TYPE:
                    photo_count += 1
                items.append(item)

        return items, nominee_indices, photo_count

    @staticmethod
    def _parse_section_slots(
        slots: dict[int, _Slot],
        *,
        section_type: str,
        allowed_types: frozenset[str],
        nominee_index: int | None,
        label: str,
    ) -> list[ProposalDocumentUploadItem]:
        if not slots:
            return []

        items: list[ProposalDocumentUploadItem] = []
        for idx in sorted(slots.keys()):
            item = ProposalDocumentValidationService._slot_to_item(
                slots[idx],
                section_type=section_type,
                allowed_types=allowed_types,
                nominee_index=nominee_index,
                label=f"{label}[{idx}]",
            )
            items.append(item)
        return ProposalDocumentValidationService._assign_document_groups(items)

    @staticmethod
    def _slot_to_item(
        slot: _Slot,
        *,
        section_type: str,
        allowed_types: frozenset[str],
        nominee_index: int | None,
        label: str,
    ) -> ProposalDocumentUploadItem:
        if slot.file is None:
            raise ValueError(f"{label}[file] is required")
        if not slot.document_type:
            raise ValueError(f"{label}[document_type] is required")

        document_type = slot.document_type.strip().lower()
        if document_type not in allowed_types:
            raise ValueError(
                f"Unsupported document_type '{document_type}' for {label}; "
                f"allowed: {', '.join(sorted(allowed_types))}",
            )

        side = ProposalDocumentValidationService._normalize_side(
            slot.side,
            document_type=document_type,
            label=label,
        )

        return ProposalDocumentUploadItem(
            file=slot.file,
            section_type=section_type,
            document_type=document_type,
            side=side,
            nominee_index=nominee_index,
            document_group_id=None,
        )

    @staticmethod
    def _normalize_side(raw: str | None, *, document_type: str, label: str) -> str | None:
        if raw is None or raw.strip() == "":
            if document_type in DOCUMENT_TYPES_WITH_SIDES:
                return None
            return None

        side = raw.strip().lower()
        if side not in SIDES:
            raise ValueError(f"Invalid side '{raw}' for {label}; must be front or back")

        if document_type not in DOCUMENT_TYPES_WITH_SIDES:
            raise ValueError(f"side is not allowed for document_type '{document_type}' at {label}")

        return side

    @staticmethod
    def _assign_document_groups(items: list[ProposalDocumentUploadItem]) -> list[ProposalDocumentUploadItem]:
        """Pair front/back uploads with a shared document_group_id when applicable."""
        pending_front: dict[tuple[str, str, int | None], str] = {}
        result: list[ProposalDocumentUploadItem] = []

        for item in items:
            group_id = item.document_group_id
            if item.document_type in DOCUMENT_TYPES_WITH_SIDES and item.side:
                key = (item.section_type, item.document_type, item.nominee_index)
                if item.side == SIDE_FRONT:
                    group_id = str(uuid.uuid4())
                    pending_front[key] = group_id
                elif item.side == SIDE_BACK:
                    group_id = pending_front.pop(key, None) or str(uuid.uuid4())

            result.append(
                ProposalDocumentUploadItem(
                    file=item.file,
                    section_type=item.section_type,
                    document_type=item.document_type,
                    side=item.side,
                    nominee_index=item.nominee_index,
                    document_group_id=group_id,
                )
            )

        return result
