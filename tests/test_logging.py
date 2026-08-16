"""Tests for structured JSON logging with request correlation (task 5.3)."""

import json
import sys

from loguru import logger

from pyflow.core.config import settings
from pyflow.core.logging_config import configure_logging


def test_default_config_keeps_default_handlers_intact(monkeypatch):
    monkeypatch.setattr(settings, "PYFLOW_LOG_JSON", False)
    before = len(logger._core.handlers)
    configure_logging(settings)
    assert len(logger._core.handlers) == before


def test_json_sink_writes_request_id(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "PYFLOW_LOG_JSON", True)
    try:
        configure_logging(settings, log_dir=tmp_path)
        logger.bind(request_id="req_test").info("run:done", status="success")
        logger.complete()

        log_files = sorted(tmp_path.glob("pyflow-*.json"))
        assert log_files
        lines = log_files[-1].read_text(encoding="utf-8").splitlines()
        assert lines
        record = json.loads(lines[0])
        assert record["record"]["message"] == "run:done"
        assert record["record"]["extra"]["request_id"] == "req_test"
    finally:
        logger.remove()
        logger.add(sys.stderr)
