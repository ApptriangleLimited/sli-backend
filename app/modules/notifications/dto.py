from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationDispatchDTO(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    message: str = Field(..., min_length=1, max_length=4000)
    type: str = Field(..., min_length=1, max_length=64)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: int | None = Field(default=None, ge=1)
    actor_user_id: int | None = Field(default=None, ge=1)
    data: dict[str, Any] | None = None


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    reference_type: str | None = None
    reference_id: int | None = None
    is_read: bool
    data: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListEnvelope(BaseModel):
    items: list[NotificationOut]
    total: int
    has_more: bool
    next_cursor_created_at: datetime | None = None
    next_cursor_id: int | None = None


class NotificationsUnreadCountOut(BaseModel):
    count: int


class NotificationReadAllResultOut(BaseModel):
    marked_count: int


class NotificationListFilters(BaseModel):
    unread: bool | None = None
    type: str | None = Field(default=None, max_length=64)
    created_from: date | None = None
    created_to: date | None = None
