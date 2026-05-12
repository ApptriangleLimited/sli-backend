from sqlalchemy.orm import Session

from app.models.role import Role
from app.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self, db: Session):
        self.repository = RoleRepository(db)

    def get_active_role_by_slug(self, slug: str) -> Role | None:
        role = self.repository.get_by_slug(slug)
        if not role or not role.is_active:
            return None
        return role

    def get_or_create_role(self, name: str, slug: str) -> Role:
        role = self.repository.get_by_slug(slug)
        if role:
            return role
        return self.repository.create(name=name, slug=slug)
