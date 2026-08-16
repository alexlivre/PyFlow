"""
Challenge runner with automatic verification (mini-Judge0).

Builds a single script from the student code plus a hidden test harness,
executes it through the isolated engine, and parses the results reported
on the marker line printed to stdout.

Harness contract:
    - The harness prologue redirects stdout into an io.StringIO, then the
      student code runs at module level (concatenated as-is, never
      re-indented), then the harness epilogue restores stdout and compares
      the captured output against each test's expected string.
    - Tests with an optional 'harness' expression call a function from the
      student code and compare str(return value) against 'expected'.
    - The harness prints the marker line "PYFLOW_TEST_RESULT::<json>" to the
      real stdout as the LAST line; the JSON payload carries the results.
    - If the student code raises (or the marker is missing or malformed), every
      test is marked failed with the execution error as 'actual'.
"""

import io
import json
import textwrap
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from pyflow.core.config import settings
from pyflow.core.engine import execute_code
from pyflow.core.models import ChallengeResult, ChallengeTestResult, RunResponse
from pyflow.utils.ids import generate_request_id

MARKER_PREFIX = "PYFLOW_TEST_RESULT::"
INVALID_MARKER_MESSAGE = "Marcador de resultado inválido."
CHALLENGES_DIR = Path(__file__).resolve().parent.parent / "data" / "challenges"

_HARNESS_PROLOGUE = textwrap.dedent(
    """\
    # ==== HARNESS ====
    import io
    import json
    import sys

    __pyflow_captured = io.StringIO()
    __pyflow_orig_stdout = sys.stdout
    sys.stdout = __pyflow_captured

    # ==== USER CODE ====
    """
)

_HARNESS_EPILOGUE = textwrap.dedent(
    """\
    # ==== HARNESS ====
    __pyflow_captured_str = __pyflow_captured.getvalue()
    sys.stdout = __pyflow_orig_stdout
    __pyflow_tests = []


    def __pyflow_add_test(name, passed, expected, actual, stdout=""):
        __pyflow_tests.append({
            "name": name,
            "passed": bool(passed),
            "expected": expected,
            "actual": actual,
            "stdout": stdout,
        })
    """
)

_MARKER_PRINT = textwrap.dedent(
    """\
    print("PYFLOW_TEST_RESULT::" + json.dumps({{
        "challenge_id": {challenge_id},
        "tests": __pyflow_tests,
        "passed_count": sum(1 for _t in __pyflow_tests if _t["passed"]),
        "total_count": len(__pyflow_tests),
    }}))
    """
)


class ChallengeNotFoundError(KeyError):
    """Raised when no challenge exists for the requested id."""


