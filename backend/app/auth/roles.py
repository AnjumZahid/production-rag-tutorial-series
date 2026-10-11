from enum import StrEnum


class OrganizationRole(StrEnum):
    """Roles available inside an organization."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Roles that can read/query organization documents.
DOCUMENT_READ_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
        OrganizationRole.VIEWER,
    }
)


# Roles that can create/upload/write documents.
DOCUMENT_WRITE_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
    }
)


# Roles that can manage organization members.
MEMBER_MANAGEMENT_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }
)


def can_read_documents(role: str) -> bool:
    """Return True when the role can read organization documents."""

    try:
        normalized_role = OrganizationRole(role)
    except ValueError:
        return False

    return normalized_role in DOCUMENT_READ_ROLES


def can_write_documents(role: str) -> bool:
    """Return True when the role can create or modify documents."""

    try:
        normalized_role = OrganizationRole(role)
    except ValueError:
        return False

    return normalized_role in DOCUMENT_WRITE_ROLES


def can_manage_members(role: str) -> bool:
    """Return True when the role can manage organization members."""

    try:
        normalized_role = OrganizationRole(role)
    except ValueError:
        return False

    return normalized_role in MEMBER_MANAGEMENT_ROLES