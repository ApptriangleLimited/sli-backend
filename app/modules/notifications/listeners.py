from sqlalchemy.orm import Session

from app.modules.notifications.dto import NotificationDispatchDTO
from app.modules.notifications.enums import NotificationReferenceType, NotificationType
from app.modules.notifications.events import (
    DomainEventDispatcher,
    ProposalApprovedEvent,
    ProposalCreatedEvent,
    ProposalRejectedEvent,
)
from app.modules.notifications.service import NotificationService
from app.services.user_service import UserService


class ProposalNotificationListener:
    """Maps proposal domain events into user-facing notification records."""

    def __init__(self, db: Session) -> None:
        self._notifications = NotificationService(db)
        self._users = UserService(db)

    def handle_proposal_created(self, event: ProposalCreatedEvent) -> None:
        underwriters = self._users.list_active_by_role_slug("underwriter")
        recipient_ids = [user.id for user in underwriters if user.id != event.creator_id]
        if not recipient_ids:
            return

        creator = self._users.get_by_id(event.creator_id)
        creator_name = creator.name if creator else "An agent"
        payload = NotificationDispatchDTO(
            title="New proposal submitted",
            message=f"{creator_name} submitted proposal {event.proposal_fa_number} for review.",
            type=NotificationType.PROPOSAL_CREATED,
            reference_type=NotificationReferenceType.PROPOSAL,
            reference_id=event.proposal_id,
            actor_user_id=event.creator_id,
            data={
                "proposal_id": event.proposal_id,
                "fa_number": event.proposal_fa_number,
                "actor_name": creator_name,
                "channel_candidates": ["database", "realtime", "push", "email", "sms"],
            },
        )
        self._notifications.send_to_users(user_ids=recipient_ids, payload=payload)

    def handle_proposal_approved(self, event: ProposalApprovedEvent) -> None:
        actor = self._users.get_by_id(event.actor_user_id)
        actor_name = actor.name if actor else "An underwriter"
        payload = NotificationDispatchDTO(
            title="Proposal approved",
            message=f"{actor_name} approved proposal {event.proposal_fa_number}.",
            type=NotificationType.PROPOSAL_APPROVED,
            reference_type=NotificationReferenceType.PROPOSAL,
            reference_id=event.proposal_id,
            actor_user_id=event.actor_user_id,
            data={
                "proposal_id": event.proposal_id,
                "fa_number": event.proposal_fa_number,
                "actor_name": actor_name,
                "decision": "approved",
                "channel_candidates": ["database", "realtime", "push", "email", "sms"],
            },
        )
        self._notifications.send_to_user(user_id=event.creator_id, payload=payload)

    def handle_proposal_rejected(self, event: ProposalRejectedEvent) -> None:
        actor = self._users.get_by_id(event.actor_user_id)
        actor_name = actor.name if actor else "An underwriter"
        reason_suffix = f" Reason: {event.reason}." if event.reason else ""
        payload = NotificationDispatchDTO(
            title="Proposal rejected",
            message=f"{actor_name} rejected proposal {event.proposal_fa_number}.{reason_suffix}",
            type=NotificationType.PROPOSAL_REJECTED,
            reference_type=NotificationReferenceType.PROPOSAL,
            reference_id=event.proposal_id,
            actor_user_id=event.actor_user_id,
            data={
                "proposal_id": event.proposal_id,
                "fa_number": event.proposal_fa_number,
                "actor_name": actor_name,
                "decision": "rejected",
                "reason": event.reason,
                "notes": event.notes,
                "channel_candidates": ["database", "realtime", "push", "email", "sms"],
            },
        )
        self._notifications.send_to_user(user_id=event.creator_id, payload=payload)


def build_notification_dispatcher(db: Session) -> DomainEventDispatcher:
    listener = ProposalNotificationListener(db)
    dispatcher = DomainEventDispatcher()
    dispatcher.register(ProposalCreatedEvent, listener.handle_proposal_created)
    dispatcher.register(ProposalApprovedEvent, listener.handle_proposal_approved)
    dispatcher.register(ProposalRejectedEvent, listener.handle_proposal_rejected)
    return dispatcher
