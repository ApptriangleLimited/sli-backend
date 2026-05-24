"""Proposal document section and type rules for create API."""

from typing import Final

SECTION_APPLICATION: Final = "application"
SECTION_APPLICANT: Final = "applicant"
SECTION_NOMINEE: Final = "nominee"
SECTION_GUARDIAN: Final = "guardian"

SECTION_TYPES: Final = frozenset(
    {SECTION_APPLICATION, SECTION_APPLICANT, SECTION_NOMINEE, SECTION_GUARDIAN}
)

SIDE_FRONT: Final = "front"
SIDE_BACK: Final = "back"
SIDES: Final = frozenset({SIDE_FRONT, SIDE_BACK})

APPLICATION_DOCUMENT_TYPES: Final = frozenset({"application_form", "supporting_document"})

APPLICANT_DOCUMENT_TYPES: Final = frozenset(
    {
        "photo",
        "signature",
        "nid",
        "birth_certificate",
        "driving_license",
        "passport",
        "ssc_certificate",
    }
)

APPLICANT_PHOTO_TYPE: Final = "photo"
APPLICANT_SIGNATURE_TYPE: Final = "signature"
MAX_APPLICANT_PHOTOS: Final = 1
MAX_APPLICANT_SIGNATURES: Final = 1

NOMINEE_DOCUMENT_TYPES: Final = frozenset(
    {
        "photo",
        "nid",
        "birth_certificate",
        "driving_license",
        "passport",
        "ssc_certificate",
        "tika_card",
    }
)

# Legal Guardian section: Photo + Age Proof Document (identity supporting docs).
GUARDIAN_PHOTO_TYPE: Final = "photo"
GUARDIAN_AGE_PROOF_DOCUMENT_TYPES: Final = frozenset(
    {
        "birth_certificate",
        "nid",
        "driving_license",
        "passport",
        "ssc_certificate",
        "tika_card",
    }
)
GUARDIAN_DOCUMENT_TYPES: Final = GUARDIAN_AGE_PROOF_DOCUMENT_TYPES | {GUARDIAN_PHOTO_TYPE}

MAX_GUARDIAN_PHOTOS: Final = 1

DOCUMENT_TYPES_WITH_SIDES: Final = frozenset({"nid", "driving_license", "passport"})

MAX_APPLICATION_DOCUMENTS: Final = 8
MAX_NOMINEES: Final = 3
MAX_NOMINEE_PHOTOS: Final = 6

NOMINEE_PHOTO_TYPE: Final = "photo"
