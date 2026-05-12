from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.proposal_repository import ProposalRepository
from app.schemas.proposal_schema import (
    ProposalCreatorBriefOut,
    ProposalDocumentOut,
    ProposalTableRowOut,
    ProposalUnderwriterDetailOut,
)


class UnderwriterProposalService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ProposalRepository(db)

    def list_table_keyset(
        self,
        *,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: int | None,
        underwriter_status: str | None,
        final_status: str | None,
        search: str | None,
    ) -> tuple[list[ProposalTableRowOut], int, bool]:
        rows = self._repo.list_for_underwriter_table(
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
            underwriter_status=underwriter_status,
            final_status=final_status,
            search=search,
        )
        has_more = len(rows) > limit
        page = rows[:limit]
        total = self._repo.count_for_underwriter_table(
            underwriter_status=underwriter_status,
            final_status=final_status,
            search=search,
        )
        items: list[ProposalTableRowOut] = []
        for proposal, creator_name, creator_email, doc_count in page:
            items.append(
                ProposalTableRowOut(
                    id=proposal.id,
                    creator=ProposalCreatorBriefOut(
                        id=proposal.created_by_id,
                        name=creator_name,
                        email=creator_email,
                    ),
                    note=proposal.note,
                    fa_number=proposal.fa_number,
                    policy_type=proposal.policy_type,
                    submission_date=proposal.submission_date,
                    ocr_status=proposal.ocr_status,
                    underwriter_status=proposal.underwriter_status,
                    final_status=proposal.final_status,
                    created_at=proposal.created_at,
                    updated_at=proposal.updated_at,
                    document_count=doc_count,
                )
            )
        return items, total, has_more

    def get_detail(self, proposal_id: int) -> ProposalUnderwriterDetailOut | None:
        proposal = self._repo.get_by_id_with_creator_and_documents(proposal_id)
        if not proposal or not proposal.creator:
            return None
        return ProposalUnderwriterDetailOut(
            id=proposal.id,
            creator=ProposalCreatorBriefOut(
                id=proposal.creator.id,
                name=proposal.creator.name,
                email=proposal.creator.email,
            ),
            note=proposal.note,
            fa_number=proposal.fa_number,
            policy_type=proposal.policy_type,
            submission_date=proposal.submission_date,
            ocr_status=proposal.ocr_status,
            underwriter_status=proposal.underwriter_status,
            final_status=proposal.final_status,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            documents=[ProposalDocumentOut.model_validate(d) for d in proposal.documents],
        )
