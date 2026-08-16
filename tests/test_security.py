import json

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
    assert validate_token(get_or_create_token()) is True
    assert validate_token("wrong-token") is False
    assert validate_token("") is False
    assert validate_token(None) is False


def test_connection_file_contains_token(tmp_path, monkeypatch):
    from pyflow.core import connection

    monkeypatch.setattr(connection, "CONNECTION_FILE", tmp_path / "connection.json")
    monkeypatch.setattr(connection, "CONNECTION_DIR", tmp_path)
    connection.write_connection_file("127.0.0.1", 8000, 123)
    data = json.loads((tmp_path / "connection.json").read_text(encoding="utf-8"))
    assert data["token"] == get_or_create_token()


def test_run_with_malicious_origin_is_rejected():
    resp = client.post(
        "/run",
        json={"code": "print(1)"},
        headers={
            "X-PyFlow-Token": get_or_create_token(),
            "Origin": "https://evil.example.com",
        },
    )
    assert resp.status_code == 403


def test_run_with_local_origin_is_accepted():
    resp = client.post(
        "/run",
        json={"code": "print(1)"},
        headers={
            "X-PyFlow-Token": get_or_create_token(),
            "Origin": "http://localhost:3000",
        },
    )
    assert resp.status_code == 200


def test_origin_with_localhost_subdomain_is_rejected():
    resp = client.post(
        "/run",
        json={"code": "print(1)"},
        headers={
            "X-PyFlow-Token": get_or_create_token(),
            "Origin": "http://localhost.evil.com",
        },
    )
    assert resp.status_code == 403


def test_origin_with_ip_subdomain_is_rejected():
    resp = client.post(
        "/run",
        json={"code": "print(1)"},
        headers={
            "X-PyFlow-Token": get_or_create_token(),
            "Origin": "http://127.0.0.1.evil.com",
        },
    )
    assert resp.status_code == 403


def test_is_local_origin_boundaries():
    from pyflow.api.deps import is_local_origin

    assert is_local_origin("http://localhost:3000") is True
    assert is_local_origin("https://localhost:3000") is True
    assert is_local_origin("http://127.0.0.1:3000") is True
    assert is_local_origin("http://localhost.evil.com") is False
    assert is_local_origin("http://127.0.0.1.evil.com") is False
    assert is_local_origin("https://evil.example.com") is False
    assert is_local_origin("null") is False
    assert is_local_origin(None) is True
