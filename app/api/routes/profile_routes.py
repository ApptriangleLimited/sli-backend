from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.services.profile_service import ProfileService, user_to_out
from app.utils.response import success_response

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.patch("")
async def update_profile(
    name: str | None = Form(default=None),
    phone: str | None = Form(default=None),
    remove_avatar: bool = Form(default=False),
    avatar: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = ProfileService(db).update_profile(
        current_user,
        name=name,
        phone=phone,
        avatar=avatar,
        remove_avatar=remove_avatar,
    )
    return success_response(
        message="Profile updated successfully",
        data={"user": user_to_out(user)},
    )


@router.get("/avatar")
def get_profile_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    path, media_type = ProfileService(db).get_avatar_file(current_user)
    return FileResponse(path, media_type=media_type, filename="avatar")
