from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

DEFAULT_ADMIN_EMAIL = "admin@apptriangle.com"
DEFAULT_ADMIN_PASSWORD = "admin@3$!12313__)("


def seed_default_admin(db: Session) -> None:
    user_repository = UserRepository(db)
    if user_repository.get_by_email(DEFAULT_ADMIN_EMAIL):
        return

    admin_role = RoleRepository(db).get_by_slug("admin")
    if not admin_role:
        raise RuntimeError("Admin role missing. Seed default roles before default admin.")

    user_repository.create(
        name="Default Admin",
        email=DEFAULT_ADMIN_EMAIL,
        password=hash_password(DEFAULT_ADMIN_PASSWORD),
        role_id=admin_role.id,
    )
    db.commit()
