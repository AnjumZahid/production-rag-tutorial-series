import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.jwt import (
    JWTService,
    TokenPair,
    jwt_service,
)
from backend.app.auth.passwords import (
    PasswordService,
    password_service,
)
from backend.app.core.exceptions import (
    AuthenticationError,
    ConflictError,
)
from backend.app.database.models.auth import (
    OrganizationRecord,
    UserRecord,
)
from backend.app.database.models.membership import (
    MembershipRecord,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def to_naive_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value

    return value.astimezone(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def normalize_email(
    email: str,
) -> str:
    return email.strip().lower()


def make_slug(
    value: str,
) -> str:
    normalized = (
        value.strip().lower()
    )

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    )

    normalized = normalized.strip("-")

    if not normalized:
        normalized = "organization"

    return (
        f"{normalized}-"
        f"{uuid4().hex[:8]}"
    )


def hash_refresh_token(
    refresh_token: str,
) -> str:
    return hashlib.sha256(
        refresh_token.encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: str
    organization_id: str
    organization_name: str
    email: str
    full_name: str | None
    role: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: AuthUser
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class AuthenticationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: AuthRepository | None = None,
        membership_repository: MembershipRepository | None = None,
        passwords: PasswordService = password_service,
        tokens: JWTService = jwt_service,
    ) -> None:
        self.session = session

        self.repository = (
            repository
            or AuthRepository(session)
        )

        self.memberships = (
            membership_repository
            or MembershipRepository(session)
        )

        self.passwords = passwords
        self.tokens = tokens

    async def register(
        self,
        *,
        organization_name: str,
        email: str,
        password: str,
        full_name: str | None,
    ) -> AuthResult:
        normalized_email = (
            normalize_email(email)
        )

        existing_user = (
            await self.repository
            .get_user_by_email(
                normalized_email
            )
        )

        if existing_user is not None:
            raise ConflictError(
                message=(
                    "A user with this email "
                    "already exists."
                )
            )

        organization = (
            await self.repository
            .create_organization(
                name=organization_name.strip(),
                slug=make_slug(
                    organization_name
                ),
            )
        )

        password_hash = (
            self.passwords
            .hash_password(
                password
            )
        )

        user = (
            await self.repository
            .create_user(
                organization_id=organization.id,
                email=normalized_email,
                password_hash=password_hash,
                full_name=(
                    full_name.strip()
                    if full_name
                    else None
                ),
                role="owner",
                is_active=True,
            )
        )

        await self.session.flush()

        membership = (
            await self.repository
            .create_owner_membership(
                organization_id=organization.id,
                user_id=user.id,
            )
        )

        await self.session.flush()

        token_pair = (
            await self
            ._issue_and_store_token_pair(
                user_id=user.id,
                organization_id=organization.id,
            )
        )

        await self.session.commit()

        return self._build_auth_result(
            user=user,
            organization=organization,
            membership=membership,
            token_pair=token_pair,
        )

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> AuthResult:
        normalized_email = (
            normalize_email(email)
        )

        user = (
            await self.repository
            .get_user_by_email(
                normalized_email
            )
        )

        if user is None:
            raise AuthenticationError(
                message=(
                    "Invalid email or password."
                )
            )

        if not user.is_active:
            raise AuthenticationError(
                message=(
                    "This user account is inactive."
                )
            )

        password_valid = (
            self.passwords
            .verify_password(
                plain_password=password,
                password_hash=(
                    user.password_hash
                ),
            )
        )

        if not password_valid:
            raise AuthenticationError(
                message=(
                    "Invalid email or password."
                )
            )

        membership = (
            await self.memberships
            .get_active_membership(
                organization_id=user.organization_id,
                user_id=user.id,
            )
        )

        if membership is None:
            raise AuthenticationError(
                message=(
                    "Your organization membership "
                    "is inactive or unavailable."
                )
            )

        user_and_org = (
            await self.repository
            .get_user_and_organization(
                user_id=user.id,
                organization_id=(
                    user.organization_id
                ),
            )
        )

        if user_and_org is None:
            raise AuthenticationError(
                message=(
                    "User organization membership "
                    "is invalid."
                )
            )

        user_record, organization = (
            user_and_org
        )

        token_pair = (
            await self
            ._issue_and_store_token_pair(
                user_id=user_record.id,
                organization_id=(
                    user_record.organization_id
                ),
            )
        )

        await self.session.commit()

        return self._build_auth_result(
            user=user_record,
            organization=organization,
            membership=membership,
            token_pair=token_pair,
        )

    async def refresh(
        self,
        *,
        refresh_token: str,
    ) -> AuthResult:
        claims = (
            self.tokens
            .decode_refresh_token(
                refresh_token
            )
        )

        token_hash = (
            hash_refresh_token(
                refresh_token
            )
        )

        refresh_record = (
            await self.repository
            .get_refresh_token_by_hash_for_update(
                token_hash
            )
        )

        if refresh_record is None:
            raise AuthenticationError(
                message=(
                    "The refresh token "
                    "is invalid."
                )
            )

        if refresh_record.revoked_at is not None:
            raise AuthenticationError(
                message=(
                    "The refresh token "
                    "has been revoked."
                )
            )

        expires_at = (
            to_naive_utc(
                refresh_record.expires_at
            )
        )

        if expires_at <= utc_now():
            raise AuthenticationError(
                message=(
                    "The refresh token "
                    "has expired."
                )
            )

        if (
            refresh_record.token_id
            != claims.token_id
        ):
            raise AuthenticationError(
                message=(
                    "The refresh token "
                    "is invalid."
                )
            )

        if (
            refresh_record.user_id
            != claims.user_id
        ):
            raise AuthenticationError(
                message=(
                    "The refresh token user "
                    "does not match."
                )
            )

        if (
            refresh_record.organization_id
            != claims.organization_id
        ):
            raise AuthenticationError(
                message=(
                    "The refresh token "
                    "organization does not match."
                )
            )

        user_and_org = (
            await self.repository
            .get_user_and_organization(
                user_id=claims.user_id,
                organization_id=(
                    claims.organization_id
                ),
            )
        )

        if user_and_org is None:
            raise AuthenticationError(
                message=(
                    "User organization membership "
                    "is invalid."
                )
            )

        user, organization = (
            user_and_org
        )

        if not user.is_active:
            raise AuthenticationError(
                message=(
                    "This user account "
                    "is inactive."
                )
            )

        membership = (
            await self.memberships
            .get_active_membership(
                organization_id=(
                    claims.organization_id
                ),
                user_id=claims.user_id,
            )
        )

        if membership is None:
            raise AuthenticationError(
                message=(
                    "Your organization membership "
                    "is inactive or unavailable."
                )
            )

        await self.repository.revoke_refresh_token(
            refresh_record
        )

        token_pair = (
            await self
            ._issue_and_store_token_pair(
                user_id=user.id,
                organization_id=(
                    user.organization_id
                ),
            )
        )

        await self.session.commit()

        return self._build_auth_result(
            user=user,
            organization=organization,
            membership=membership,
            token_pair=token_pair,
        )

    async def logout(
        self,
        *,
        refresh_token: str,
        user_id: str,
        organization_id: str,
    ) -> None:
        claims = (
            self.tokens
            .decode_refresh_token(
                refresh_token
            )
        )

        if claims.user_id != user_id:
            raise AuthenticationError(
                message=(
                    "The refresh token user "
                    "does not match."
                )
            )

        if (
            claims.organization_id
            != organization_id
        ):
            raise AuthenticationError(
                message=(
                    "The refresh token "
                    "organization does not match."
                )
            )

        token_hash = (
            hash_refresh_token(
                refresh_token
            )
        )

        refresh_record = (
            await self.repository
            .get_refresh_token_by_hash_for_update(
                token_hash
            )
        )

        if (
            refresh_record is not None
            and refresh_record.revoked_at
            is None
        ):
            await self.repository.revoke_refresh_token(
                refresh_record
            )

        await self.session.commit()

    async def get_current_user(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> AuthUser:
        user_and_org = (
            await self.repository
            .get_user_and_organization(
                user_id=user_id,
                organization_id=organization_id,
            )
        )

        if user_and_org is None:
            raise AuthenticationError(
                message=(
                    "Current user could "
                    "not be found."
                )
            )

        user, organization = (
            user_and_org
        )

        if not user.is_active:
            raise AuthenticationError(
                message=(
                    "This user account "
                    "is inactive."
                )
            )

        membership = (
            await self.memberships
            .get_active_membership(
                organization_id=organization_id,
                user_id=user_id,
            )
        )

        if membership is None:
            raise AuthenticationError(
                message=(
                    "Your organization membership "
                    "is inactive or unavailable."
                )
            )

        return self._build_user_response(
            user=user,
            organization=organization,
            membership=membership,
        )

    async def _issue_and_store_token_pair(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> TokenPair:
        token_pair = (
            self.tokens
            .create_token_pair(
                user_id=user_id,
                organization_id=organization_id,
            )
        )

        refresh_claims = (
            self.tokens
            .decode_refresh_token(
                token_pair.refresh_token
            )
        )

        await self.repository.create_refresh_token(
            user_id=user_id,
            organization_id=organization_id,
            token_id=(
                refresh_claims.token_id
            ),
            token_hash=(
                hash_refresh_token(
                    token_pair.refresh_token
                )
            ),
            expires_at=(
                to_naive_utc(
                    refresh_claims.expires_at
                )
            ),
        )

        return token_pair

    def _build_auth_result(
        self,
        *,
        user: UserRecord,
        organization: OrganizationRecord,
        membership: MembershipRecord,
        token_pair: TokenPair,
    ) -> AuthResult:
        return AuthResult(
            user=self._build_user_response(
                user=user,
                organization=organization,
                membership=membership,
            ),
            access_token=(
                token_pair.access_token
            ),
            refresh_token=(
                token_pair.refresh_token
            ),
            token_type=(
                token_pair.token_type
            ),
            expires_in=(
                token_pair.expires_in
            ),
        )

    def _build_user_response(
        self,
        *,
        user: UserRecord,
        organization: OrganizationRecord,
        membership: MembershipRecord,
    ) -> AuthUser:
        return AuthUser(
            id=user.id,
            organization_id=(
                user.organization_id
            ),
            organization_name=(
                organization.name
            ),
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            is_active=(
                user.is_active
                and membership.is_active
            ),
        )