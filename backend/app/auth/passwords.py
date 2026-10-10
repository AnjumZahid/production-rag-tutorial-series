# uv add "pwdlib[argon2]" email-validator

from pwdlib import PasswordHash

from backend.app.core.exceptions import AuthenticationError


class PasswordService:
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def validate_password_strength(
        self,
        password: str,
    ) -> None:
        if len(password) < 12:
            raise AuthenticationError(
                message="Password must be at least 12 characters long."
            )

        if len(password) > 128:
            raise AuthenticationError(
                message="Password must not exceed 128 characters."
            )

    def hash_password(
        self,
        password: str,
    ) -> str:
        self.validate_password_strength(password)

        return self._password_hash.hash(password)

    def verify_password(
        self,
        *,
        plain_password: str,
        password_hash: str,
    ) -> bool:
        return self._password_hash.verify(
            plain_password,
            password_hash,
        )


password_service = PasswordService()