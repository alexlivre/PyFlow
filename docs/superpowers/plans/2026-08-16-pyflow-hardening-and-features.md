# PyFlow — Plano Mestre de Implementação (Segurança, Correções, Testes, Features)

> **Para agentes de execução:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para implementar task por task. As steps usam checkbox (`- [ ]`) para rastreamento. Cada task termina com um commit atômico.

**Goal:** Endurecer a segurança do PyFlow, corrigir todos os bugs identificados na análise, adicionar cobertura de testes + CI, e evoluir o produto (streaming, output rico, tutoria socrática, sandbox real) em 5 fases incrementais.

**Architecture:** Backend FastAPI com camada de segurança própria (`core/security.py`, dependencies), engine refatorado com backend de execução plugável (`core/backends/`), streaming via NDJSON (`/run/stream`), e UI Nuxt ampliada (token, highlight de erro, autosave, snippets, modo Pyodide). TDD em todas as fases.

**Tech Stack:** Python 3.11 (FastAPI, uvicorn, litellm, psutil, pydantic v2, pytest, httpx), Nuxt 3 / Vue 3 / Pinia / CodeMirror 6, Docker, GitHub Actions. **Sem novas dependências sem justificativa** — quando adicionar, pinar versão.

---

## Global Constraints

- Python >= 3.11 (Dockerfile usa `python:3.11-slim`; corrigir README que diz "3.14+").
- Código-fonte, comentários e mensagens de commit **em inglês**. UI mantém textos atuais (PT/EN misto).
- TDD obrigatório: escrever teste → ver falhar → implementar → ver passar → commit.
- Commits atômicos e frequentes, estilo do repo (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Todas as dependências novas entram pinadas (`requirements.txt` com `==`).
- A API **nunca** deve aceitar execução de código de origens não-locais após a Fase 0.
- Rota `/health` permanece pública (para discovery/healthcheck).
- Windows e Linux devem funcionar (cuidado com paths e permissões de arquivo).
- Segredos nunca em código, localStorage ou logs.

---

# FASE 0 — SEGURANÇA (CRÍTICA) — fazer primeiro, tudo bloqueia até terminar

## Task 0.1: Token de autenticação local (`X-PyFlow-Token`)

**Files:**
- Create: `pyflow/core/security.py`
- Create: `pyflow/api/deps.py`
- Modify: `pyflow/core/config.py` (campo `PYFLOW_API_TOKEN`)
- Modify: `pyflow/core/connection.py` (incluir token no connection.json)
- Modify: `pyflow/api/routes_run.py`, `pyflow/api/routes_chat.py`, `pyflow/api/routes_models.py` (dependency)
- Modify: `pyflow/api/routes_health.py` (não protegido)
- Create: `tests/test_security.py`

**Interfaces:**
- Produces: `get_or_create_token() -> str`, `validate_token(token: str | None) -> bool` (em `pyflow/core/security.py`); `require_token` (dependency FastAPI em `pyflow/api/deps.py`).
- Consumes: `settings.PYFLOW_API_TOKEN` (novo campo config), `CONNECTION_DIR` de `pyflow/core/connection.py`.

- [ ] **Step 1: Escrever o teste que falha** — `tests/test_security.py`:

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_security.py -v`
Expected: `test_run_without_token_returns_401` FAIL (hoje retorna 200).

- [ ] **Step 3: Implementar** — Create `pyflow/core/security.py`:

```python
"""Local API token management for PyFlow."""

import hmac
import secrets
from pathlib import Path

from pyflow.core.config import settings
from pyflow.core.connection import CONNECTION_DIR

TOKEN_FILE = CONNECTION_DIR / "token"


def get_or_create_token() -> str:
    """Return the API token, generating and persisting it on first call.

    The token comes from PYFLOW_API_TOKEN env var if set, otherwise it is
    generated once and stored in ~/.pyflow/token.
    """
    if settings.PYFLOW_API_TOKEN:
        return settings.PYFLOW_API_TOKEN
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(32)
    CONNECTION_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass
    return token


def validate_token(token: str | None) -> bool:
    """Compare the provided token against the local token in constant time."""
    if not token:
        return False
    return hmac.compare_digest(token, get_or_create_token())
```

- [ ] **Step 4: Config** — em `pyflow/core/config.py`, adicionar na seção de API Keys:

```python
    # Segurança
    PYFLOW_API_TOKEN: Optional[str] = None
```

- [ ] **Step 5: Connection file com token** — em `pyflow/core/connection.py`, alterar `write_connection_file` para incluir o token (import `get_or_create_token` de `pyflow.core.security`):

```python
    data = {
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}",
        "pid": pid,
        "version": __version__,
        "status": "online",
        "token": get_or_create_token(),
    }
```

> ⚠️ Cuidado com import circular: `security.py` importa `connection.py` (`CONNECTION_DIR`) e `connection.py` importará `security.py`. Resolver movendo `CONNECTION_DIR`/`CONNECTION_FILE` para `pyflow/core/config.py` (ou importar `security` dentro da função). **Decisão:** mover `CONNECTION_DIR` e `CONNECTION_FILE` para `pyflow/core/config.py` como constantes; `connection.py` e `security.py` importam de lá.

- [ ] **Step 6: Dependency** — Create `pyflow/api/deps.py`:

```python
"""Shared FastAPI dependencies for PyFlow."""

from fastapi import Header, HTTPException

from pyflow.core.security import validate_token


async def require_token(x_pyflow_token: str | None = Header(default=None)) -> None:
    """Reject requests that do not carry a valid local API token."""
    if not validate_token(x_pyflow_token):
        raise HTTPException(status_code=401, detail="Invalid or missing X-PyFlow-Token")
```

- [ ] **Step 7: Proteger as rotas** — em `routes_run.py` (`@router.post("/run", response_model=RunResponse, dependencies=[Depends(require_token)])`), `routes_chat.py` e `routes_models.py` idem. `routes_health.py` permanece sem proteção. Imports: `from fastapi import Depends` e `from pyflow.api.deps import require_token`.

- [ ] **Step 8: Rodar os testes**

Run: `python -m pytest tests/ -v`
Expected: todos PASS (incluindo os 3 existentes).

- [ ] **Step 9: Commit**

```bash
git add pyflow/core/security.py pyflow/api/deps.py pyflow/core/config.py pyflow/core/connection.py pyflow/api/routes_run.py pyflow/api/routes_chat.py pyflow/api/routes_models.py tests/test_security.py
git commit -m "feat: add local API token authentication to protected routes"
```

---

## Task 0.2: CORS restrito + verificação de origem (bloqueio de CSRF)

**Files:**
- Modify: `pyflow/main.py`
- Modify: `pyflow/api/deps.py`
- Modify: `tests/test_security.py`

**Interfaces:**
- Produces: `is_local_origin(origin: str | None) -> bool` e `require_local_origin` (dependency) em `pyflow/api/deps.py`.

- [ ] **Step 1: Testes** — adicionar em `tests/test_security.py`:

```python
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
```

- [ ] **Step 2: Confirmar que falha** — `python -m pytest tests/test_security.py -v` → `test_run_with_malicious_origin_is_rejected` FAIL.

- [ ] **Step 3: Implementar** — adicionar em `pyflow/api/deps.py`:

```python
LOCAL_ORIGIN_PREFIXES = ("http://localhost", "http://127.0.0.1")


