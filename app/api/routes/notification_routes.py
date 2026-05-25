from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.modules.notifications.dto import (
    NotificationListEnvelope,
    NotificationOut,
    NotificationReadAllResultOut,
    NotificationsUnreadCountOut,
)
from app.modules.notifications.service import NotificationService
from app.utils.response import success_response

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    cursor_created_at: datetime | None = Query(None),
    cursor_id: int | None = Query(None, ge=1),
    unread: bool | None = Query(None),
    type: str | None = Query(None, max_length=64),
    created_from: date | None = Query(None),
    created_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if (cursor_created_at is None) ^ (cursor_id is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cursor_created_at and cursor_id must be sent together",
        )

    items, total, has_more = NotificationService(db).get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
        unread=unread,
        notification_type=type,
        created_from=created_from,
        created_to=created_to,
    )
    next_ca: datetime | None = None
    next_cid: int | None = None
    if has_more and items:
        tail = items[-1]
        next_ca = tail.created_at
        next_cid = tail.id

    envelope = NotificationListEnvelope(
        items=[NotificationOut.model_validate(item) for item in items],
        total=total,
        has_more=has_more,
        next_cursor_created_at=next_ca,
        next_cursor_id=next_cid,
    )
    return success_response(message="Notifications fetched", data=envelope.model_dump())


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = NotificationService(db).mark_as_read(
        user_id=current_user.id,
        notification_id=notification_id,
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return success_response(
        message="Notification marked as read",
        data={"notification": NotificationOut.model_validate(notification).model_dump()},
    )


@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    marked_count = NotificationService(db).mark_all_as_read(user_id=current_user.id)
    payload = NotificationReadAllResultOut(marked_count=marked_count)
    return success_response(message="Notifications marked as read", data=payload.model_dump())


@router.get("/unread-count")
def get_unread_notifications_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = NotificationsUnreadCountOut(count=NotificationService(db).get_unread_count(user_id=current_user.id))
    return success_response(message="Unread notification count fetched", data=payload.model_dump())
