"""Shared FastAPI dependencies for PyFlow."""

from urllib.parse import urlsplit

from fastapi import Header, HTTPException

from pyflow.core.security import validate_token

LOCAL_ORIGIN_HOSTNAMES = ("localhost", "127.0.0.1", "::1")


def is_local_origin(origin: str | None) -> bool:
    """True when the Origin header belongs to a local client."""
    if not origin:
        return True
    try:
        hostname = urlsplit(origin).hostname
    except ValueError:
        return False
    return hostname in LOCAL_ORIGIN_HOSTNAMES


async def require_token(x_pyflow_token: str | None = Header(default=None)) -> None:
    """Reject requests that do not carry a valid local API token."""
    if not validate_token(x_pyflow_token):
        raise HTTPException(status_code=401, detail="Invalid or missing X-PyFlow-Token")


async def require_local_origin(origin: str | None = Header(default=None)) -> None:
    """Block requests coming from non-local web origins (CSRF defense)."""
    if not is_local_origin(origin):
        raise HTTPException(status_code=403, detail="Cross-origin requests are not allowed")