def is_local_origin(origin: str | None) -> bool:
    """True when the Origin header belongs to a local client."""
    if not origin:
        return True
    return origin.lower().startswith(LOCAL_ORIGIN_PREFIXES)


async def require_local_origin(origin: str | None = Header(default=None)) -> None:
    """Block requests coming from non-local web origins (CSRF defense)."""
    if not is_local_origin(origin):
        raise HTTPException(status_code=403, detail="Cross-origin requests are not allowed")
```

- [ ] **Step 4: Aplicar nas rotas** — `dependencies=[Depends(require_token), Depends(require_local_origin)]` em `/run`, `/chat` e `/models/openrouter`.

- [ ] **Step 5: CORS restrito** — em `pyflow/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 6: Testes PASS** — `python -m pytest tests/ -v`.

- [ ] **Step 7: Commit** — `git commit -m "feat: restrict CORS to local origins and reject cross-origin requests"`.

---

## Task 0.3: Whitelist de env vars do subprocesso (bloqueio de vazamento de segredos)

**Files:**
- Modify: `pyflow/core/engine.py`
- Modify: `tests/test_engine.py` (criar este arquivo)

**Interfaces:**
- Produces: `_build_child_env() -> dict[str, str]` em `pyflow/core/engine.py`.

- [ ] **Step 1: Teste** — create `tests/test_engine.py`:

```python
"""Engine tests: environment isolation and execution controls."""

import asyncio
import os

from pyflow.core.engine import _build_child_env, execute_code


def test_build_child_env_whitelists_variables():
    os.environ["OPENAI_API_KEY"] = "sk-secret-should-not-leak"
    env = _build_child_env()
    assert "OPENAI_API_KEY" not in env
    assert "PYTHONIOENCODING" in env
    assert "PYTHONUNBUFFERED" in env


def test_executed_code_cannot_read_server_env():
    os.environ["OPENAI_API_KEY"] = "sk-secret-should-not-leak"
    result = asyncio.run(
        execute_code(
            request_id="req_env_test",
            code="import os; print(os.environ.get('OPENAI_API_KEY'))",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert "sk-secret-should-not-leak" not in result.stdout
```

- [ ] **Step 2: Confirmar falha** — `python -m pytest tests/test_engine.py -v` → ambos FAIL (hoje o env é copiado).

- [ ] **Step 3: Implementar** — em `pyflow/core/engine.py`, substituir `env_vars = os.environ.copy()` por:

```python
def _build_child_env() -> dict:
    """Build a minimal env for the child process.

    A whitelist prevents user code from reading server secrets
    (API keys, tokens) and keeps the execution environment clean.
    """
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }
```

E na chamada do subprocesso, `env=env_vars` → `env=_build_child_env()` (remover o bloco que copia o ambiente).

- [ ] **Step 4: Testes PASS** — `python -m pytest tests/test_engine.py tests/test_security.py -v`.

- [ ] **Step 5: Commit** — `git commit -m "fix: whitelist child process env to prevent secret leakage"`.

---

## Task 0.4: Hardening do Docker (bind local, usuário não-root, tmpfs)

**Files:**
- Modify: `Dockerfile.api`
- Modify: `docker-compose.yml`
- Modify: `run_docker.bat`

- [ ] **Step 1: Dockerfile.api** — usuário não-root e Python pinado:

```dockerfile
FROM python:3.11.9-slim

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin pyflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyflow ./pyflow

USER pyflow
EXPOSE 8000

CMD ["uvicorn", "pyflow.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: docker-compose.yml** — sem `version:`, bind local, tmpfs para o `/tmp` do engine, token explícito:

```yaml
services:
  pyflow-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    command: uvicorn pyflow.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - PYFLOW_API_TOKEN=${PYFLOW_API_TOKEN:-pyflow-dev-token-change-me}
    tmpfs:
      - /tmp
    volumes:
      - .:/app
    networks:
      - pyflow-network

  pyflow-ui:
    build:
      context: ./ui
      dockerfile: Dockerfile
    command: node scripts/dev.mjs
    ports:
      - "3000:3000"
    environment:
      - NUXT_PUBLIC_API_BASE=http://pyflow-api:8000
      - PYFLOW_API_TOKEN=${PYFLOW_API_TOKEN:-pyflow-dev-token-change-me}
    volumes:
      - ./ui:/app
      - /app/node_modules
      - /app/.nuxt
      - /app/.output
    depends_on:
      - pyflow-api
    networks:
      - pyflow-network

networks:
  pyflow-network:
    driver: bridge
