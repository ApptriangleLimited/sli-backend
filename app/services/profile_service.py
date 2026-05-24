from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserOut
from app.services.profile_storage_service import ProfileStorageService


def user_to_out(user: User) -> UserOut:
    return UserOut.model_validate(user).model_copy(
        update={
            "has_profile_image": bool(user.profile_image_path),
        }
    )


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.storage = ProfileStorageService()

    def update_profile(
        self,
        user: User,
        *,
        name: str | None,
        phone: str | None,
        avatar: UploadFile | None,
        remove_avatar: bool,
    ) -> User:
        changed = False

        if name is not None:
            trimmed = name.strip()
            if len(trimmed) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Name must be at least 2 characters",
                )
            if trimmed != user.name:
                user.name = trimmed
                changed = True

        if phone is not None:
            normalized = phone.strip() or None
            if normalized != user.phone:
                user.phone = normalized
                changed = True

        if remove_avatar and user.profile_image_path:
            self.storage.delete_file(user.profile_image_path)
            user.profile_image_path = None
            changed = True

        if avatar is not None and avatar.filename:
            try:
                if user.profile_image_path:
                    self.storage.delete_file(user.profile_image_path)
                relative, _ = self.storage.persist_avatar(avatar, user.id)
                user.profile_image_path = relative
                changed = True
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc

        if changed:
            self.db.commit()
            self.db.refresh(user)
            user = self.users.get_by_id(user.id) or user

        return user

    def get_avatar_file(self, user: User) -> tuple[str, str]:
        if not user.profile_image_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile image not set",
            )
        try:
            path = self.storage.absolute_path(user.profile_image_path)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile image file missing",
            )
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), "application/octet-stream")
        return str(path), content_type
