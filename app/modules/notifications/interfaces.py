from collections.abc import Sequence
from typing import Protocol

from app.modules.notifications.dto import NotificationDispatchDTO


class NotificationChannel(Protocol):
    """Delivery channel contract used by NotificationService."""

    def send(self, *, user_ids: Sequence[int], payload: NotificationDispatchDTO) -> None: ...