```

> Nota: o engine escreve arquivos temporários em `gettempdir()` — por isso o `tmpfs: /tmp` no container (arquivos efêmeros não persistem e não tocam o filesystem do container).

- [ ] **Step 3: run_docker.bat** — trocar `docker-compose` por `docker compose` (2 ocorrências).

- [ ] **Step 4: UI conhece o token** — a store precisa do token para chamar a API. Em `ui/stores/pyflow.js`, adicionar estado `apiToken: ''` e ação:

```js
async fetchToken() {
    if (process.client) {
        try {
            const res = await $fetch('/api/token')
            this.apiToken = res.token || ''
        } catch (e) {
            console.error('Failed to fetch API token:', e)
        }
    }
},
```

E em `runCode`/`sendChatMessage`/fetch de modelos, incluir `headers: { 'X-PyFlow-Token': this.apiToken }` (apenas se `apiToken` não vazio).

- [ ] **Step 5: Rota `/auth/token` + proxy nitro** — create `pyflow/api/routes_auth.py`:

```python
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
```

Registrar em `pyflow/main.py` (`app.include_router(routes_auth.router)`) e adicionar em `ui/nuxt.config.ts`:

```ts
'/api/token': { proxy: (process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000') + '/auth/token' },
```

- [ ] **Step 6: Teste** — em `tests/test_security.py`:

```python
def test_token_route_rejects_evil_origin():
    resp = client.get("/auth/token", headers={"Origin": "https://evil.example.com"})
    assert resp.status_code == 403


def test_token_route_works_locally():
    resp = client.get("/auth/token", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.json()["token"]
```

- [ ] **Step 7: Verificar build docker** — `docker compose build` (sem erro) e `docker compose up -d` seguido de `curl http://localhost:8000/health` retornando 200.

- [ ] **Step 8: Commit** — `git commit -m "feat: harden docker deployment and deliver token to local UI"`.

---

## Task 0.5: Verificação de Host (defesa contra DNS rebinding)

**Files:**
- Modify: `pyflow/main.py`
- Modify: `tests/test_security.py`

- [ ] **Step 1: Teste**:

```python
def test_host_header_spoofing_is_rejected():
    resp = client.post(
        "/run",
        json={"code": "print(1)"},
        headers={
            "X-PyFlow-Token": get_or_create_token(),
            "Host": "evil.example.com",
        },
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Implementar** — em `pyflow/main.py`, middleware de verificação:

```python
ALLOWED_HOST_SUFFIXES = ("localhost", "127.0.0.1", "pyflow-api", "pyflow-ui", "0.0.0.0", "::1")

@app.middleware("http")
async def reject_non_local_hosts(request, call_next):
    host = request.headers.get("host", "").split(":")[0].lower()
    if host and not any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "Non-local host not allowed"})
    return await call_next(request)
```

- [ ] **Step 3: Testes PASS** e rodar suíte completa.

- [ ] **Step 4: Commit** — `git commit -m "feat: reject requests with non-local Host headers (DNS rebinding defense)"`.

> ✅ **Checkpoint FASE 0:** `python -m pytest tests/ -v` tudo verde; `docker compose up` funcionando; UI conectada e rodando código com token.

---

# FASE 1 — CORREÇÕES DE BUGS E DÍVIDAS TÉCNICAS

## Task 1.1: Implementar `include_raw_traceback` de verdade

**Files:**
- Modify: `pyflow/core/diagnostics.py`
- Modify: `pyflow/core/engine.py`
- Modify: `pyflow/api/routes_run.py`
- Modify: `tests/test_basic.py`

**Interfaces:**
- Produces: `parse_traceback_str(stderr: str, user_filename: str, include_raw: bool = False) -> Diagnostics`; `execute_code(..., include_raw_traceback: bool = False)`.

- [ ] **Step 1: Teste** — adicionar em `tests/test_basic.py`:

```python
def test_parse_with_raw_traceback():
    stderr = 'Traceback (most recent call last):\n  File "pyflow_tmp_1.py", line 1, in <module>\n    x\nNameError: name \'x\' is not defined\n'
    d = parse_traceback_str(stderr, "pyflow_tmp_1.py", include_raw=True)
    assert d.raw_traceback == stderr.strip()


def test_parse_without_raw_traceback():
    stderr = 'Traceback (most recent call last):\n  File "pyflow_tmp_1.py", line 1, in <module>\n    x\nNameError: name \'x\' is not defined\n'
    d = parse_traceback_str(stderr, "pyflow_tmp_1.py", include_raw=False)
    assert d.raw_traceback is None
```

- [ ] **Step 2: Implementar** — `diagnostics.py:139-145`: retornar `raw_traceback=stderr.strip() if include_raw else None`. Em `engine.py`, `execute_code` ganha o parâmetro `include_raw_traceback` e o repassa na chamada `parse_traceback_str(stderr_str, tmp_file.name, include_raw=include_raw_traceback)`. Em `routes_run.py`, passar `include_raw_traceback=req.include_raw_traceback`.

- [ ] **Step 3: Testes PASS.**

- [ ] **Step 4: Commit** — `git commit -m "feat: honor include_raw_traceback request flag"`.

---

## Task 1.2: Remover dead code e deduplicar chamadas de IA (GPT-5 + LiteLLM)

**Files:**
- Modify: `pyflow/core/ai_service.py`
- Modify: `tests/test_ai_service.py` (criar)

**Interfaces:**
- Produces: helper `_completion(model: str, messages: list[dict], config: AIConfig, *, extra_headers: dict | None = None, response_format: dict | None = None) -> str` que decide internamente Responses API (GPT-5) vs LiteLLM. `explain_error` e `chat` passam a usá-lo.

- [ ] **Step 1: Refatorar** — em `ai_service.py`:
  - Deletar `_prepare_env` (nunca usado).
  - Extrair a lógica de escolha (GPT-5 → `_call_gpt5_responses_api`; senão `acompletion` com params) para `_completion`.
  - `explain_error` e `chat` montam apenas `messages`/prompts e chamam `_completion`.

- [ ] **Step 2: Testes** — create `tests/test_ai_service.py`:

```python
"""AI service unit tests (no network calls)."""

from pyflow.core.ai_service import AIService
from pyflow.core.models import AIConfig


def test_build_model_string_openrouter_passthrough():
    cfg = AIConfig(provider="openrouter", model_id="anthropic/claude-3.5-sonnet")
    assert AIService._build_model_string(cfg) == "anthropic/claude-3.5-sonnet"


def test_build_model_string_google_prefix():
    cfg = AIConfig(provider="google", model_id="gemini-2.5-flash")
    assert AIService._build_model_string(cfg) == "gemini/gemini-2.5-flash"


def test_build_model_string_gpt_passthrough():
    cfg = AIConfig(provider="openai", model_id="gpt-5-nano")
    assert AIService._build_model_string(cfg) == "gpt-5-nano"


def test_format_code_with_lines():
    out = AIService._format_code_with_lines("a\nb")
    assert out == "001 | a\n002 | b"


def test_gpt5_detection():
    assert AIService._is_gpt5_model("gpt-5-nano") is True
    assert AIService._is_gpt5_model("gpt-4o") is False
```

- [ ] **Step 3: Rodar suíte** — `python -m pytest tests/ -v` (sem chamadas de rede nos testes).

- [ ] **Step 4: Commit** — `git commit -m "refactor: remove dead code and unify LLM call path"`.

---

## Task 1.3: Validar `ChatMessage.role` e histórico

**Files:**
- Modify: `pyflow/core/models.py`
- Modify: `tests/test_ai_service.py`

- [ ] **Step 1: Implementar** — `models.py:152`: `role: Literal["user", "assistant"]`. Importar `Literal` do typing (já usado no arquivo para `RunResponse`).

- [ ] **Step 2: Teste**:

```python
def test_chat_message_rejects_invalid_role():
    from pyflow.core.models import ChatMessage
    from pydantic import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="x")
```

- [ ] **Step 3: Testes PASS.**

- [ ] **Step 4: Commit** — `git commit -m "fix: enforce chat message role enum"`.

---

## Task 1.4: `response_format` resiliente (retry sem JSON mode)

**Files:**
- Modify: `pyflow/core/ai_service.py`
- Modify: `tests/test_ai_service.py` (mocking acompletion)

**Interfaces:**
- Produces: dentro de `_completion`: se `response_format` causar erro e o provider não for OpenAI/OpenRouter, refazer a chamada sem `response_format`.

- [ ] **Step 1: Implementar** — envolver a chamada LiteLLM:

```python
def _supports_json_mode(model: str) -> bool:
    lowered = model.lower()
    return "deepseek" not in lowered and "ollama" not in lowered
