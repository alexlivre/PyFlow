"""Token delivery route for the local UI."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pyflow.api.deps import require_local_origin
from pyflow.core.security import get_or_create_token

router = APIRouter()


class TokenResponse(BaseModel):
    token: str


@router.get("/auth/token", response_model=TokenResponse, dependencies=[Depends(require_local_origin)])
async def get_token():
    """Return the local API token to same-origin local clients."""
    return TokenResponse(token=get_or_create_token())
