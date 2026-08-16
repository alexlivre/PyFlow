"""
Backends de execução plugáveis.

`get_backend()` devolve o backend ativo conforme
`settings.PYFLOW_EXECUTION_BACKEND` ("subprocess" por padrão, ou
"docker" para sandbox isolado).
"""

from typing import Dict

from pyflow.core.backends.base import ExecutionBackend, RawExecution
from pyflow.core.backends.subprocess_backend import SubprocessBackend
from pyflow.core.backends.docker_backend import DockerBackend
from pyflow.core.config import settings

__all__ = [
    "ExecutionBackend",
    "RawExecution",
    "SubprocessBackend",
    "DockerBackend",
    "get_backend",
]

_backend_cache: Dict[str, ExecutionBackend] = {}


def get_backend() -> ExecutionBackend:
    """Return the configured execution backend (cached per name)."""
    name = settings.PYFLOW_EXECUTION_BACKEND
    backend = _backend_cache.get(name)
    if backend is None:
        if name == "docker":
            backend = DockerBackend()
        elif name == "subprocess":
            backend = SubprocessBackend()
        else:
            raise ValueError(f"Unknown execution backend: {name!r}")
        _backend_cache[name] = backend
    return backend
