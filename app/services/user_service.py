from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.role_service import RoleService


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)
        self.role_service = RoleService(db)

    def get_by_id(self, user_id: int) -> User | None:
        return self.repository.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.repository.get_by_email(email)

    def create_user(self, name: str, email: str, password: str, role_slug: str) -> User:
        role_slug = role_slug.lower().strip()

        if self.repository.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        if role_slug == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin users cannot be created through public registration",
            )

        role = self.role_service.get_active_role_by_slug(role_slug)
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

        user = self.repository.create(
            name=name,
            email=email,
            password=hash_password(password),
            role_id=role.id,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_user_by_admin(
        self,
        name: str,
        email: str,
        password: str,
        role_slug: str,
        is_active: bool = True,
    ) -> User:
        role_slug = role_slug.lower().strip()

        if self.repository.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        role = self.role_service.get_active_role_by_slug(role_slug)
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

        user = self.repository.create(
            name=name,
            email=email,
            password=hash_password(password),
            role_id=role.id,
            is_active=is_active,
        )
        self.db.commit()
        self.db.refresh(user)
        return user