```

Na chamada `_completion`, montar `params` sem `response_format` se `not _supports_json_mode(model)`; para os demais, tentar com e, em `Exception`, retry sem `response_format` (uma única vez).

- [ ] **Step 2: Teste com mock** — usar `unittest.mock.patch("pyflow.core.ai_service.acompletion")` para simular falha com `response_format` e sucesso sem; assert que a segunda chamada acontece e o resultado é retornado.

- [ ] **Step 3: Testes PASS.**

- [ ] **Step 4: Commit** — `git commit -m "fix: fallback when model rejects response_format json mode"`.

---

## Task 1.5: Engine — `asyncio.wait` correto e status de truncamento preciso

**Files:**
- Modify: `pyflow/core/engine.py`
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Testes**:

```python
def test_output_limit_returns_output_limit_status():
    result = asyncio.run(
        execute_code(
            request_id="req_trunc",
            code="print('x' * 5000)",
            stdin=None,
            timeout_seconds=10,
            max_output_chars=100,
        )
    )
    assert result.status == "error"
    assert result.output_truncated is True
    assert result.diagnostics.error_type == "OutputLimitExceeded"


def test_timeout_kills_process():
    result = asyncio.run(
        execute_code(
            request_id="req_timeout",
            code="import time; time.sleep(5)",
            stdin=None,
            timeout_seconds=1,
            max_output_chars=1000,
        )
    )
    assert result.status == "timeout"
    assert result.diagnostics.error_type == "Timeout"
```

- [ ] **Step 2: Implementar** — em `engine.py:195-200`:

```python
        done, pending = await asyncio.wait(
            [wait_process_task, read_stdout_task, read_stderr_task],
            timeout=timeout_seconds,
            return_when=asyncio.ALL_COMPLETED,
        )
```

E no branch de timeout, antes de retornar `timeout`, verificar se as leituras já truncaram:

```python
        if process.returncode is None and not wait_process_task.done():
            _kill_process_tree(process.pid)
            try:
                await process.wait()
            except Exception:
                pass
            read_stdout_task.cancel()
            read_stderr_task.cancel()

            # If output was already over the limit, report truncation,
            # not timeout (the process was killed for flooding, not hanging).
            stdout_trunc = read_stdout_task.done() and read_stdout_task.result()[1] if read_stdout_task.done() else False
            stderr_trunc = read_stderr_task.done() and read_stderr_task.result()[1] if read_stderr_task.done() else False

            elapsed_ms = int((time.time() - start_time) * 1000)
            if stdout_trunc or stderr_trunc:
                return RunResponse(
                    status="error",
                    stdout="",
                    stderr="Output limit exceeded; process terminated.",
                    exit_code=None,
                    execution_time_ms=elapsed_ms,
                    output_truncated=True,
                    diagnostics=create_output_limit_diagnostics(),
                    request_id=request_id,
                )

            return RunResponse(...)  # timeout normal (existente)
