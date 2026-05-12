from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminCreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role_slug: str = Field(min_length=2, max_length=100)
    is_active: bool = True


class RoleOut(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime
    role: RoleOut

    model_config = ConfigDict(from_attributes=True)
