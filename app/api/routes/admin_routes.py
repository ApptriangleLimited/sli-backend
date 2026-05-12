from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth_dependency import require_roles
from app.models.user import User
from app.schemas.user_schema import AdminCreateUserRequest, UserOut
from app.services.user_service import UserService
from app.utils.response import success_response

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/dashboard")
def admin_dashboard(current_user: User = Depends(require_roles("admin"))):
    return success_response(
        message="Admin dashboard access granted",
        data={
            "user": UserOut.model_validate(current_user),
            "stats": {
                "message": "Protected Admin-only dashboard endpoint",
            },
        },
    )


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = UserService(db).create_user_by_admin(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role_slug=payload.role_slug,
        is_active=payload.is_active,
    )
    return success_response(
        message="User created successfully",
        data={"user": UserOut.model_validate(user)},
        status_code=status.HTTP_201_CREATED,
    )
