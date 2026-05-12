from sqlalchemy.orm import Session, joinedload

from app.models.refresh_token import RefreshToken
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(self, email: str) -> User | None:
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.email == email.lower())
            .first()
        )

    def create(
        self,
        name: str,
        email: str,
        password: str,
        role_id: int,
        is_active: bool = True,
    ) -> User:
        user = User(
            name=name,
            email=email.lower(),
            password=password,
            role_id=role_id,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def create_refresh_token(self, user_id: int, token: str, expires_at) -> RefreshToken:
        refresh_token = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def get_refresh_token(self, token: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(RefreshToken.token == token).first()

    def revoke_refresh_token(self, token: str) -> None:
        refresh_token = self.get_refresh_token(token)
        if refresh_token:
            refresh_token.is_revoked = True
            self.db.flush()
