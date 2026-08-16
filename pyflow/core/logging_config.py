"""Loguru reconfiguration for structured JSON logs.

PyFlow logs in human-readable format by default. When ``PYFLOW_LOG_JSON``
is enabled, loguru is reconfigured to write newline-delimited JSON records
(``serialize=True``) to a rotating file under ``logs/``, so each record
carries structured fields such as ``request_id`` bound via
``logger.bind(...)``.

In JSON mode the default stderr handler is removed; otherwise loguru is
left untouched so default behavior is preserved.
"""

from pathlib import Path

from loguru import logger

from pyflow.core.config import Settings

_DEFAULT_LOG_DIR = Path("logs")
_JSON_LOG_FILE = "pyflow-{time}.json"


def configure_logging(settings: Settings, log_dir: Path | None = None) -> None:
    """Reconfigure loguru for structured JSON logging when enabled.

    Args:
        settings: Application settings (PYFLOW_LOG_JSON flag).
        log_dir: Directory for the JSON log files (defaults to ./logs).

    A logging misconfiguration must never crash the app, so any failure
    here is swallowed.
    """
    if not settings.PYFLOW_LOG_JSON:
        return
    try:
        logger.remove()
        logger.add(
            (log_dir or _DEFAULT_LOG_DIR) / _JSON_LOG_FILE,
            rotation="10 MB",
            serialize=True,
            enqueue=True,
        )
    except Exception:
        pass
