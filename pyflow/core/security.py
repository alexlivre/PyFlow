"""Local API token management for PyFlow."""

import hmac
import secrets

from loguru import logger

from pyflow.core.config import settings, CONNECTION_DIR

TOKEN_FILE = CONNECTION_DIR / "token"


def get_or_create_token() -> str:
    """Return the API token, generating and persisting it on first call.

    The token comes from PYFLOW_API_TOKEN env var if set, otherwise it is
    generated once and stored in ~/.pyflow/token.
    """
    if settings.PYFLOW_API_TOKEN:
        return settings.PYFLOW_API_TOKEN
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(32)
    CONNECTION_DIR.mkdir(parents=True, exist_ok=True)
    try:
        TOKEN_FILE.write_text(token, encoding="utf-8")
    except OSError as e:
        logger.error(f"Failed to persist token: {e}")
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass
    return token


def validate_token(token: str | None) -> bool:
    """Compare the provided token against the local token in constant time."""
    if not token:
        return False
    return hmac.compare_digest(token, get_or_create_token())
