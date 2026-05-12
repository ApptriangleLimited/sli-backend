from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, RegisterRequest
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.user_service = UserService(db)

    def register(self, payload: RegisterRequest) -> dict:
        user = self.user_service.create_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role_slug=payload.role_slug,
        )
        return {"user": user}

    def login(self, payload: LoginRequest) -> dict:
        user = self.user_repository.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not user.is_active or not user.role.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

        return self._issue_tokens(user=user, remember_me=payload.remember_me)

    def refresh_access_token(self, refresh_token: str) -> dict:
        token_record = self.user_repository.get_refresh_token(refresh_token)
        if not token_record or token_record.is_revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if token_record.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user = self.user_repository.get_by_id(int(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token, expires_at = create_access_token(str(user.id), user.role.slug, access_expires)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int((expires_at - datetime.now(UTC)).total_seconds()),
            "user": user,
        }

    def logout(self, refresh_token: str | None) -> None:
        if refresh_token:
            self.user_repository.revoke_refresh_token(refresh_token)
            self.db.commit()

    def _issue_tokens(self, user: User, remember_me: bool) -> dict:
        access_expires = (
            timedelta(days=settings.REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS)
            if remember_me
            else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        access_token, access_expires_at = create_access_token(str(user.id), user.role.slug, access_expires)
        refresh_token, refresh_expires_at = create_refresh_token(str(user.id), refresh_expires)
        self.user_repository.create_refresh_token(user.id, refresh_token, refresh_expires_at)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int((access_expires_at - datetime.now(UTC)).total_seconds()),
            "user": user,
        }
