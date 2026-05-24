from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.schemas.auth_schema import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.schemas.user_schema import UserOut
from app.services.auth_service import AuthService
from app.services.profile_service import user_to_out
from app.utils.response import success_response

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    result = AuthService(db).register(payload)
    return success_response(
        message="User registered successfully",
        data={"user": user_to_out(result["user"])},
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    result = AuthService(db).login(payload)
    result["user"] = user_to_out(result["user"])
    return success_response(message="Login successful", data=result)


@router.post("/refresh-token")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    result = AuthService(db).refresh_access_token(payload.refresh_token)
    result["user"] = user_to_out(result["user"])
    return success_response(message="Token refreshed successfully", data=result)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(
        message="Current user fetched successfully",
        data={"user": user_to_out(current_user)},
    )


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    AuthService(db).logout(payload.refresh_token)
    return success_response(message="Logged out successfully")
