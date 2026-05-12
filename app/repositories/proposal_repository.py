from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.proposal import Proposal, ProposalDocument
from app.models.user import User


class ProposalRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, proposal: Proposal) -> Proposal:
        self._db.add(proposal)
        self._db.flush()
        return proposal

    def add_document(self, document: ProposalDocument) -> ProposalDocument:
        self._db.add(document)
        self._db.flush()
        return document

    def get_owned(self, proposal_id: int, owner_user_id: int) -> Proposal | None:
        stmt: Select[tuple[Proposal]] = (
            select(Proposal)
            .where(Proposal.id == proposal_id, Proposal.created_by_id == owner_user_id)
            .options(selectinload(Proposal.documents))
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_creator(
        self,
        created_by_id: int,
        *,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: int | None,
    ) -> list[Proposal]:
        stmt = (
            select(Proposal)
            .where(Proposal.created_by_id == created_by_id)
            .options(selectinload(Proposal.documents))
            .order_by(Proposal.created_at.desc(), Proposal.id.desc())
            .limit(limit)
        )
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                (Proposal.created_at < cursor_created_at)
                | ((Proposal.created_at == cursor_created_at) & (Proposal.id < cursor_id))
            )
        return list(self._db.execute(stmt).scalars().all())

    def count_for_creator(self, created_by_id: int) -> int:
        stmt = select(func.count()).select_from(Proposal).where(Proposal.created_by_id == created_by_id)
        return int(self._db.execute(stmt).scalar_one())

    def _underwriter_table_filters(
        self,
        stmt,
        *,
        underwriter_status: str | None,
        final_status: str | None,
        search: str | None,
    ):
        if underwriter_status:
            stmt = stmt.where(Proposal.underwriter_status == underwriter_status)
        if final_status:
            stmt = stmt.where(Proposal.final_status == final_status)
        if search:
            s = search.strip()[:120].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Proposal.fa_number.ilike(f"%{s}%", escape="\\"))
        return stmt

    def count_for_underwriter_table(
        self,
        *,
        underwriter_status: str | None,
        final_status: str | None,
        search: str | None,
    ) -> int:
        stmt = select(func.count()).select_from(Proposal)
        stmt = self._underwriter_table_filters(
            stmt,
            underwriter_status=underwriter_status,
            final_status=final_status,
            search=search,
        )
        return int(self._db.execute(stmt).scalar_one())

    def list_for_underwriter_table(
        self,
        *,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: int | None,
        underwriter_status: str | None,
        final_status: str | None,
        search: str | None,
    ) -> list[tuple[Proposal, str, str, int]]:
        doc_count_sq = (
            select(func.count(ProposalDocument.id))
            .where(ProposalDocument.proposal_id == Proposal.id)
            .correlate(Proposal)
            .scalar_subquery()
        )
        stmt = (
            select(Proposal, User.name, User.email, doc_count_sq)
            .join(User, User.id == Proposal.created_by_id)
            .order_by(Proposal.created_at.desc(), Proposal.id.desc())
            .limit(limit)
        )
        stmt = self._underwriter_table_filters(
            stmt,
            underwriter_status=underwriter_status,
            final_status=final_status,
            search=search,
        )
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                (Proposal.created_at < cursor_created_at)
                | ((Proposal.created_at == cursor_created_at) & (Proposal.id < cursor_id))
            )
        rows = self._db.execute(stmt).all()
        return [(r[0], str(r[1]), str(r[2]), int(r[3])) for r in rows]

    def get_by_id_with_creator_and_documents(self, proposal_id: int) -> Proposal | None:
        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(selectinload(Proposal.documents), selectinload(Proposal.creator))
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_document_for_underwriter(self, proposal_id: int, document_id: int) -> ProposalDocument | None:
        stmt = select(ProposalDocument).where(
            ProposalDocument.id == document_id,
            ProposalDocument.proposal_id == proposal_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_document_owned(
        self, proposal_id: int, document_id: int, owner_user_id: int
    ) -> ProposalDocument | None:
        stmt = (
            select(ProposalDocument)
            .join(Proposal, ProposalDocument.proposal_id == Proposal.id)
            .where(
                ProposalDocument.id == document_id,
                ProposalDocument.proposal_id == proposal_id,
                Proposal.created_by_id == owner_user_id,
            )
        )
        return self._db.execute(stmt).scalar_one_or_none()