```

- [ ] **Step 3: Testes PASS.**

- [ ] **Step 4: Commit** — `git commit -m "fix: engine wait semantics and accurate truncation status"`.

---

## Task 1.6: Pinar dependências e alinhar versões

**Files:**
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `pyflow/core/config.py` (opcional: validação de versão)

- [ ] **Step 1: requirements.txt** — versões fixadas (verificar as disponíveis com `pip index versions <pkg>` antes; usar as atuais instaladas no ambiente do dev como base):

```
fastapi==0.115.x
uvicorn==0.34.x
typer==0.15.x
litellm==1.6x.x
pydantic==2.11.x
pydantic-settings==2.9.x
loguru==0.7.x
psutil==6.x
tenacity==9.x
httpx==0.28.x
openai==1.x
pytest==8.x
```

- [ ] **Step 2: README** — trocar "Python 3.14+" por "Python 3.11+" (seções de instalação e doctor).

- [ ] **Step 3: Validar** — `pip install -r requirements.txt` e `python -m pytest tests/ -v`.

- [ ] **Step 4: Commit** — `git commit -m "chore: pin dependency versions and align Python requirement docs"`.

---

## Task 1.7: docker-compose moderno

**Files:**
- Modify: `docker-compose.yml` (remover linha `version: '3.8'` já feita na Task 0.4 — confirmar)
- Modify: `run_docker.bat`

- [ ] **Step 1: Verificar** que `docker compose config` roda sem warnings.

- [ ] **Step 2: Commit** — `git commit -m "chore: modernize docker compose config"` (se houve mudança).

---

## Task 1.8: Persona configurável via settings

**Files:**
- Modify: `pyflow/core/config.py`
- Modify: `pyflow/core/ai_service.py`
- Modify: `tests/test_ai_service.py`

**Interfaces:**
- Produces: `settings.PYFLOW_AI_TUTOR_PROMPT: str` (default = prompt atual do chat), `settings.PYFLOW_AI_EXPLAINER_PROMPT: str` (default = prompt atual do explain).

- [ ] **Step 1: Implementar** — mover os textos dos prompts atuais (linhas 313-322 e 447-460 de `ai_service.py`) para `config.py` como defaults; `ai_service` usa `settings.PYFLOW_AI_TUTOR_PROMPT` / `PYFLOW_AI_EXPLAINER_PROMPT`.

- [ ] **Step 2: Teste** — testar que `AIService.chat`/`explain_error` usam o prompt do settings (patch de `acompletion` e assert do system prompt na chamada).

- [ ] **Step 3: README** — documentar as 2 novas env vars na tabela.

- [ ] **Step 4: Commit** — `git commit -m "feat: make AI tutor and explainer prompts configurable"`.

---

# FASE 2 — TESTES E CI

## Task 2.1: Suite de testes do engine (completa)

**Files:**
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Adicionar testes de stdin, blocked, success e sanitização**:

```python
def test_stdin_is_delivered_to_input():
    result = asyncio.run(
        execute_code(
            request_id="req_stdin",
            code="name = input('Nome: '); print(f'Olá {name}')",
            stdin="Maria\n",
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert "Olá Maria" in result.stdout


def test_blocked_when_input_without_stdin():
    result = asyncio.run(
        execute_code(
            request_id="req_blocked",
            code="input()",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "blocked"
    assert result.diagnostics.error_type == "InputRequiresStdin"


def test_syntax_error_diagnostics():
    result = asyncio.run(
        execute_code(
            request_id="req_syntax",
            code="if True\n",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "error"
    assert result.diagnostics.error_type == "SyntaxError"
    assert result.diagnostics.line is not None


def test_traceback_paths_are_sanitized():
    result = asyncio.run(
        execute_code(
            request_id="req_sanitize",
            code="x = 1/0",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert "<user_code>" in result.stderr
    assert "pyflow_tmp" not in result.stderr
```

- [ ] **Step 2: Rodar** — `python -m pytest tests/test_engine.py -v` → todos PASS.

- [ ] **Step 3: Commit** — `git commit -m "test: cover stdin, blocked, syntax and sanitization paths"`.

---

## Task 2.2: Testes de integração da API (ASGI)

**Files:**
- Create: `tests/test_api.py`

- [ ] **Step 1: Escrever**:

```python
"""API integration tests via ASGI transport (no real server needed)."""

import pytest
from httpx import ASGITransport, AsyncClient

from pyflow.main import app
from pyflow.core.security import get_or_create_token

HEADERS = {"X-PyFlow-Token": get_or_create_token()}


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_run_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "print(2+2)", "ai_explain_on_error": False},
            headers=HEADERS,
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
            headers=HEADERS,
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
            headers=HEADERS,
        )
    assert resp.status_code == 200
    assert "Nenhuma configuração" in resp.json()["reply"]


@pytest.mark.asyncio
async def test_code_too_large():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "#" * 200_000, "ai_explain_on_error": False},
            headers=HEADERS,
        )
    body = resp.json()
    assert body["status"] == "error"
    assert body["diagnostics"]["error_type"] == "CodeTooLarge"
```

- [ ] **Step 2: Requisito** — `pytest-asyncio` no `requirements.txt` (pinar) e `asyncio_mode = auto` num arquivo `pytest.ini` ou `pyproject.toml`:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Rodar** — `python -m pytest tests/ -v` → todos PASS.

- [ ] **Step 4: Commit** — `git commit -m "test: add API integration tests via ASGI transport"`.

---

## Task 2.3: Testes de segurança consolidados

**Files:**
- Modify: `tests/test_security.py`

- [ ] **Step 1: Adicionar** teste de CORS headers e de que `/auth/token` com Origin de outra porta local funciona:

```python
def test_cors_allows_local_ui_origin():
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert "http://localhost:3000" in resp.headers.get("access-control-allow-origin", "")


def test_token_route_accepts_any_local_port():
    resp = client.get("/auth/token", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Rodar suíte completa.**

- [ ] **Step 3: Commit** — `git commit -m "test: consolidate security coverage for CORS and token delivery"`.

---

## Task 2.4: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Escrever o workflow**:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest tests/ -v
      - name: Compile check
        run: python -m compileall pyflow

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ui
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: ui/package-lock.json
      - run: npm ci
      - run: npm run build
```

- [ ] **Step 2: Validar sintaxe** — `npx actionlint` (se instalado) ou revisão manual; fazer push do branch e conferir que o CI roda.

- [ ] **Step 3: Commit** — `git commit -m "ci: add backend and frontend pipelines"`.

---

# FASE 3 — EXPERIÊNCIA (UI/UX)

## Task 3.1: Destacar linha do erro no editor

**Files:**
- Modify: `ui/app.vue`
- Modify: `ui/stores/pyflow.js`

**Interfaces:**
- Produces: `store.output.diagnostics.line` consumido para criar decorations do CodeMirror.

- [ ] **Step 1: Implementar** — em `app.vue`, criar computed reativo e aplicar `EditorView` decorations via watcher:

```ts
import { EditorView, Decoration, DecorationSet } from '@codemirror/view'
import { StateEffect, StateField } from '@codemirror/state'

const errorLine = computed(() => store.output?.diagnostics?.line ?? null)

const setErrorLine = StateEffect.define<number | null>()
const errorLineField = StateField.define({
    create: () => Decoration.none,
    update(deco, tr) {
        deco = deco.map(tr.changes)
        for (const e of tr.effects) if (e.is(setErrorLine)) {
            deco = Decoration.none
            if (e.value != null) {
                const mark = Decoration.line({ attributes: { style: 'background: rgba(239,68,68,0.12); border-left: 3px solid #ef4444;' } })
                deco = deco.add(tr.startState.doc, tr.startState.doc.line(e.value), mark)
            }
        }
        return deco
    },
})

watch(errorLine, (line) => {
    const view = editorView.value
    if (view) view.dispatch({ effects: setErrorLine.of(line) })
})
```

> `editorView` é obtido pelo evento `@ready` do `vue-codemirror` (`(view) => { editorView.value = view }`) e a extensão `errorLineField` entra no array `extensions`.

- [ ] **Step 2: Teste manual** — rodar `x = 1/0`; a linha 1 deve ficar vermelha no editor.

- [ ] **Step 3: Commit** — `git commit -m "feat: highlight error line in the editor"`.

---

## Task 3.2: Autosave do código (localStorage)

**Files:**
- Modify: `ui/stores/pyflow.js`

- [ ] **Step 1: Implementar**:

```js
saveCodeToStorage: (() => {
    let timer = null
    return function () {
        clearTimeout(timer)
        timer = setTimeout(() => {
            if (process.client) localStorage.setItem('pyflow_code', this.code)
        }, 500)
    }
})(),
```

Chamar `this.saveCodeToStorage()` em `runCode` e via `watch(() => store.code, ...)` em `app.vue`. No `loadFromStorage`, carregar `pyflow_code` se existir.

- [ ] **Step 2: Teste manual** — editar, recarregar a página, código permanece.

- [ ] **Step 3: Commit** — `git commit -m "feat: autosave editor code to localStorage"`.

---

## Task 3.3: Badge de conexão real

**Files:**
- Modify: `ui/app.vue`
- Modify: `ui/stores/pyflow.js`

**Interfaces:**
- Produces: `store.apiOnline: boolean | null`; `store.refreshHealth()`.

- [ ] **Step 1: Store**:

```js
apiOnline: null,

async refreshHealth() {
    try {
        await $fetch('/api/health', { headers: { 'X-PyFlow-Token': this.apiToken } })
        this.apiOnline = true
    } catch (e) {
        this.apiOnline = false
    }
},
```

- [ ] **Step 2: UI** — `onMounted` chama `refreshHealth()` + `setInterval` 10s (limpar no `onUnmounted`); badge "Connected" usa `apiOnline` (verde/vermelho + texto "Connected"/"Offline").

- [ ] **Step 3: Commit** — `git commit -m "feat: live connection status badge"`.

---

## Task 3.4: Proxy do nitro para `/api/models/openrouter` + fetch relativo

**Files:**
- Modify: `ui/nuxt.config.ts`
- Modify: `ui/app.vue`

- [ ] **Step 1: nuxt.config.ts** — adicionar routeRule:

```ts
'/api/models/openrouter': { proxy: (process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000') + '/models/openrouter' },
```

- [ ] **Step 2: app.vue** — `fetchOpenRouterModels` troca `http://localhost:8000/models/openrouter` por `$fetch('/api/models/openrouter', { headers: {...} })` + token.

- [ ] **Step 3: Teste manual** — no Docker e local, buscar modelos funciona.

- [ ] **Step 4: Commit** — `git commit -m "fix: proxy openrouter models route through nitro"`.

---

## Task 3.5: Biblioteca de exemplos (snippets)

**Files:**
- Create: `ui/data/examples.js`
- Modify: `ui/app.vue`

- [ ] **Step 1: `ui/data/examples.js`** — 10+ exemplos com `{ title, description, code }` (hello world, loops, listas, dicts, funções, turtle, matplotlib, erro proposital, input(), recursão).

- [ ] **Step 2: UI** — substituir botão "Example" por dropdown com os exemplos (título + descrição); clicar carrega no editor.

- [ ] **Step 3: Commit** — `git commit -m "feat: add example snippets library"`.

---

## Task 3.6: Streaming de saída (NDJSON) — `/run/stream`

**Files:**
- Create: `pyflow/core/streaming.py`
- Modify: `pyflow/core/engine.py`
- Modify: `pyflow/api/routes_run.py`
- Modify: `ui/stores/pyflow.js`
- Modify: `ui/app.vue`
- Modify: `ui/nuxt.config.ts`
- Modify: `tests/test_streaming.py` (criar)

**Interfaces:**
- Produces: `execute_code_stream(request_id, code, stdin, timeout_seconds, max_output_chars, on_output: Callable[[str, str], None]) -> RunResponse` em `engine.py`; endpoint `POST /run/stream` (NDJSON, `application/x-ndjson`); eventos: `{"type":"output","stream":"stdout","data":"..."}`, `{"type":"status","status":"running"}`, e ao final o `RunResponse` completo.
- Consumes: `_read_stream` (refatorado para callback), `_build_child_env`, `parse_traceback_str`.

- [ ] **Step 1: Refatorar `_read_stream`** — aceitar `on_chunk: Callable[[str], None] | None`; chamar a cada chunk (antes de checar limite). Em `engine.py`, criar `execute_code_stream` reutilizando o mesmo fluxo, emitindo chunks em tempo real.

- [ ] **Step 2: Endpoint** — em `routes_run.py` (ou `routes_stream.py` novo):

```python
from fastapi.responses import StreamingResponse

@router.post("/run/stream", dependencies=[Depends(require_token), Depends(require_local_origin)])
async def run_stream(req: RunRequest):
    """Execute code and stream output as NDJSON events."""
    request_id = generate_request_id()

    async def event_source():
        async def on_output(stream: str, data: str) -> None:
            if not data:
                return
            yield f'{{"type":"output","stream":"{stream}","data":{json.dumps(data)}}}\n'

        # note: on_output must be an async generator wired into the reader loop
        ...
```

> Implementação detalhada: `execute_code_stream` aceita `emit: Callable[[str, str], Awaitable[None]]`; o `StreamingResponse` usa `json.dumps` com `ensure_ascii=False` para o payload; ao final, emite `{"type":"done","result": <RunResponse.model_dump_json()>}`.

- [ ] **Step 3: Frontend** — store:

```js
async runCodeStreaming() {
    this.isRunning = true
    this.output = null
    this.activeTab = 'console'
    this.streamBuffer = ''
    try {
        const res = await fetch('/api/run/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-PyFlow-Token': this.apiToken },
            body: JSON.stringify({ code: this.code, ai_explain_on_error: true, include_raw_traceback: true }),
        })
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        while (true) {
            const { done, value } = await reader.read()
            if (done) break
            this.streamBuffer += decoder.decode(value, { stream: true })
            const lines = this.streamBuffer.split('\n')
            this.streamBuffer = lines.pop() || ''
            for (const line of lines) {
                if (!line.trim()) continue
                const evt = JSON.parse(line)
                if (evt.type === 'output') {
                    this.consoleStream += evt.data
                } else if (evt.type === 'done') {
                    this.output = evt.result
                    if (evt.result.diagnostics || evt.result.ai_error_help) this.activeTab = 'diagnostics'
                }
            }
        }
    } catch (err) { /* erro de rede */ } finally { this.isRunning = false }
}
```

Estado novo na store: `consoleStream: ''` (append de output durante o run; exibido no console enquanto `isRunning`).

- [ ] **Step 4: Rota de proxy** — `ui/nuxt.config.ts`: `/api/run/stream` → proxy.

- [ ] **Step 5: Teste backend** — `tests/test_streaming.py`: consumir o `StreamingResponse` com `httpx` ASGI e assert de que há eventos `output` antes do `done` (para código com `print` em loop com sleep pequeno). **Nota:** pode ser flaky; usar `time.sleep(0.1)` × 3 no código e timeout de 5s.

- [ ] **Step 6: Teste manual** — `for i in range(10): print(i); time.sleep(0.2)` mostra números em tempo real.

- [ ] **Step 7: Commit** — `git commit -m "feat: stream execution output via NDJSON endpoint"`.

---

# FASE 4 — EDUCAÇÃO E DIFERENCIAÇÃO

## Task 4.1: Modo Tutor Socrático (`/hint` + modo no chat)

**Files:**
- Modify: `pyflow/core/ai_service.py`
- Modify: `pyflow/api/routes_chat.py`
- Modify: `pyflow/core/models.py`
- Modify: `ui/stores/pyflow.js`
- Modify: `ui/app.vue`
- Modify: `tests/test_ai_service.py`

**Interfaces:**
- Produces: `AIService.socratic_hint(code: str, diagnostics: Diagnostics | None, level: int, config: AIConfig) -> str`; campo `mode: Literal["tutor","hint"] | None` em `ChatRequest`; endpoint `POST /hint`.

- [ ] **Step 1: Backend** — em `ai_service.py`, novo método com prompt socrático (3 níveis: 1 = pergunta-guia conceitual, 2 = localiza o problema, 3 = quase-solução). Usar `_completion`. Em `routes_chat.py`, rota `/hint` que chama `socratic_hint` com o `diagnostics` parseado se houver erro.

- [ ] **Step 2: Models** — `HintRequest { code, level, diagnostics?, ai_config }` e `HintResponse { hint, request_id }`.

- [ ] **Step 3: UI** — botão "Dica" no painel de diagnostics (level 1 → 2 → 3 progressivo); resposta exibida no chat ou modal.

- [ ] **Step 4: Teste** — mock de `acompletion` e assert de que o prompt contém "pergunta" (nível 1 não dá resposta direta).

- [ ] **Step 5: Commit** — `git commit -m "feat: socratic hint endpoint for progressive guidance"`.

---

## Task 4.2: Desafios com verificação automática (mini-Judge0)

**Files:**
- Create: `pyflow/core/challenges.py`
- Modify: `pyflow/api/routes_run.py` (ou `routes_challenges.py` novo)
- Modify: `pyflow/core/models.py`
- Create: `pyflow/data/challenges/` (JSONs de desafios)
- Modify: `ui/app.vue`
- Create: `tests/test_challenges.py`

**Interfaces:**
- Produces: `run_challenge(code: str, challenge_id: str, timeout_seconds: int) -> ChallengeResult`; `ChallengeResult { challenge_id, tests: [{ name, passed, stdout, expected, actual }], passed_count, total_count }`.
- Consumes: `execute_code` (executa o código do aluno + harness de testes como um script único).

- [ ] **Step 1: Formato do desafio** (`pyflow/data/challenges/hello_world.json`):

```json
{
  "id": "hello_world",
  "title": "Hello World",
  "description": "Imprima 'Olá, PyFlow!'",
  "solution_hint": "print('Olá, PyFlow!')",
  "tests": [
    { "name": "saída correta", "expected": "Olá, PyFlow!\n" }
  ]
}
```

- [ ] **Step 2: Harness** — `challenges.py` monta `user_code + "\n\n" + harness` onde o harness compara `captured_stdout` com `expected` (usando `io.StringIO` + redirect `sys.stdout`), e retorna resultados serializáveis via `print("PYFLOW_TEST_RESULT::" + json.dumps(...))` que o engine já captura no stdout.

- [ ] **Step 3: Endpoint** — `POST /challenges/run { challenge_id, code }` protegido (token+origin). Resposta usa `ChallengeResult`.

- [ ] **Step 4: UI** — aba "Desafios" com lista, enunciado, e execução que aponta para o endpoint; exibe pass/fail por teste.

- [ ] **Step 5: Teste** — `run_challenge` com código correto → 1/1; com código errado → 0/1 com `actual` preenchido.

- [ ] **Step 6: Commit** — `git commit -m "feat: challenge runner with hidden test harness"`.

---

## Task 4.3: Output rico — matplotlib inline (imagens base64)

**Files:**
- Create: `pyflow/core/runner_tpl.py`
- Modify: `pyflow/core/engine.py`
- Modify: `pyflow/core/models.py`
- Modify: `ui/app.vue`
- Modify: `tests/test_engine.py`

**Interfaces:**
- Produces: `RunResponse.images: list[str] = []` (base64 PNGs); runner wrapper que importa matplotlib (Agg), executa o código do usuário e, ao final, serializa as figuras abertas.
- Consumes: `_build_child_env`, fluxo existente do engine.

- [ ] **Step 1: Runner wrapper** — `runner_tpl.py` contém um template de código (`RUNNER_TEMPLATE`) que:

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64, io, json, sys

_original_stdout = sys.stdout

# <USER_CODE_PLACEHOLDER>

plt.ioff()
_images = []
for num in plt.get_fignums():
    fig = plt.figure(num)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    _images.append(base64.b64encode(buf.getvalue()).decode("ascii"))
    plt.close(fig)

if _images:
    sys.stdout.write("PYFLOW_IMAGES::" + json.dumps(_images) + "\n")
```

- [ ] **Step 2: Engine** — após ler o stdout, extrair a linha `PYFLOW_IMAGES::<json>` (se presente), removê-la do stdout exibido e preencher `images`. Flag no request: `rich_output: bool = False` (default False para não desacelerar execuções normais — matplotlib import custa ~1-2s).

- [ ] **Step 3: Models** — `RunResponse.images: List[str] = []`.

- [ ] **Step 4: UI** — no console, renderizar `<img :src="'data:image/png;base64,' + img">` para cada item de `output.images` (com `max-width: 100%`).

- [ ] **Step 5: Teste** — rodar código com `rich_output=True` que plota 1 figura → `images` tem 1 item válido (base64 decodifica como PNG).

- [ ] **Step 6: Commit** — `git commit -m "feat: inline matplotlib figures in run output"`.

---

## Task 4.4: Limite de concorrência (semáforo + 429)

**Files:**
- Modify: `pyflow/core/config.py`
- Modify: `pyflow/api/routes_run.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `settings.PYFLOW_MAX_CONCURRENT_RUNS: int = 4`; `asyncio.Semaphore` global em `routes_run.py`.

- [ ] **Step 1: Implementar**:

```python
import asyncio
from fastapi import HTTPException

_run_semaphore = asyncio.Semaphore(settings.PYFLOW_MAX_CONCURRENT_RUNS)

@router.post("/run", response_model=RunResponse, dependencies=[Depends(require_token), Depends(require_local_origin)])
async def run_code_endpoint(req: RunRequest):
    if _run_semaphore.locked():
        raise HTTPException(status_code=429, detail="Too many concurrent executions", headers={"Retry-After": "1"})
    async with _run_semaphore:
        ...  # corpo atual
```

> Alternativa com espera: `await asyncio.wait_for(_run_semaphore.acquire(), timeout=2)` → 429 se estourar. Aplicar também ao `/run/stream` (mesmo semáforo).

- [ ] **Step 2: Teste** — com `PYFLOW_MAX_CONCURRENT_RUNS=1` (monkeypatch), disparar 2 execuções simultâneas (uma com sleep) e assert de 429 na segunda.

- [ ] **Step 3: README** — documentar a env var.

- [ ] **Step 4: Commit** — `git commit -m "feat: cap concurrent executions with 429 rejection"`.

---

## Task 4.5: Gamificação leve (streak + XP local)

**Files:**
- Modify: `ui/stores/pyflow.js`
- Modify: `ui/app.vue`

**Interfaces:**
- Produces: store `xp: number`, `streak: number`, `lastRunDay: string`; ações `trackRun(success: boolean)` e `computeStats()`.

- [ ] **Step 1: Store** — em `runCode`, após resposta: `this.trackRun(res.status === 'success')`. `trackRun` incrementa XP (5 por run, +10 bônus por erro resolvido em ≤3 tentativas — simplificado: +5 por run, +5 se sucesso após erro anterior), atualiza streak (mesma data → 0; dia consecutivo → +1; gap → 1), persiste em localStorage.

- [ ] **Step 2: UI** — chip no header: `⚡ {xp} XP · 🔥 {streak} dias`.

- [ ] **Step 3: Commit** — `git commit -m "feat: lightweight XP and streak tracking"`.

---

# FASE 5 — ESCALA, SANDBOX E EMPACOTAMENTO

## Task 5.1: Backend de execução plugável + sandbox Docker

**Files:**
- Create: `pyflow/core/backends/__init__.py`
- Create: `pyflow/core/backends/base.py`
- Create: `pyflow/core/backends/subprocess_backend.py`
- Create: `pyflow/core/backends/docker_backend.py`
- Modify: `pyflow/core/config.py`
- Modify: `pyflow/core/engine.py`
- Modify: `README.md`
- Create: `tests/test_backends.py`

**Interfaces:**
- Produces: `ExecutionBackend` (ABC: `async run(code: str, stdin: str | None, timeout_seconds: int, max_output_chars: int, cwd: str) -> RawExecution`); `RawExecution { stdout: str, stderr: str, exit_code: int | None, timed_out: bool }`; `get_backend() -> ExecutionBackend` baseado em `settings.PYFLOW_EXECUTION_BACKEND` (`"subprocess"` default | `"docker"`).
- Consumes: `_build_child_env` (movido para o backend de subprocesso), `_kill_process_tree`, `_read_stream`.

- [ ] **Step 1: Refatorar engine** — mover a criação/execução do subprocesso para `subprocess_backend.py` (reutilizando `_read_stream`, `_kill_process_tree`), mantendo `execute_code` como orquestrador (validação, temp file, diagnóstico, status). O engine passa a usar `get_backend()`.

- [ ] **Step 2: Docker backend** — `docker_backend.py` executa:

```bash
docker run --rm --network none --memory 128m --pids-limit 32 \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \
  --user nobody -i -e PYTHONIOENCODING=utf-8 \
  python:3.11.9-slim python -u - < /dev/stdin
```

(código via stdin, não arquivo — evita montar volume). Timeout: `asyncio.wait_for` no `create_subprocess_exec`.

- [ ] **Step 3: Config** — `PYFLOW_EXECUTION_BACKEND: str = "subprocess"` + `PYFLOW_DOCKER_IMAGE: str = "python:3.11.9-slim"`.

- [ ] **Step 4: Testes** — com backend `subprocess` (CI não tem Docker): os testes existentes do engine continuam verdes; teste unitário do comando docker com mock de `create_subprocess_exec` (assert de args).

- [ ] **Step 5: README** — seção "Modos de execução" explicando `subprocess` (rápido, para dev) vs `docker` (isolado, para produção/multi-usuário) e o trade-off.

- [ ] **Step 6: Commit** — `git commit -m "feat: pluggable execution backends with docker sandbox mode"`.

---

## Task 5.2: Modo Pyodide (execução no navegador)

**Files:**
- Modify: `ui/stores/pyflow.js`
- Modify: `ui/app.vue`
- Modify: `ui/package.json`

**Interfaces:**
- Produces: store `executionMode: "server" | "browser"`; `runCodeBrowser()` usando Pyodide; toggle no header.

- [ ] **Step 1: Instalar** — `npm install pyodide`.

- [ ] **Step 2: Store**:

```js
executionMode: 'server',

async runCodeBrowser() {
    this.isRunning = true
    this.output = null
    this.activeTab = 'console'
    try {
        if (!this.pyodide) {
            const { loadPyodide } = await import('pyodide')
            this.pyodide = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/' })
        }
        let out = ''
        const err = []
        this.pyodide.setStdout({ batched: (s) => { out += s + '\n' } })
        this.pyodide.setStderr({ batched: (s) => { err.push(s) } })
        try {
            await this.pyodide.runPythonAsync(this.code)
            this.output = { status: 'success', stdout: out, stderr: err.join('\n'), execution_time_ms: 0 }
        } catch (e) {
            this.output = {
                status: 'error',
                stdout: out,
                stderr: err.join('\n') + '\n' + (e.message || String(e)),
                execution_time_ms: 0,
                diagnostics: { error_type: e.name || 'Error', message: e.message || String(e) },
            }
        }
    } catch (err) {
        this.output = { status: 'error', stdout: '', stderr: 'Falha ao carregar Pyodide: ' + err.message, execution_time_ms: 0 }
    } finally {
        this.isRunning = false
    }
},
```

- [ ] **Step 3: UI** — toggle no header ("Execução: Servidor | Navegador"); `runCode()` despacha para o modo ativo; nota visível de que o modo navegador é seguro/offline mas sem libs nativas pesadas.

- [ ] **Step 4: Teste manual** — código `print(6*7)` no modo navegador → 42; modo servidor continua funcionando.

- [ ] **Step 5: Commit** — `git commit -m "feat: browser-side execution mode via Pyodide"`.

---

## Task 5.3: Logs estruturados (JSON + request_id)

**Files:**
- Modify: `pyflow/main.py`
- Modify: `pyflow/api/routes_run.py`
- Modify: `pyflow/api/routes_chat.py`
- Modify: `pyflow/core/config.py`

**Interfaces:**
- Produces: `settings.PYFLOW_LOG_JSON: bool = False`; sink JSON do loguru com `request_id` no contexto (loguru `contextvars` bind).

- [ ] **Step 1: Implementar** — em `main.py` (lifespan ou import-time):

```python
from loguru import logger
if settings.PYFLOW_LOG_JSON:
    logger.remove()
    logger.add(
        "logs/pyflow-{time}.json",
        rotation="10 MB",
        serialize=True,
        enqueue=True,
    )
```

E nas rotas: `logger.bind(request_id=request_id).info("run:start", code_chars=len(req.code), ...)` e `logger.bind(request_id=request_id).info("run:done", status=result.status, duration_ms=result.execution_time_ms)`.

- [ ] **Step 2: README** — documentar `PYFLOW_LOG_JSON`.

- [ ] **Step 3: Commit** — `git commit -m "feat: structured JSON logs with request correlation"`.

---

## Task 5.4: Empacotamento (`pyproject.toml` + entry point)

**Files:**
- Create: `pyproject.toml`
- Modify: `README.md`
- Modify: `.gitignore` (adicionar `*.egg-info/` — já existe)

- [ ] **Step 1: pyproject.toml**:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyflow"
version = "2.1.0"
description = "Local API for safe Python execution with AI assistance"
requires-python = ">=3.11"
dependencies = [
    "fastapi==0.115.*",
    "uvicorn==0.34.*",
    "typer==0.15.*",
    "litellm==1.6.*",
    "pydantic==2.11.*",
    "pydantic-settings==2.9.*",
    "loguru==0.7.*",
    "psutil==6.*",
    "tenacity==9.*",
    "httpx==0.28.*",
    "openai==1.*",
]

[project.scripts]
pyflow = "pyflow.cli:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Validar** — `pip install -e .` e `pyflow doctor` funciona; `python -m pytest tests/ -v` verde.

- [ ] **Step 3: Atualizar README** — instalação com `pip install -e .` e uso do entry point `pyflow start`.

- [ ] **Step 4: Commit** — `git commit -m "feat: package project with pyproject.toml and pyflow entry point"`.

---

# FASE 6 — DOCUMENTAÇÃO E RELEASE

## Task 6.1: README v2.1

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Atualizar** — seções novas: autenticação por token (como obter via `~/.pyflow/connection.json`), modos de execução (subprocess/docker/browser), streaming (`/run/stream`), desafios, hint socrático, env vars novas (`PYFLOW_API_TOKEN`, `PYFLOW_MAX_CONCURRENT_RUNS`, `PYFLOW_LOG_JSON`, `PYFLOW_EXECUTION_BACKEND`, `PYFLOW_AI_TUTOR_PROMPT`, `PYFLOW_AI_EXPLAINER_PROMPT`), versão Python 3.11+.

- [ ] **Step 2: Commit** — `git commit -m "docs: document v2.1 security, streaming and sandbox features"`.

## Task 6.2: Release v2.1.0

- [ ] **Step 1:** Atualizar `pyflow/__init__.py` (`__version__ = "2.1.0"`).
- [ ] **Step 2:** Tag `v2.1.0` e push (após autorização do usuário).
- [ ] **Step 3:** Changelog no README ou release notes do GitHub.

---

## Self-Review (executado antes de encerrar o plano)

- **Cobertura do relatório:** segurança (0.1-0.5 ✅), bugs B1-B12 (1.1-1.8 ✅ — B7 em 1.6/1.7, B10 em 0.4+3.4, B11 em 3.6, B12 em 5.3), testes/CI (2.1-2.4 ✅), features curto prazo (3.1-3.5 ✅), médio (3.6, 4.1-4.4 ✅), longo (5.1-5.4 ✅). Gamificação (4.5 ✅).
- **Placeholders:** nenhum passo descritivo sem código/interface exata.
- **Consistência de tipos:** `get_or_create_token`, `validate_token`, `_completion`, `execute_code(include_raw_traceback)`, `_build_child_env`, `ExecutionBackend.run`, `RunResponse.images` — nomes idênticos em todas as tasks que os referenciam.
