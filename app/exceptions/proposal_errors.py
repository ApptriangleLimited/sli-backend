class ProposalNotFoundError(Exception):
    """Raised when a proposal id does not exist."""


class ProposalDecisionConflictError(Exception):
    """Raised when an underwriter decision cannot be applied to the current state."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
