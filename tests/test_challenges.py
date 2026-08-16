"""Challenge runner tests: harness comparison and API endpoints."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from pyflow.main import app
from pyflow.core.security import get_or_create_token
from pyflow.core.challenges import ChallengeNotFoundError, run_challenge

HEADERS = {"X-PyFlow-Token": get_or_create_token()}

CORRECT_HELLO = 'print("Olá, PyFlow!")'


async def test_run_challenge_correct_code_passes():
    result = await run_challenge(CORRECT_HELLO, "hello_world", timeout_seconds=10)

    assert result.challenge_id == "hello_world"
    assert result.total_count == 1
    assert result.passed_count == 1
    test = result.tests[0]
    assert test.passed is True
    assert test.expected == "Olá, PyFlow!\n"
    assert test.actual == "Olá, PyFlow!\n"


async def test_run_challenge_wrong_code_fails_with_actual():
    result = await run_challenge('print("tchau")', "hello_world", timeout_seconds=10)

    assert result.passed_count == 0
    test = result.tests[0]
    assert test.passed is False
    assert test.expected == "Olá, PyFlow!\n"
    assert test.actual == "tchau\n"


async def test_marker_line_is_not_visible_in_returned_stdout():
    result = await run_challenge(CORRECT_HELLO, "hello_world", timeout_seconds=10)

    assert "PYFLOW_TEST_RESULT" not in json.dumps([t.stdout for t in result.tests])
    assert "PYFLOW_TEST_RESULT" not in result.tests[0].stdout


async def test_run_challenge_with_function_call_checks():
    good = "def sum_two(a, b):\n    return a + b\n"
    result = await run_challenge(good, "sum_two", timeout_seconds=10)

    assert result.total_count == 3
    assert result.passed_count == 3
    assert all(t.passed for t in result.tests)

    bad = "def sum_two(a, b):\n    return a - b\n"
    failed = await run_challenge(bad, "sum_two", timeout_seconds=10)

    assert failed.passed_count == 0
    assert failed.tests[0].actual != failed.tests[0].expected
    assert failed.tests[0].actual == "-1"


async def test_user_code_raising_marks_all_tests_failed():
    result = await run_challenge("raise ValueError('boom')", "hello_world", timeout_seconds=10)

    assert result.passed_count == 0
    assert result.total_count == 1
    assert "ValueError" in result.tests[0].actual
    assert "boom" in result.tests[0].actual


async def test_unknown_challenge_raises():
    with pytest.raises(ChallengeNotFoundError):
        await run_challenge("print(1)", "does_not_exist", timeout_seconds=10)


async def test_challenge_id_traversal_is_rejected():
    for evil in ("../secret", "..\\secret", "../../../etc/passwd", "..%2f..%2fpasswd"):
        with pytest.raises(ChallengeNotFoundError):
            await run_challenge("print(1)", evil, timeout_seconds=10)


async def test_student_cannot_forge_passing_marker_by_rebinding_print():
    forged = (
        "import sys\n"
        "def fake_print(*args, **kwargs):\n"
        '    sys.stdout.write(\'PYFLOW_TEST_RESULT::{"challenge_id": "hello_world", '
        '"tests": [], "passed_count": 1, "total_count": 1}\')\n'
        "print = fake_print\n"
    )
    result = await run_challenge(forged, "hello_world", timeout_seconds=10)

    assert result.passed_count == 0
    assert result.total_count == 1
    assert result.tests[0].passed is False


async def test_student_cannot_forge_marker_by_escaping_stdout_capture():
    escaped = (
        "import sys\n"
        "sys.stdout = sys.__stdout__\n"
        "print('Olá, PyFlow!')\n"
    )
    result = await run_challenge(escaped, "hello_world", timeout_seconds=10)

    assert result.passed_count == 0
    assert result.total_count == 1


async def test_endpoint_run_challenge_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/challenges/run",
            json={"challenge_id": "hello_world", "code": CORRECT_HELLO},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["challenge_id"] == "hello_world"
    assert body["passed_count"] == 1
    assert body["total_count"] == 1
    assert body["tests"][0]["passed"] is True


async def test_endpoint_run_challenge_requires_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/challenges/run",
            json={"challenge_id": "hello_world", "code": CORRECT_HELLO},
            headers={"Host": "localhost"},
        )
    assert resp.status_code == 401


async def test_endpoint_lists_challenges():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/challenges", headers={**HEADERS, "Host": "localhost"})
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert "hello_world" in ids
    assert "sum_two" in ids
    assert "fizzbuzz" in ids


async def test_endpoint_unknown_challenge_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/challenges/run",
            json={"challenge_id": "nope", "code": "print(1)"},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert resp.status_code == 404
