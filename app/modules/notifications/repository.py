from datetime import date, datetime, timezone

from sqlalchemy import Date, cast, func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.modules.notifications.dto import NotificationDispatchDTO


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_many(self, *, user_ids: list[int], payload: NotificationDispatchDTO) -> list[Notification]:
        notifications = [
            Notification(
                user_id=user_id,
                actor_user_id=payload.actor_user_id,
                title=payload.title,
                message=payload.message,
                type=payload.type,
                reference_type=payload.reference_type,
                reference_id=payload.reference_id,
                data=payload.data,
            )
            for user_id in user_ids
        ]
        self._db.add_all(notifications)
        self._db.flush()
        return notifications

    def list_for_user(
        self,
        user_id: int,
        *,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: int | None,
        unread: bool | None,
        notification_type: str | None,
        created_from: date | None,
        created_to: date | None,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        )
        stmt = self._apply_filters(
            stmt,
            unread=unread,
            notification_type=notification_type,
            created_from=created_from,
            created_to=created_to,
        )
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                (Notification.created_at < cursor_created_at)
                | ((Notification.created_at == cursor_created_at) & (Notification.id < cursor_id))
            )
        return list(self._db.execute(stmt).scalars().all())

    def count_for_user(
        self,
        user_id: int,
        *,
        unread: bool | None,
        notification_type: str | None,
        created_from: date | None,
        created_to: date | None,
    ) -> int:
        stmt = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        stmt = self._apply_filters(
            stmt,
            unread=unread,
            notification_type=notification_type,
            created_from=created_from,
            created_to=created_to,
        )
        return int(self._db.execute(stmt).scalar_one())

    def count_unread(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return int(self._db.execute(stmt).scalar_one())

    def get_for_user(self, notification_id: int, user_id: int) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def mark_read(self, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            self._db.flush()
        return notification

    def mark_all_read(self, user_id: int) -> int:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=func.now())
        )
        result = self._db.execute(stmt)
        self._db.flush()
        return int(result.rowcount or 0)

    @staticmethod
    def _apply_filters(
        stmt,
        *,
        unread: bool | None,
        notification_type: str | None,
        created_from: date | None,
        created_to: date | None,
    ):
        if unread is not None:
            stmt = stmt.where(Notification.is_read.is_(False if unread else True))
        if notification_type:
            stmt = stmt.where(Notification.type == notification_type)
        if created_from is not None:
            stmt = stmt.where(cast(Notification.created_at, Date) >= created_from)
        if created_to is not None:
            stmt = stmt.where(cast(Notification.created_at, Date) <= created_to)
        return stmt
