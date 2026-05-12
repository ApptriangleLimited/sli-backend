from sqlalchemy.orm import Session

from app.services.role_service import RoleService

DEFAULT_ROLES = [
    {"name": "Agent", "slug": "agent"},
    {"name": "Underwriter", "slug": "underwriter"},
    {"name": "Admin", "slug": "admin"},
]


def seed_default_roles(db: Session) -> None:
    service = RoleService(db)
    for role in DEFAULT_ROLES:
        service.get_or_create_role(name=role["name"], slug=role["slug"])
    db.commit()
