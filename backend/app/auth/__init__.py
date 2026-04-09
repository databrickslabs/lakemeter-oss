"""Authentication module."""
from app.auth.databricks_auth import (
    get_current_user,
    get_optional_user,
    get_or_create_user,
    get_user_from_headers,
    FORWARDED_EMAIL_HEADER,
    FORWARDED_USER_HEADER,
    FORWARDED_ACCESS_TOKEN_HEADER
)

__all__ = [
    "get_current_user",
    "get_optional_user",
    "get_or_create_user",
    "get_user_from_headers",
    "FORWARDED_EMAIL_HEADER",
    "FORWARDED_USER_HEADER",
    "FORWARDED_ACCESS_TOKEN_HEADER"
]
