from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

DEFAULT_UNDERWRITER_EMAIL = "underwriter@apptriangle.com"
DEFAULT_UNDERWRITER_PASSWORD = "password123"


def seed_default_underwriter(db: Session) -> None:
    user_repository = UserRepository(db)
    if user_repository.get_by_email(DEFAULT_UNDERWRITER_EMAIL):
        return

    underwriter_role = RoleRepository(db).get_by_slug("underwriter")
    if not underwriter_role:
        raise RuntimeError("Underwriter role missing. Seed default roles before default underwriter.")

    user_repository.create(
        name="Default Underwriter",
        email=DEFAULT_UNDERWRITER_EMAIL,
        password=hash_password(DEFAULT_UNDERWRITER_PASSWORD),
        role_id=underwriter_role.id,
    )
    db.commit()
