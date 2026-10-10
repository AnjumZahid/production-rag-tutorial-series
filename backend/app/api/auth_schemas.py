from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    organization_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )
    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        min_length=1,
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        min_length=1,
    )


class UserResponse(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class MessageResponse(BaseModel):
    status: str
    message: str