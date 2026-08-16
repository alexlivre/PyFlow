"""Shared FastAPI dependencies for PyFlow."""

from fastapi import Header, HTTPException

from pyflow.core.security import validate_token


async def require_token(x_pyflow_token: str | None = Header(default=None)) -> None:
    """Reject requests that do not carry a valid local API token."""
    if not validate_token(x_pyflow_token):
        raise HTTPException(status_code=401, detail="Invalid or missing X-PyFlow-Token")
