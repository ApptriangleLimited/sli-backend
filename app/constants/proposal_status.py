"""Canonical proposal status values shared across services and validation."""

UNDERWRITER_PENDING = "pending"
UNDERWRITER_IN_REVIEW = "in_review"
UNDERWRITER_NEEDS_INFO = "needs_info"
UNDERWRITER_APPROVED = "approved"
UNDERWRITER_REJECTED = "rejected"

FINAL_OPEN = "open"
FINAL_CLOSED_APPROVED = "closed_approved"
FINAL_CLOSED_REJECTED = "closed_rejected"
FINAL_VOID = "void"

TERMINAL_UNDERWRITER_STATUSES = frozenset({UNDERWRITER_APPROVED, UNDERWRITER_REJECTED})
