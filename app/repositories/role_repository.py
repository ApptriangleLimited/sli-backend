from sqlalchemy.orm import Session

from app.models.role import Role


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_slug(self, slug: str) -> Role | None:
        return self.db.query(Role).filter(Role.slug == slug).first()

    def get_by_name(self, name: str) -> Role | None:
        return self.db.query(Role).filter(Role.name == name).first()

    def create(self, name: str, slug: str, is_active: bool = True) -> Role:
        role = Role(name=name, slug=slug, is_active=is_active)
        self.db.add(role)
        self.db.flush()
        return role