def load_challenge(challenge_id: str) -> dict:
    """Load a challenge definition by id from the challenges directory."""
    path = CHALLENGES_DIR / f"{challenge_id}.json"
    if not path.is_file():
        raise ChallengeNotFoundError(challenge_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_challenge_infos() -> List[dict]:
    """Return the public metadata of every available challenge."""
    infos = []
    for path in sorted(CHALLENGES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        infos.append(
            {
                "id": data["id"],
                "title": data["title"],
                "description": data["description"],
                "solution_hint": data["solution_hint"],
            }
        )
    return infos


def _build_test_code(test: dict) -> str:
    """Generate the harness statements that verify a single test."""
    name = json.dumps(test["name"], ensure_ascii=False)
    expected = json.dumps(test["expected"], ensure_ascii=False)
    if "harness" in test:
        harness_expr = textwrap.dedent(test["harness"])
        return (
            f"try:\n"
            f"    __pyflow_actual = {harness_expr}\n"
            f"    __pyflow_add_test({name}, str(__pyflow_actual) == {expected}, {expected}, str(__pyflow_actual))\n"
            f"except Exception as __pyflow_err:\n"
            f"    __pyflow_add_test({name}, False, {expected}, type(__pyflow_err).__name__ + ': ' + str(__pyflow_err))\n"
        )
    return (
        f"__pyflow_add_test({name}, __pyflow_captured_str == {expected}, {expected}, __pyflow_captured_str, __pyflow_captured_str)\n"
    )


def _build_script(user_code: str, challenge: dict) -> str:
    """Assemble the single script the engine will execute."""
    parts = [_HARNESS_PROLOGUE, user_code, _HARNESS_EPILOGUE]
    for test in challenge["tests"]:
        parts.append(_build_test_code(test))
    parts.append(_MARKER_PRINT.format(challenge_id=json.dumps(challenge["id"])))
    return "\n\n".join(parts)


def _extract_marker(stdout: str) -> Optional[dict]:
    """Parse the last valid PYFLOW_TEST_RESULT line from the engine stdout."""
    lines = stdout.splitlines()
    for line in reversed(lines):
        if line.startswith(MARKER_PREFIX):
            try:
                return json.loads(line[len(MARKER_PREFIX):])
            except json.JSONDecodeError:
                continue
    return None


def _failure_reason(result: RunResponse) -> str:
    """Best-effort single-line summary of why the student script failed."""
    stderr_lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    if stderr_lines:
        return stderr_lines[-1]
    if result.status == "timeout":
        return "Tempo limite de execução excedido."
    if result.status == "blocked":
        return result.stderr or "Execução bloqueada."
    return "Erro desconhecido durante a execução."


def _build_failed_tests(challenge: dict, reason: str) -> List[ChallengeTestResult]:
    """Build one failed ChallengeTestResult per challenge test, all marked failed."""
    return [
        ChallengeTestResult(
            name=test["name"], passed=False, stdout="", expected=test["expected"], actual=reason
        )
        for test in challenge["tests"]
    ]


async def run_challenge(code: str, challenge_id: str, timeout_seconds: int) -> ChallengeResult:
    """Execute the student code against a challenge's hidden tests."""
    challenge = load_challenge(challenge_id)
    script = _build_script(code, challenge)
    result = await execute_code(
        request_id=generate_request_id(),
        code=script,
        stdin=None,
        timeout_seconds=timeout_seconds,
        max_output_chars=settings.PYFLOW_MAX_OUTPUT_CHARS_DEFAULT,
    )

    payload = _extract_marker(result.stdout)
    if payload is None:
        return ChallengeResult(
            challenge_id=challenge_id,
            tests=_build_failed_tests(challenge, _failure_reason(result)),
            passed_count=0,
            total_count=len(challenge["tests"]),
        )

    if not isinstance(payload, dict):
        return ChallengeResult(
            challenge_id=challenge_id,
            tests=_build_failed_tests(challenge, INVALID_MARKER_MESSAGE),
            passed_count=0,
            total_count=len(challenge["tests"]),
        )

    tests_raw = payload.get("tests")
    if not isinstance(tests_raw, list):
        return ChallengeResult(
            challenge_id=challenge_id,
            tests=_build_failed_tests(challenge, INVALID_MARKER_MESSAGE),
            passed_count=0,
            total_count=len(challenge["tests"]),
        )

    tests = []
    for test in tests_raw:
        if not isinstance(test, dict):
            tests.append(
                ChallengeTestResult(
                    name="teste inválido", passed=False, stdout="", expected="", actual=INVALID_MARKER_MESSAGE
                )
            )
            continue
        try:
            tests.append(ChallengeTestResult(**test))
        except ValidationError as exc:
            tests.append(
                ChallengeTestResult(
                    name=str(test.get("name") or "teste inválido"),
                    passed=False,
                    stdout=str(test.get("stdout") or ""),
                    expected=str(test.get("expected") or ""),
                    actual=str(exc),
                )
            )

    forged_id = payload.get("challenge_id", challenge_id)
    if not isinstance(forged_id, str):
        forged_id = challenge_id

    passed_count = payload.get("passed_count")
    total_count = payload.get("total_count")
    if not isinstance(passed_count, int) or isinstance(passed_count, bool):
        passed_count = sum(1 for t in tests if t.passed)
    if not isinstance(total_count, int) or isinstance(total_count, bool):
        total_count = len(tests)

    return ChallengeResult(
        challenge_id=forged_id,
        tests=tests,
        passed_count=passed_count,
        total_count=total_count,
    )
