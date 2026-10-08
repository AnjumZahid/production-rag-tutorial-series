import argparse

from backend.app.auth import create_access_token


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a development JWT access token."
    )

    parser.add_argument(
        "--user-id",
        required=True,
        help="User ID to place in the token subject claim.",
    )

    parser.add_argument(
        "--organization-id",
        required=True,
        help="Organization ID to place in the token.",
    )

    parser.add_argument(
        "--expires-minutes",
        type=int,
        default=None,
        help="Token lifetime in minutes.",
    )

    args = parser.parse_args()

    token = create_access_token(
        user_id=args.user_id,
        organization_id=args.organization_id,
        expires_minutes=args.expires_minutes,
    )

    print(token)


if __name__ == "__main__":
    main()

# uv run python -m scripts.create_dev_token `
#     --user-id test-user `
#     --organization-id test-org `
#     --expires-minutes 60