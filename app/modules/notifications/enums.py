from enum import StrEnum


class NotificationType(StrEnum):
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"


class NotificationReferenceType(StrEnum):
    PROPOSAL = "proposal"


class NotificationChannelName(StrEnum):
    DATABASE = "database"
