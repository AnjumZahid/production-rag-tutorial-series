from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_database_session_dependency,
    get_organization_access,
    require_organization_roles,
)
from backend.app.api.organization_schemas import (
    CreateOrganizationMemberRequest,
    OrganizationMemberListResponse,
    OrganizationMemberResponse,
    OrganizationResponse,
    UpdateOrganizationMemberRoleRequest,
)
from backend.app.auth.roles import OrganizationRole
from backend.app.core.config import settings
from backend.app.organizations.service import (
    OrganizationMember,
    OrganizationService,
    OrganizationSummary,
)


router = APIRouter(
    prefix=f"{settings.api_prefix}/organizations",
    tags=["Organizations"],
)


manage_members_access = require_organization_roles(
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
)


@router.get(
    "/current",
    response_model=OrganizationResponse,
)
async def get_current_organization(
    access: OrganizationAccess = Depends(
        get_organization_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> OrganizationResponse:
    service = OrganizationService(
        session=session
    )

    organization = (
        await service.get_current_organization(
            organization_id=access.organization_id
        )
    )

    return organization_response(
        organization
    )


@router.get(
    "/current/members",
    response_model=OrganizationMemberListResponse,
)
async def list_organization_members(
    access: OrganizationAccess = Depends(
        manage_members_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> OrganizationMemberListResponse:
    service = OrganizationService(
        session=session
    )

    members = await service.list_members(
        organization_id=access.organization_id
    )

    return OrganizationMemberListResponse(
        members=[
            member_response(member)
            for member in members
        ]
    )


@router.post(
    "/current/members",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization_member(
    request: CreateOrganizationMemberRequest,
    access: OrganizationAccess = Depends(
        manage_members_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> OrganizationMemberResponse:
    service = OrganizationService(
        session=session
    )

    member = await service.create_member(
        organization_id=access.organization_id,
        actor_user_id=access.user_id,
        actor_role=access.role,
        email=str(request.email),
        password=request.password,
        full_name=request.full_name,
        role=request.role.value,
    )

    return member_response(member)


@router.patch(
    "/current/members/{membership_id}/role",
    response_model=OrganizationMemberResponse,
)
async def change_organization_member_role(
    membership_id: str,
    request: UpdateOrganizationMemberRoleRequest,
    access: OrganizationAccess = Depends(
        manage_members_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> OrganizationMemberResponse:
    service = OrganizationService(
        session=session
    )

    member = await service.change_member_role(
        organization_id=access.organization_id,
        actor_user_id=access.user_id,
        actor_role=access.role,
        membership_id=membership_id,
        role=request.role.value,
    )

    return member_response(member)


@router.delete(
    "/current/members/{membership_id}",
    response_model=OrganizationMemberResponse,
)
async def deactivate_organization_member(
    membership_id: str,
    access: OrganizationAccess = Depends(
        manage_members_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> OrganizationMemberResponse:
    service = OrganizationService(
        session=session
    )

    member = await service.deactivate_member(
        organization_id=access.organization_id,
        actor_user_id=access.user_id,
        actor_role=access.role,
        membership_id=membership_id,
    )

    return member_response(member)


def organization_response(
    organization: OrganizationSummary,
) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        created_at=organization.created_at,
    )


def member_response(
    member: OrganizationMember,
) -> OrganizationMemberResponse:
    return OrganizationMemberResponse(
        membership_id=member.membership_id,
        user_id=member.user_id,
        email=member.email,
        full_name=member.full_name,
        role=OrganizationRole(member.role),
        is_active=member.is_active,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )