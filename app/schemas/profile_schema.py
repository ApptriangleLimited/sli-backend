from pydantic import BaseModel, Field


class ProfileUpdateForm(BaseModel):
    """Documented fields for multipart PATCH /api/profile (parsed from Form in route)."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
