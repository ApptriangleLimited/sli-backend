from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.modules.notifications.dto import NotificationDispatchDTO
from app.modules.notifications.interfaces import NotificationChannel
from app.modules.notifications.repository import NotificationRepository


class DatabaseNotificationChannel:
    """Default persistent channel backed by the notifications table."""

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    def send(self, *, user_ids: list[int], payload: NotificationDispatchDTO) -> None:
        unique_ids = list(dict.fromkeys(user_ids))
        if not unique_ids:
            return
        self._repository.create_many(user_ids=unique_ids, payload=payload)


class NotificationService:
    def __init__(
        self,
        db: Session,
        *,
        repository: NotificationRepository | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> None:
        self._db = db
        self._repository = repository or NotificationRepository(db)
        self._channels = channels or [DatabaseNotificationChannel(self._repository)]

    def send_to_user(self, *, user_id: int, payload: NotificationDispatchDTO) -> None:
        self.send_to_users(user_ids=[user_id], payload=payload)

    def send_to_users(self, *, user_ids: list[int], payload: NotificationDispatchDTO) -> None:
        for channel in self._channels:
            channel.send(user_ids=user_ids, payload=payload)

    def get_user_notifications(
        self,
        *,
        user_id: int,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: int | None,
        unread: bool | None,
        notification_type: str | None,
        created_from: date | None,
        created_to: date | None,
    ) -> tuple[list[Notification], int, bool]:
        rows = self._repository.list_for_user(
            user_id,
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
            unread=unread,
            notification_type=notification_type,
            created_from=created_from,
            created_to=created_to,
        )
        has_more = len(rows) > limit
        page = rows[:limit]
        total = self._repository.count_for_user(
            user_id,
            unread=unread,
            notification_type=notification_type,
            created_from=created_from,
            created_to=created_to,
        )
        return page, total, has_more

    def mark_as_read(self, *, user_id: int, notification_id: int) -> Notification | None:
        notification = self._repository.get_for_user(notification_id, user_id)
        if not notification:
            return None
        self._repository.mark_read(notification)
        self._db.commit()
        self._db.refresh(notification)
        return notification

    def mark_all_as_read(self, *, user_id: int) -> int:
        marked_count = self._repository.mark_all_read(user_id)
        self._db.commit()
        return marked_count

    def get_unread_count(self, *, user_id: int) -> int:
        return self._repository.count_unread(user_id)
