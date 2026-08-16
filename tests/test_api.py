"""API integration tests via ASGI transport (no real server needed)."""

import pytest
from httpx import ASGITransport, AsyncClient

from pyflow.main import app
from pyflow.core.security import get_or_create_token

HEADERS = {"X-PyFlow-Token": get_or_create_token()}


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health", headers={"Host": "localhost"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_run_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "print(2+2)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "4" in body["stdout"]
    assert body["request_id"].startswith("req_")


@pytest.mark.asyncio
async def test_run_error_with_diagnostics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "x = 1/0", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    body = resp.json()
    assert body["status"] == "error"
    assert body["diagnostics"]["error_type"] == "ZeroDivisionError"
    assert body["diagnostics"]["line"] == 1


@pytest.mark.asyncio
async def test_chat_requires_ai_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"user_message": "oi"},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert resp.status_code == 200
    assert "Nenhuma configuração" in resp.json()["reply"]


@pytest.mark.asyncio
async def test_code_too_large():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "#" * 200_000, "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    body = resp.json()
    assert body["status"] == "error"
    assert body["diagnostics"]["error_type"] == "CodeTooLarge"
