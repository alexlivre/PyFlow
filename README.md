# 📘 PyFlow API - Guia Completo e Definitivo

<p align="center">
  <strong>Versão 2.1.0</strong>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137-teal)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED)](https://www.docker.com)
[![Release](https://img.shields.io/github/v/release/alexlivre/PyFlow)](https://github.com/alexlivre/PyFlow/releases)
[![CI](https://github.com/alexlivre/PyFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/alexlivre/PyFlow/actions)

**PyFlow** é uma API local robusta construída em **FastAPI** para execução segura de código Python em subprocessos isolados, com captura de saída, diagnósticos de erros estruturados e integração com múltiplos provedores de Inteligência Artificial (OpenAI, Gemini, Anthropic, OpenRouter, DeepSeek, Ollama, MiniMax, OpenCode Zen/Go) para explicação de erros e chat contextual.

Este documento é o **guia definitivo** para desenvolvedores que desejam consumir a API do PyFlow, criar suas próprias interfaces gráficas (UIs), ou simplesmente entender todas as suas funcionalidades em detalhes.

---

## 📑 Índice

1.  [🐳 Início Rápido com Docker (Recomendado)](#-início-rápido-com-docker-recomendado)
2.  [Visão Geral](#-visão-geral)
3.  [Instalação e Configuração](#-instalação-e-configuração)
    *   [Instalando Dependências](#1-instalando-dependências)
    *   [Variáveis de Ambiente](#2-variáveis-de-ambiente-opcional)
4.  [🔐 Autenticação por Token](#-autenticação-por-token)
5.  [Modos de Execução](#-modos-de-execução)
6.  [Iniciando o Servidor da API](#-iniciando-o-servidor-da-api)
    *   [Via Módulo Python](#via-módulo-python-simples)
    *   [Via CLI (Typer)](#via-cli-typer)
    *   [Comando `doctor`](#comando-doctor-para-diagnóstico)
7.  [Rodando a Interface Gráfica (UI)](#-rodando-a-interface-gráfica-ui)
8.  [Documentação Completa dos Endpoints](#-documentação-completa-dos-endpoints)
    *   [`GET /health`](#1-get-health---verificar-saúde-do-serviço)
    *   [`POST /run`](#2-post-run---executar-código-python)
    *   [`POST /run/stream`](#3-post-runstream---execução-com-streaming)
    *   [`POST /chat`](#4-post-chat---chat-contextual-com-ia)
    *   [`POST /hint`](#5-post-hint---dica-socrática-com-ia)
    *   [`GET /challenges`](#6-get-challenges---listar-desafios)
    *   [`POST /challenges/run`](#7-post-challengesrun---executar-desafio)
    *   [`GET /auth/token`](#8-get-authtoken---obter-token-da-api)
    *   [`GET /models/openrouter`](#9-get-modelsopenrouter---listar-modelos-do-openrouter)
9.  [Modelos de Dados (Schemas)](#-modelos-de-dados-schemas)
10. [Configuração de Provedores de IA (`ai_config`)](#-configuração-de-provedores-de-ia-ai_config)
11. [Tratamento de Erros e Status de Resposta](#-tratamento-de-erros-e-status-de-resposta)
    *   [Status `success`](#status-success)
    *   [Status `error`](#status-error)
    *   [Status `blocked`](#status-blocked)
    *   [Status `timeout`](#status-timeout)
12. [Estrutura do Projeto](#-estrutura-do-projeto)
13. [Referência Rápida](#-referência-rápida)
14. [🛠️ Built with](#️-built-with)
15. [🙏 Agradecimentos](#-agradecimentos)
16. [🔗 Links](#-links)
17. [📝 Licença](#-licen%C3%A7a)

---

## 🐳 Início Rápido com Docker (Recomendado)

> **⚡ Esta é a forma mais rápida e eficiente de rodar o PyFlow!**
>
> Com apenas um comando, você terá a API e a Interface rodando juntas, sem precisar instalar Python, Node.js ou qualquer dependência manualmente.

### Pré-requisitos

*   [Docker](https://www.docker.com/products/docker-desktop/) instalado e rodando
*   [Docker Compose](https://docs.docker.com/compose/) (geralmente incluído no Docker Desktop)

### Passos

**1. Clone o repositório (se ainda não tiver):**
```bash
git clone <url-do-repositorio>
cd PyFlow
```

**2. Execute o script de inicialização:**

**Windows:**
```powershell
.\run_docker.bat
```

**Linux/macOS:**
```bash
docker-compose up --build
```

**3. Aguarde a compilação** (pode levar alguns minutos na primeira vez).

**4. Acesse a interface:**
```
http://localhost:3000
```

> 📝 **Nota:** A API estará disponível em `http://localhost:8000`

### Parando os Contêineres

```bash
docker-compose down
```

### Desenvolvimento com Docker

O `docker-compose.yml` está configurado em **modo de desenvolvimento**:
*   Alterações no código Python (backend) são recarregadas automaticamente
*   Alterações no código Vue/Nuxt (frontend) usam Hot Module Replacement (HMR)
*   Não é necessário reconstruir os contêineres após editar o código

---

## 🎯 Visão Geral

O PyFlow foi projetado para ser o motor de execução de código para aplicações educacionais, playgrounds de código e qualquer cenário onde seja necessário executar Python de forma segura e obter feedback inteligente.

**Principais Funcionalidades:**

*   **Execução Isolada:** Código é executado em subprocessos separados, não afetando o servidor.
*   **Timeout:** Configurável para evitar loops infinitos.
*   **Limites de Saída:** Evita ataques de consumo de memória (e.g., `print` infinito).
*   **Suporte a `stdin`:** Permite executar código que usa `input()`.
*   **Diagnósticos Estruturados:** Erros são parseados para extrair tipo, mensagem, linha e contexto.
*   **Streaming de Saída:** `POST /run/stream` entrega stdout/stderr em tempo real via eventos NDJSON.
*   **Saída Rica:** Figuras `matplotlib` são capturadas como PNGs base64 no campo `images`.
*   **Desafios com Verificação Automática:** Testes ocultos são executados e avaliados no servidor (mini-Judge0).
*   **Dica Socrática:** Orientação progressiva em 3 níveis sem entregar a solução pronta.
*   **Autenticação por Token:** Toda rota (exceto `/health`) exige o header `X-PyFlow-Token`.
*   **Explicação de Erros por IA:** Quando um erro ocorre, a IA pode gerar uma explicação e código corrigido.
*   **Chat Contextual:** Converse com a IA sobre o código no editor.
*   **Multi-Provedor de IA:** Suporte a OpenAI, Gemini, Anthropic, DeepSeek, OpenRouter (400+ modelos) e Ollama (local).
*   **Modos de Execução:** `subprocess` (local), `docker` (sandbox endurecido) e `browser` (Pyodide, direto no navegador).

---

## 🛠️ Instalação e Configuração

### 1. Instalando Dependências

Certifique-se de ter **Python 3.11+** instalado. No diretório raiz do projeto:

```bash
pip install -e .
```

A instalação **editable** disponibiliza o pacote `pyflow` e o entry point
`pyflow` (CLI) — veja [Via CLI (Typer)](#via-cli-typer) abaixo.

> **Nota:** as versões das dependências em `pyproject.toml` são o espelho
> das fixadas em `requirements.txt`. Para testes, instale também o extra de
> desenvolvimento: `pip install -e ".[dev]"`.

Alternativamente, sem instalar o pacote, é possível instalar apenas as
dependências:

```bash
pip install -r requirements.txt
```

**Dependências Principais:**
*   `fastapi`, `uvicorn`: Framework web.
*   `litellm`: Abstração para múltiplos provedores de IA.
*   `openai`: SDK oficial da OpenAI (para modelos GPT-5).
*   `pydantic`, `pydantic-settings`: Validação de dados.
*   `psutil`: Gerenciamento de processos.
*   `typer`: CLI.
*   `loguru`: Logging.
*   `httpx`: Cliente HTTP assíncrono.
*   `tenacity`: Retries.

### 2. Variáveis de Ambiente (Opcional)

Você pode configurar o PyFlow via variáveis de ambiente ou arquivo `.env` na raiz do projeto.

| Variável                         | Descrição                                              | Padrão        |
| -------------------------------- | ------------------------------------------------------ | ------------- |
| `PYFLOW_HOST`                    | Endereço do host do servidor                           | `127.0.0.1`   |
| `PYFLOW_DEFAULT_PORT`            | Porta padrão do servidor                               | `8000`        |
| `PYFLOW_PORT_SEARCH_MAX_TRIES`   | Quantas portas testar se a padrão estiver ocupada      | `50`          |
| `PYFLOW_DEFAULT_TIMEOUT_SECONDS` | Timeout padrão para execução de código (segundos)      | `30`          |
| `PYFLOW_MAX_CODE_CHARS`          | Limite máximo de caracteres do código                  | `100000`      |
| `PYFLOW_MAX_OUTPUT_CHARS_DEFAULT`| Limite padrão de caracteres na saída                   | `100000`      |
| `PYFLOW_MAX_OUTPUT_CHARS_MAX`    | Limite máximo absoluto de caracteres na saída          | `500000`      |
| `PYFLOW_MAX_CONCURRENT_RUNS`     | Máximo de execuções simultâneas (429 quando excedido)  | `4`           |
| `PYFLOW_EXECUTION_BACKEND`       | Backend de execução: `subprocess` ou `docker`          | `subprocess`  |
| `PYFLOW_DOCKER_IMAGE`            | Imagem usada pelo backend docker                       | `python:3.11.9-slim` |
| `PYFLOW_LOG_JSON`                | Logs estruturados JSON com request_id em `logs/`       | `false`       |
| `PYFLOW_AI_MAX_TOKENS`           | Máximo de tokens para respostas da IA                  | `800`         |
| `PYFLOW_AI_TEMPERATURE`          | Temperatura para geração da IA                         | `1.0`         |
| `PYFLOW_AI_EXPLAINER_PROMPT`     | Persona/prompt do assistente de explicação de erros    | *(padrão interno)* |
| `PYFLOW_AI_TUTOR_PROMPT`         | Persona/prompt do tutor de chat                        | *(padrão interno)* |
| `PYFLOW_API_TOKEN`               | Token de API fixo. Se definido, substitui o token auto-gerado em `~/.pyflow/token` | `null` (auto-gerado) |
| `OPENAI_API_KEY`                 | Chave de API da OpenAI (fallback)                      | `null`        |
| `GEMINI_API_KEY`                 | Chave de API do Google Gemini (fallback)               | `null`        |
| `ANTHROPIC_API_KEY`              | Chave de API da Anthropic (fallback)                   | `null`        |
| `DEEPSEEK_API_KEY`               | Chave de API do DeepSeek (fallback)                    | `null`        |
| `OPENROUTER_API_KEY`             | Chave de API do OpenRouter (fallback)                  | `null`        |
| `MINIMAX_API_KEY`                | Chave de API do MiniMax (fallback)                     | `null`        |
| `OPENCODE_API_KEY`               | Chave de API do OpenCode Zen (fallback)                | `null`        |
| `OPENCODE_GO_API_KEY`            | Chave de API do OpenCode Go (fallback)                 | `null`        |

> **Nota:** As chaves de API também podem ser passadas diretamente no corpo da requisição via `ai_config.api_key`.

---

## 🔐 Autenticação por Token

Desde a v2.1, **todas as rotas da API exigem autenticação por token** —
exceto `GET /health`, que permanece público para monitoramento e descoberta.
Além do token, as rotas também validam a **origem** da requisição (defesa
contra CSRF).

### Como o token funciona

1.  Na primeira execução, o servidor **gera um token aleatório** e o persiste
    em `~/.pyflow/token` (permissões `0600`).
2.  Se a variável `PYFLOW_API_TOKEN` estiver definida, ela **substitui** o
    token auto-gerado.
3.  Todo cliente (UI, scripts, curl) deve enviar o token no header:

    ```http
    X-PyFlow-Token: <token>
    ```

### Obtendo o token

**Via arquivo de conexão (recomendado):** ao iniciar o servidor (CLI ou
módulo), o PyFlow escreve `~/.pyflow/connection.json` com a configuração de
descoberta, incluindo o token:

```json
{
  "host": "127.0.0.1",
  "port": 8000,
  "url": "http://127.0.0.1:8000",
  "pid": 12345,
  "version": "2.1.0",
  "status": "online",
  "token": "<token>"
}
```

**Via arquivo de token:** leia diretamente de `~/.pyflow/token`.

**Via endpoint `GET /auth/token`:** para UIs locais (a UI oficial usa um proxy
`/api/token`), que retorna o token sem exigir o próprio header:

```http
GET /auth/token
```

```json
{
  "token": "<token>"
}
```

> ⚠️ O endpoint `/auth/token` exige apenas **origem local** (`localhost`,
> `127.0.0.1`, `::1`) — ele não exige o header de token, justamente para
> permitir o primeiro acesso. Nunca exponha o servidor para a internet.

### Comportamento de erro

| Cenário                                | Status | Detalhe                                       |
| -------------------------------------- | ------ | --------------------------------------------- |
| Token ausente ou inválido              | `401`  | `Invalid or missing X-PyFlow-Token`           |
| Origin não local (CSRF)                | `403`  | `Cross-origin requests are not allowed`       |
| Host não permitido (`Host` header)     | `403`  | `Non-local host not allowed`                  |

**Exemplo com curl:**

```bash
TOKEN=$(cat ~/.pyflow/token)

curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-PyFlow-Token: $TOKEN" \
  -d '{"code": "print(1+1)", "ai_explain_on_error": false}'
```

---

## ⚙️ Modos de Execução

O PyFlow roteia a execução de código através de um backend plugável,
controlado pela variável `PYFLOW_EXECUTION_BACKEND`:

| Backend      | Descrição                                                            | Uso recomendado                    |
| ------------ | -------------------------------------------------------------------- | ---------------------------------- |
| `subprocess` | Executa em um processo filho local, com ambiente restrito (whitelist de variáveis, timeout, limites de saída). Rápido e sem dependências externas. | Desenvolvimento e ambientes de confiança única. |
| `docker`     | Executa em um container efêmero endurecido (`--network none`, memória e processos limitados, filesystem read-only, sem capabilities, sem novos privilégios, usuário `nobody`). Isolamento real do host. | Produção e ambientes multi-usuário. |
| `browser`    | Executa **no navegador** via **Pyodide** (WebAssembly), sem passar pela API. Toggle na UI (`Servidor`/`Navegador`). Seguro e offline, porém sem bibliotecas nativas e sem acesso ao servidor. | Estudos e ambientes sem servidor.  |

### Trade-off

O backend `subprocess` é mais rápido (sem overhead de container) e
suporta código interativo (`input()` com o campo `stdin`), mas o
processo filho compartilha o kernel do host — um código malicioso tem
acesso ao que o usuário do processo consegue acessar.

O backend `docker` executa o código em um sandbox isolado e fortemente
restrito; o daemon do Docker deve estar em execução, e a imagem
`python:3.11.9-slim` é baixada na primeira execução. **Limitação v1**:
código que usa `input()` com o campo `stdin` não é suportado no modo
docker (o código trafega pelo stdin do container) — a requisição falha
com erro explícito (`NotImplementedError`) em vez de degradar
silenciosamente para o subprocesso local. Use `subprocess` para código
interativo.

O comando `docker run` endurecido usado por execução é:

```bash
docker run --rm \
  --network none \
  --memory 128m \
  --pids-limit 32 \
  --read-only \
  --tmpfs /tmp \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user nobody \
  -i \
  -e PYTHONIOENCODING=utf-8 \
  python:3.11.9-slim \
  python -u -
```

O modo `browser` (Pyodide) é um runtime WebAssembly carregado de um CDN
(`https://cdn.jsdelivr.net/pyodide/v0.26.4/full/`) na primeira execução —
seguro por design (roda no sandbox do navegador, sem contato com o
servidor) e funcional offline após o primeiro carregamento, mas limitado
à biblioteca padrão do Python: sem bibliotecas nativas (ex.: `numpy` com
SIMD, `matplotlib`) e sem acesso à API do PyFlow (chat, dicas e desafios
continuam exigindo o modo servidor).

Para trocar o backend:

```bash
# Linux/macOS
PYFLOW_EXECUTION_BACKEND=docker python -m pyflow.main

# Windows (PowerShell)
$env:PYFLOW_EXECUTION_BACKEND="docker"; python -m pyflow.main
```

---

## 🚀 Iniciando o Servidor da API

### Via Módulo Python (Simples)

```bash
python -m pyflow.main
```

Isso iniciará o servidor em `http://127.0.0.1:8000`.

### Via CLI (Typer)

O PyFlow inclui uma CLI para gerenciamento:

```bash
# Iniciar com opções padrão
pyflow start

# Especificar host e porta
pyflow start --host 0.0.0.0 --port 9000
```

A CLI automaticamente:
1.  Busca uma porta disponível se a padrão estiver ocupada.
2.  Cria um arquivo `~/.pyflow/connection.json` para que clientes descubram a porta — o arquivo também contém o **token da API** (ver [Autenticação por Token](#-autenticação-por-token)).

### Comando `doctor` (para Diagnóstico)

Verifica se o ambiente está configurado corretamente:

```bash
pyflow doctor
```

Saída esperada:
```
🏥 PyFlow Doctor 🏥

✅ Python Version: 3.11.4
✅ Write Access to C:\Users\<user>\.pyflow
✅ Dependency 'fastapi' installed
✅ Dependency 'uvicorn' installed
...
All checks completed.
```

---

## 🖥️ Rodando a Interface Gráfica (UI)

O projeto inclui uma UI moderna em **Nuxt.js 3** com **TailwindCSS** e suporte a **CodeMirror**.

### Pré-requisitos
*   Node.js (v18 ou superior)
*   npm

### Passos

1.  **Navegue até a pasta da UI:**
    ```bash
    cd ui
    ```

2.  **Instale as dependências:**
    ```bash
    npm install
    ```

3.  **Inicie o servidor de desenvolvimento:**
    ```bash
    npm run dev
    ```

4.  **Acesse no navegador:** `http://localhost:3000`

> ⚠️ **Importante:** Certifique-se de que a API (backend) esteja rodando na porta `8000` para que a UI possa comunicar-se corretamente.

---

## 📚 Documentação Completa dos Endpoints

**Base URL:** `http://127.0.0.1:8000`

---

### 1. `GET /health` - Verificar Saúde do Serviço

Verifica se o servidor PyFlow está online e retorna metadados.

**Requisição:**
```http
GET /health
```

**Resposta (200 OK):**
```json
{
  "status": "ok",
  "service": "pyflow",
  "version": "2.0.0",
  "pid": 12345,
  "time": "2025-12-21T15:00:00-0300"
}
```

**Campos da Resposta:**
| Campo     | Tipo   | Descrição                                 |
| --------- | ------ | ----------------------------------------- |
| `status`  | string | Status do serviço (`ok`)                  |
| `service` | string | Nome do serviço (`pyflow`)                |
| `version` | string | Versão do PyFlow                          |
| `pid`     | int    | ID do processo do servidor                |
| `time`    | string | Timestamp atual (ISO 8601)                |

---

### 2. `POST /run` - Executar Código Python

Executa código Python através do backend configurado (`subprocess` ou
`docker`) e retorna o resultado.

**Requisição:**
```http
POST /run
Content-Type: application/json
```

**Corpo da Requisição (Todos os Campos):**
```json
{
  "code": "import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])\nprint('Olá')\nx = 1/0",
  "stdin": null,
  "timeout_seconds": 30,
  "max_output_chars": 100000,
  "include_raw_traceback": false,
  "rich_output": true,
  "ai_explain_on_error": true,
  "ai_config": {
    "provider": "openai",
    "model_id": "gpt-4o",
    "api_key": "sk-...",
    "base_url": null
  }
}
```

**Descrição dos Campos da Requisição:**
| Campo                   | Tipo           | Obrigatório | Descrição                                                                            |
| ----------------------- | -------------- | ----------- | ------------------------------------------------------------------------------------ |
| `code`                  | string         | ✅ Sim       | Código Python a ser executado                                                        |
| `stdin`                 | string \| null | ❌ Não       | Entrada padrão para o código (para `input()`)                                        |
| `timeout_seconds`       | int \| null    | ❌ Não       | Tempo máximo de execução (padrão: 30s)                                               |
| `max_output_chars`      | int \| null    | ❌ Não       | Limite de caracteres na saída (padrão: 100000)                                       |
| `include_raw_traceback` | bool           | ❌ Não       | Se `true`, inclui traceback completo em `diagnostics.raw_traceback`                  |
| `rich_output`           | bool           | ❌ Não       | Saída rica: captura figuras `matplotlib` como PNGs base64 em `images` (padrão: `false`) |
| `ai_explain_on_error`   | bool           | ❌ Não       | Se `true` e houver erro, solicita explicação à IA                                    |
| `ai_config`             | object \| null | ❌ Não       | Configuração do provedor de IA (ver seção dedicada)                                  |

---

#### Resposta Completa (`RunResponse`)

```json
{
  "status": "error",
  "stdout": "Olá\n",
  "stderr": "Traceback (most recent call last):\n  File \"<user_code>\", line 2, in <module>\n    x = 1/0\n        ~^~\nZeroDivisionError: division by zero\n",
  "exit_code": 1,
  "execution_time_ms": 120,
  "output_truncated": false,
  "diagnostics": {
    "error_type": "ZeroDivisionError",
    "message": "division by zero",
    "line": 2,
    "context": "x = 1/0\n~^~",
    "raw_traceback": null
  },
  "images": [
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9...",
    "..."
  ],
  "ai_error_help": {
    "summary": "Você tentou dividir um número por zero na linha 2, o que é uma operação matemática inválida.",
    "probable_fix": "Verifique se o divisor não é zero antes de realizar a divisão.",
    "suggested_code": "print('Olá')\nif 0 != 0:\n    x = 1/0\nelse:\n    print('Divisão por zero!')"
  },
  "request_id": "req_abc123"
}
```

**Descrição dos Campos da Resposta:**
| Campo              | Tipo           | Descrição                                                                        |
| ------------------ | -------------- | -------------------------------------------------------------------------------- |
| `status`           | string         | Status da execução: `success`, `error`, `blocked`, `timeout`                     |
| `stdout`           | string         | Saída padrão capturada                                                           |
| `stderr`           | string         | Saída de erro capturada (traceback)                                              |
| `exit_code`        | int \| null    | Código de saída do processo                                                      |
| `execution_time_ms`| int            | Tempo de execução em milissegundos                                               |
| `output_truncated` | bool           | `true` se a saída foi truncada por exceder o limite                              |
| `diagnostics`      | object \| null | Informações estruturadas do erro (ver abaixo)                                    |
| `images`           | string[]       | Figuras `matplotlib` capturadas como PNGs base64 (requer `rich_output: true`)    |
| `ai_error_help`    | object \| null | Explicação da IA sobre o erro (ver abaixo)                                       |
| `request_id`       | string         | Identificador único da requisição                                                |

> **Saída Rica (`rich_output`):** com `rich_output: true`, o código é
> executado dentro de um wrapper que, ao final, renderiza qualquer figura
> `matplotlib` ainda aberta para PNG e a entrega em `images` (base64).
> Requer `matplotlib` instalado no ambiente de execução; se a biblioteca
> estiver ausente, o código continua rodando normalmente e `images` vem
> vazio — nunca causa falha na execução.

---

### 3. `POST /run/stream` - Execução com Streaming

Igual ao `/run`, porém a saída (stdout/stderr) é entregue **em tempo real**
como uma sequência de eventos **NDJSON** (uma linha JSON por evento),
`Content-Type: application/x-ndjson`.

**Requisição:**
```http
POST /run/stream
Content-Type: application/json
X-PyFlow-Token: <token>
```

O corpo é o mesmo `RunRequest` do `/run`. A requisição respeita o mesmo
semáforo de concorrência — quando o limite `PYFLOW_MAX_CONCURRENT_RUNS` é
atingido, responde `429` com `Retry-After: 1`.

**Eventos emitidos:**

| Evento                          | Campos                                                        |
| ------------------------------- | ------------------------------------------------------------- |
| `{"type": "status", ...}`       | `status: "running"` — enviado logo no início                  |
| `{"type": "output", ...}`       | `stream: "stdout" \| "stderr"`, `data: "<chunk>"` — 0..n vezes|
| `{"type": "done", ...}`         | `result: RunResponse` — evento final em execução bem-sucedida |
| `{"type": "error", ...}`        | `message: "<erro interno>"` — substitui `done` em falha       |

**Exemplo de uso (fetch + ReadableStream):**

```javascript
const res = await fetch('http://localhost:8000/run/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-PyFlow-Token': localStorage.getItem('pyflow_token'),
  },
  body: JSON.stringify({ code: "for i in range(5): print(i)" }),
});

const reader = res.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  for (const line of decoder.decode(value).trim().split('\n')) {
    if (!line) continue;
    const event = JSON.parse(line);
    if (event.type === 'output') {
      console.log(`[${event.stream}] ${event.data}`);
    } else if (event.type === 'done') {
      console.log('Resultado final:', event.result);
    } else if (event.type === 'error') {
      console.error('Erro interno:', event.message);
    }
  }
}
```

---

### 4. `POST /chat` - Chat Contextual com IA

Envia uma mensagem para a IA, incluindo o código atual como contexto.

**Requisição:**
```http
POST /chat
Content-Type: application/json
```

**Corpo da Requisição:**
```json
{
  "user_message": "O que este código faz?",
  "code": "def fib(n):\n  return n if n <= 1 else fib(n-1) + fib(n-2)",
  "history": [
    {"role": "user", "content": "Olá"},
    {"role": "assistant", "content": "Olá! Como posso ajudar?"}
  ],
  "ai_config": {
    "provider": "openrouter",
    "model_id": "anthropic/claude-3.5-sonnet",
    "api_key": "sk-or-..."
  }
}
```

**Descrição dos Campos:**
| Campo          | Tipo           | Obrigatório | Descrição                                                |
| -------------- | -------------- | ----------- | -------------------------------------------------------- |
| `user_message` | string         | ✅ Sim       | Mensagem do usuário                                      |
| `code`         | string \| null | ❌ Não       | Código atual no editor para contexto                     |
| `history`      | array          | ❌ Não       | Histórico de mensagens anteriores (roles: `user`, `assistant`) |
| `ai_config`    | object \| null | ❌ Não       | Configuração do provedor de IA                           |

**Resposta:**
```json
{
  "reply": "Esta função calcula o n-ésimo número da sequência de Fibonacci de forma recursiva...",
  "history": [
    {"role": "user", "content": "Olá"},
    {"role": "assistant", "content": "Olá! Como posso ajudar?"},
    {"role": "user", "content": "O que este código faz?"},
    {"role": "assistant", "content": "Esta função calcula..."}
  ],
  "request_id": "req_xyz789"
}
```

---

### 5. `POST /hint` - Dica Socrática com IA

Gera uma orientação **progressiva** (níveis 1 a 3) sobre o código do
usuário, no estilo socrático: a IA guia o aluno à descoberta do erro sem
entregar a solução pronta. Na UI, o botão **Dica** no painel de
diagnósticos usa este endpoint.

**Requisição:**
```http
POST /hint
Content-Type: application/json
X-PyFlow-Token: <token>
```

**Corpo da Requisição:**
```json
{
  "code": "x = 10\nprint(y)",
  "level": 2,
  "diagnostics": {
    "error_type": "NameError",
    "message": "name 'y' is not defined",
    "line": 2,
    "context": "print(y)"
  },
  "ai_config": {
    "provider": "openai",
    "model_id": "gpt-4o",
    "api_key": "sk-..."
  }
}
```

**Descrição dos Campos:**
| Campo          | Tipo           | Obrigatório | Descrição                                                    |
| -------------- | -------------- | ----------- | ------------------------------------------------------------ |
| `code`         | string         | ✅ Sim       | Código Python atual no editor                                |
| `level`        | int            | ❌ Não       | Nível da dica, `1` a `3` (padrão: `1`; valores fora do range são rejeitados com 422) |
| `diagnostics`  | object \| null | ❌ Não       | Diagnóstico do erro (usado nos níveis 2 e 3)                 |
| `ai_config`    | object \| null | ❌ Não       | Configuração do provedor de IA                               |

**Níveis de dica:**

| Nível | Comportamento da IA                                                        |
| ----- | -------------------------------------------------------------------------- |
| `1`   | **Pergunta-guia conceitual** — sem solução e sem mencionar a linha do erro  |
| `2`   | **Localiza o problema** — indica a linha aproximada e o conceito envolvido  |
| `3`   | **Quase-solução** — aponta a causa exata e oferece um esboço/pseudocódigo   |

**Resposta:**
```json
{
  "hint": "Observe a linha 2: `y` está sendo usado antes de existir...",
  "request_id": "req_hint_123"
}
```

> **Nota:** se `ai_config` não for fornecido, a resposta vem com uma
> mensagem de erro amigável em `hint` em vez de falhar a requisição.

---

### 6. `GET /challenges` - Listar Desafios

Lista o catálogo público dos desafios disponíveis (aba **Desafios** na UI).
Os **testes são ocultos** — eles rodam no servidor.

**Requisição:**
```http
GET /challenges
X-PyFlow-Token: <token>
```

**Resposta (200 OK):**
```json
[
  {
    "id": "hello_world",
    "title": "Hello World",
    "description": "Imprima 'Olá, PyFlow!'",
    "solution_hint": "print('Olá, PyFlow!')"
  },
  {
    "id": "fizzbuzz",
    "title": "FizzBuzz",
    "description": "Escreva uma função fizzbuzz(n) que retorna...",
    "solution_hint": "def fizzbuzz(n):\n    ..."
  }
]
```

**Campos da Resposta (`ChallengeInfo`):**
| Campo            | Tipo   | Descrição                           |
| ---------------- | ------ | ----------------------------------- |
| `id`             | string | Identificador do desafio            |
| `title`          | string | Título do desafio                   |
| `description`    | string | Enunciado do desafio                |
| `solution_hint`  | string | Dica de solução (o aluno pode consultar) |

---

### 7. `POST /challenges/run` - Executar Desafio

Executa o código do aluno contra os **testes ocultos** do desafio e
retorna o resultado de cada teste (mini-Judge0).

**Requisição:**
```http
POST /challenges/run
Content-Type: application/json
X-PyFlow-Token: <token>
```

**Corpo da Requisição:**
```json
{
  "challenge_id": "hello_world",
  "code": "print('Olá, PyFlow!')",
  "timeout_seconds": 30
}
```

**Resposta (200 OK):**
```json
{
  "challenge_id": "hello_world",
  "tests": [
    {
      "name": "saída correta",
      "passed": true,
      "stdout": "Olá, PyFlow!\n",
      "expected": "Olá, PyFlow!\n",
      "actual": "Olá, PyFlow!\n"
    }
  ],
  "passed_count": 1,
  "total_count": 1
}
```

**Campos da Resposta:**
| Campo           | Tipo   | Descrição                                        |
| --------------- | ------ | ------------------------------------------------ |
| `challenge_id`  | string | Identificador do desafio executado               |
| `tests`         | array  | Resultado individual de cada teste (`ChallengeTestResult`: `name`, `passed`, `stdout`, `expected`, `actual`) |
| `passed_count`  | int    | Quantidade de testes aprovados                   |
| `total_count`   | int    | Quantidade total de testes                       |

**Erros:**
| Status | Descrição                     |
| ------ | ----------------------------- |
| `400`  | Código excede `PYFLOW_MAX_CODE_CHARS` |
| `404`  | `Challenge not found` (challenge_id inexistente) |

> **Como funciona (protocolo do harness):** o código do aluno é concatenado
> com um harness oculto e executado pelo engine isolado. O harness captura
> o stdout do aluno, compara com os `expected` de cada teste e imprime a
> linha `PYFLOW_TEST_RESULT::<json>` — que o servidor usa para montar a
> resposta. Se o código do aluno lançar uma exceção (ou o marcador sair
> malformado), todos os testes são marcados como falhos com a mensagem do
> erro em `actual`. Se `input()` for usado, a execução é bloqueada
> (`status: blocked`).

---

### 8. `GET /auth/token` - Obter Token da API

Retorna o token da API para **clientes de origem local** (UIs). Não exige o
header `X-PyFlow-Token` — apenas origem local (ver
[Autenticação por Token](#-autenticação-por-token)).

**Requisição:**
```http
GET /auth/token
```

**Resposta (200 OK):**
```json
{
  "token": "<token>"
}
```

---

### 9. `GET /models/openrouter` - Listar Modelos do OpenRouter

Lista todos os modelos disponíveis no OpenRouter. Útil para popular dropdowns na UI.

**Requisição:**
```http
GET /models/openrouter
X-OpenRouter-API-Key: sk-or-v1-...
```

**Resposta (200 OK):**
```json
{
  "data": [
    {
      "id": "anthropic/claude-3.5-sonnet",
      "name": "Claude 3.5 Sonnet",
      "description": "...",
      "context_length": 200000,
      "pricing": {
        "prompt": "0.000003",
        "completion": "0.000015"
      }
    },
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4o",
      "description": "...",
      "context_length": 128000,
      "pricing": {
        "prompt": "0.000005",
        "completion": "0.000015"
      }
    }
  ]
}
```

> **Dica para UI:** Use o campo `pricing.prompt` e `pricing.completion` para filtrar modelos gratuitos (valor `0`).

---

## 📦 Modelos de Dados (Schemas)

### `AIConfig`
```json
{
  "provider": "openai | anthropic | google | openrouter | deepseek | ollama | minimax | opencode | opencode-go",
  "model_id": "gpt-4o | claude-3.5-sonnet | gemini-1.5-pro | ...",
  "api_key": "sk-... (opcional)",
  "base_url": "https://... (opcional)"
}
```

### `Diagnostics`
```json
{
  "error_type": "ZeroDivisionError",
  "message": "division by zero",
  "line": 2,
  "context": "x = 1/0\n~^~",
  "raw_traceback": "..."
}
```

### `AIErrorHelp`
```json
{
  "summary": "Resumo do erro em linguagem simples",
  "probable_fix": "Sugestão de como corrigir",
  "suggested_code": "Código corrigido (opcional)"
}
```

### `ChatMessage`
```json
{
  "role": "user | assistant",
  "content": "Conteúdo da mensagem"
}
```

---

## ⚙️ Configuração de Provedores de IA (`ai_config`)

O campo `ai_config` é fundamental para integração com IA. Aqui estão as configurações para cada provedor:

| Provider       | `provider`    | `model_id` (Exemplos)                     | `base_url`                        | Observações                                      |
| -------------- | ------------- | ----------------------------------------- | --------------------------------- | ------------------------------------------------ |
| **OpenAI**     | `openai`      | `gpt-4o`, `gpt-4-turbo`, `gpt-5-nano`     | (não necessário)                  | Para GPT-5, usa API Responses automaticamente    |
| **Anthropic**  | `anthropic`   | `claude-3-opus`, `claude-3-sonnet`        | (não necessário)                  |                                                  |
| **Google**     | `google`      | `gemini-1.5-pro`, `gemini-2.5-flash-lite` | (não necessário)                  | Internamente convertido para `gemini/...`        |
| **DeepSeek**   | `deepseek`    | `deepseek-chat`, `deepseek-coder`         | (não necessário)                  |                                                  |
| **OpenRouter** | `openrouter`  | `openai/gpt-4o`, `anthropic/claude-3`     | (não necessário, usa padrão)      | Use IDs no formato `provider/model`              |
| **Ollama**     | `ollama`      | `llama3`, `codellama`, `mistral`          | `http://localhost:11434/v1`       | Requer servidor Ollama local                     |
| **MiniMax**    | `minimax`     | `MiniMax-M3`, `MiniMax-M2.7`              | (não necessário)                  | Provedor nativo via LiteLLM                       |
| **OpenCode Zen** | `opencode`  | `gpt-5.6-luna`, `deepseek-v4-flash`, `claude-sonnet-4-5`, `minimax-m3` | `https://opencode.ai/zen/v1` | Protocolo (Responses/Messages/Chat) selecionado automaticamente por modelo |
| **OpenCode Go**  | `opencode-go` | `gpt-5.6-luna`, `deepseek-v4-flash`, `claude-sonnet-4-5`, `minimax-m3` | `https://opencode.ai/zen/go/v1` | Protocolo (Responses/Messages/Chat) selecionado automaticamente por modelo |

---

## 🚨 Tratamento de Erros e Status de Resposta

O campo `status` da resposta do `/run` indica o resultado da execução:

### Status `success`
O código foi executado sem erros (exit_code = 0).

```json
{
  "status": "success",
  "stdout": "Resultado aqui",
  "stderr": "",
  "exit_code": 0,
  "diagnostics": null,
  "ai_error_help": null
}
```

### Status `error`
Ocorreu um erro durante a execução (exception, syntax error, etc).

```json
{
  "status": "error",
  "stdout": "...",
  "stderr": "Traceback...\nNameError: name 'x' is not defined",
  "exit_code": 1,
  "diagnostics": {
    "error_type": "NameError",
    "message": "name 'x' is not defined",
    "line": 3,
    "context": "print(x)"
  },
  "ai_error_help": { ... }
}
```

**Tipos de Erro Comuns:**
- `SyntaxError`: Erro de sintaxe no código
- `NameError`: Variável não definida
- `TypeError`: Tipo inválido para operação
- `IndexError`: Índice fora do range
- `ZeroDivisionError`: Divisão por zero
- `CodeTooLarge`: Código excede o limite de caracteres

### Status `blocked`
O código contém `input()` mas nenhum `stdin` foi fornecido.

```json
{
  "status": "blocked",
  "stdout": "",
  "stderr": "Execução bloqueada: seu código usa input(). Envie o campo 'stdin'.",
  "diagnostics": {
    "error_type": "InputRequiresStdin",
    "message": "O código contém input() mas nenhum stdin foi fornecido."
  }
}
```

**Como resolver:** Envie o campo `stdin` na requisição com os valores que serão lidos pelo `input()` (separados por `\n` se houver múltiplos).

### Status `timeout`
O tempo de execução excedeu o limite configurado.

```json
{
  "status": "timeout",
  "stdout": "",
  "stderr": "Tempo limite atingido (30s).",
  "exit_code": null,
  "diagnostics": {
    "error_type": "Timeout",
    "message": "Execução excedeu o tempo limite (30s)."
  }
}
```

---

## 📂 Estrutura do Projeto

```
PyFlow/
├── pyflow/                    # Backend Python
│   ├── __init__.py            # Versão do pacote
│   ├── main.py                # Aplicação FastAPI + CORS
│   ├── cli.py                 # CLI (typer): start, doctor
│   ├── api/                   # Rotas da API
│   │   ├── routes_auth.py     # GET /auth/token
│   │   ├── routes_health.py   # GET /health
│   │   ├── routes_run.py      # POST /run
│   │   ├── routes_stream.py   # POST /run/stream (NDJSON)
│   │   ├── routes_chat.py     # POST /chat
│   │   ├── routes_hint.py     # POST /hint (dica socrática)
│   │   ├── routes_models.py   # GET /models/openrouter
│   │   ├── routes_challenges.py # GET /challenges, POST /challenges/run
│   │   └── deps.py            # Dependências: token + origem local
│   ├── core/                  # Lógica central
│   │   ├── config.py          # Configurações (Pydantic Settings)
│   │   ├── models.py          # Schemas Pydantic
│   │   ├── engine.py          # Motor de execução de código
│   │   ├── runner_tpl.py      # Wrapper de saída rica (matplotlib)
│   │   ├── diagnostics.py     # Parser de traceback
│   │   ├── ai_service.py      # Integração com IA (LiteLLM)
│   │   ├── challenges.py      # Runner de desafios (harness oculto)
│   │   ├── security.py        # Token da API (~/.pyflow/token)
│   │   ├── concurrency.py     # Semáforo de execuções simultâneas
│   │   ├── logging_config.py  # Logs JSON estruturados
│   │   ├── connection.py      # Arquivo de conexão (~/.pyflow)
│   │   └── backends/          # Backends de execução plugáveis
│   │       ├── base.py        # Interface ExecutionBackend
│   │       ├── subprocess_backend.py # Backend subprocess
│   │       ├── docker_backend.py     # Backend docker (sandbox)
│   │       └── _util.py       # Helpers de processo
│   ├── data/                  # Dados embarcados
│   │   └── challenges/        # Definições de desafios (JSON)
│   └── utils/                 # Utilitários
│       ├── ids.py             # Gerador de request_id
│       └── net.py             # Busca de porta disponível
├── ui/                        # Frontend Nuxt.js
│   ├── app.vue                # Componente principal
│   ├── stores/pyflow.js       # Store Pinia
│   ├── nuxt.config.ts         # Configuração Nuxt
│   └── ...
├── tests/                     # Testes
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

---

## 📋 Referência Rápida

| Endpoint               | Método | Descrição                                    |
| ---------------------- | ------ | -------------------------------------------- |
| `/health`              | GET    | Verifica se o servidor está online (público) |
| `/auth/token`          | GET    | Obtém o token da API (origem local)          |
| `/run`                 | POST   | Executa código Python                        |
| `/run/stream`          | POST   | Executa com streaming NDJSON em tempo real   |
| `/chat`                | POST   | Chat contextual com IA                       |
| `/hint`                | POST   | Dica socrática progressiva (níveis 1-3)      |
| `/challenges`          | GET    | Lista desafios disponíveis                   |
| `/challenges/run`      | POST   | Executa código contra os testes ocultos      |
| `/models/openrouter`   | GET    | Lista modelos do OpenRouter                  |

> **Nota:** todos os endpoints exigem o header `X-PyFlow-Token` e origem
> local, exceto `/health` (público) e `/auth/token` (apenas origem local).

**Exemplos de Código (cURL):**

```bash
TOKEN=$(cat ~/.pyflow/token)

# Health Check (público)
curl http://localhost:8000/health

# Executar Código
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-PyFlow-Token: $TOKEN" \
  -d '{"code": "print(1+1)", "ai_explain_on_error": false}'

# Executar com Streaming (NDJSON)
curl -N -X POST http://localhost:8000/run/stream \
  -H "Content-Type: application/json" \
  -H "X-PyFlow-Token: $TOKEN" \
  -d '{"code": "for i in range(5): print(i)"}'

# Dica Socrática (nível 2)
curl -X POST http://localhost:8000/hint \
  -H "Content-Type: application/json" \
  -H "X-PyFlow-Token: $TOKEN" \
  -d '{
    "code": "x = 10\nprint(y)",
    "level": 2,
    "ai_config": {"provider": "openai", "model_id": "gpt-4o", "api_key": "sk-..."}
  }'

# Listar Desafios
curl http://localhost:8000/challenges -H "X-PyFlow-Token: $TOKEN"

# Executar Desafio
curl -X POST http://localhost:8000/challenges/run \
  -H "Content-Type: application/json" \
  -H "X-PyFlow-Token: $TOKEN" \
  -d '{"challenge_id": "hello_world", "code": "print(\"Olá, PyFlow!\")"}'

# Chat com IA
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-PyFlow-Token: $TOKEN" \
  -d '{
    "user_message": "O que é Python?",
    "ai_config": {"provider": "openai", "model_id": "gpt-4o", "api_key": "sk-..."}
  }'
```

---

## 🛠️ Built with

- **[FastAPI](https://fastapi.tiangolo.com)** + **[Uvicorn](https://www.uvicorn.org)** — API assíncrona
- **[LiteLLM](https://github.com/BerriAI/litellm)** — abstração multi-provedor de IA
- **[Nuxt 3](https://nuxt.com)** + **[Vue 3](https://vuejs.org)** + **[Pinia](https://pinia.vuejs.org)** — interface web
- **[CodeMirror 6](https://codemirror.net)** — editor de código
- **[Pyodide](https://pyodide.org)** — execução Python no navegador (WebAssembly)
- **[Docker](https://www.docker.com)** — sandbox de execução e deploy
- **[Typer](https://typer.tiangolo.com)** — CLI
- **[pytest](https://pytest.org)** — testes

## 🙏 Agradecimentos

- [FastAPI](https://fastapi.tiangolo.com) — o framework que torna a API simples e robusta
- [LiteLLM](https://github.com/BerriAI/litellm) — um único SDK para dezenas de provedores de IA
- [Nuxt](https://nuxt.com) / [Vue](https://vuejs.org) — a UI
- [CodeMirror](https://codemirror.net) — o editor
- [Pyodide](https://pyodide.org) — Python no navegador
- [Judge0](https://github.com/judge0/judge0) — inspiração para a arquitetura de sandbox dos desafios
- [OpenCode](https://github.com/anomalyco/opencode) — a ferramenta de IA usada para construir, testar e manter este projeto

## 🔗 Links

- **Código-fonte:** [github.com/alexlivre/PyFlow](https://github.com/alexlivre/PyFlow)
- **Releases:** [GitHub Releases](https://github.com/alexlivre/PyFlow/releases)
- **Issue tracker:** [GitHub Issues](https://github.com/alexlivre/PyFlow/issues)
- **Licença:** [MIT](./LICENSE)

---

## 📝 Licença

[MIT](./LICENSE) © 2026 [Alex Santos](https://alexlivre.dev/) ([@alexlivre](https://github.com/alexlivre))

---

<p align="center">
  Made with care for the Python learning community.
</p>
