from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)

from backend.app.auth.roles import OrganizationRole


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime


class OrganizationMemberResponse(BaseModel):
    membership_id: str
    user_id: str
    email: EmailStr
    full_name: str | None
    role: OrganizationRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationMemberListResponse(BaseModel):
    members: list[OrganizationMemberResponse]


class CreateOrganizationMemberRequest(BaseModel):
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

    role: OrganizationRole = OrganizationRole.MEMBER


class UpdateOrganizationMemberRoleRequest(BaseModel):
    role: OrganizationRole