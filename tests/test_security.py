import pytest
from fastapi.testclient import TestClient
from pyflow.main import app
from pyflow.core.security import get_or_create_token

client = TestClient(app)


def test_run_without_token_returns_401():
    resp = client.post("/run", json={"code": "print(1)"})
    assert resp.status_code == 401


def test_run_with_token_returns_200():
    token = get_or_create_token()
    resp = client.post(
        "/run",
        json={"code": "print(1)", "ai_explain_on_error": False},
        headers={"X-PyFlow-Token": token},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_health_is_public():
    assert client.get("/health").status_code == 200


def test_token_validation_is_timing_safe():
    from pyflow.core.security import validate_token
    assert validate_token("wrong-token") is False
    assert validate_token("") is False
    assert validate_token(None) is False
