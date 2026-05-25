from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProposalCreatedEvent:
    proposal_id: int
    proposal_fa_number: str
    creator_id: int


@dataclass(frozen=True, slots=True)
class ProposalApprovedEvent:
    proposal_id: int
    proposal_fa_number: str
    creator_id: int
    actor_user_id: int


@dataclass(frozen=True, slots=True)
class ProposalRejectedEvent:
    proposal_id: int
    proposal_fa_number: str
    creator_id: int
    actor_user_id: int
    reason: str | None = None
    notes: str | None = None


DomainEvent = ProposalCreatedEvent | ProposalApprovedEvent | ProposalRejectedEvent
DomainEventHandler = Callable[[Any], None]


class DomainEventDispatcher:
    """Tiny in-process dispatcher to keep business actions decoupled from notification delivery."""

    def __init__(self) -> None:
        self._handlers: dict[type[Any], list[DomainEventHandler]] = defaultdict(list)

    def register(self, event_type: type[Any], handler: DomainEventHandler) -> None:
        self._handlers[event_type].append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)
