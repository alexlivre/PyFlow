# 📘 PyFlow API - Guia Completo e Definitivo

<p align="center">
  <strong>Versão 2.0.0</strong>
</p>

**PyFlow** é uma API local robusta construída em **FastAPI** para execução segura de código Python em subprocessos isolados, com captura de saída, diagnósticos de erros estruturados e integração com múltiplos provedores de Inteligência Artificial (OpenAI, Gemini, Anthropic, OpenRouter, DeepSeek, Ollama) para explicação de erros e chat contextual.

Este documento é o **guia definitivo** para desenvolvedores que desejam consumir a API do PyFlow, criar suas próprias interfaces gráficas (UIs), ou simplesmente entender todas as suas funcionalidades em detalhes.

---

## 📑 Índice

1.  [🐳 Início Rápido com Docker (Recomendado)](#-início-rápido-com-docker-recomendado)
2.  [Visão Geral](#-visão-geral)
3.  [Instalação e Configuração](#-instalação-e-configuração)
    *   [Instalando Dependências](#1-instalando-dependências)
    *   [Variáveis de Ambiente](#2-variáveis-de-ambiente-opcional)
4.  [Iniciando o Servidor da API](#-iniciando-o-servidor-da-api)
    *   [Via Módulo Python](#via-módulo-python-simples)
    *   [Via CLI (Typer)](#via-cli-typer)
    *   [Comando `doctor`](#comando-doctor-para-diagnóstico)
5.  [Rodando a Interface Gráfica (UI)](#-rodando-a-interface-gráfica-ui)
6.  [Documentação Completa dos Endpoints](#-documentação-completa-dos-endpoints)
    *   [`GET /health`](#1-get-health---verificar-saúde-do-serviço)
    *   [`POST /run`](#2-post-run---executar-código-python)
    *   [`POST /chat`](#3-post-chat---chat-contextual-com-ia)
    *   [`GET /models/openrouter`](#4-get-modelsopenrouter---listar-modelos-do-openrouter)
7.  [Modelos de Dados (Schemas)](#-modelos-de-dados-schemas)
8.  [Configuração de Provedores de IA (`ai_config`)](#-configuração-de-provedores-de-ia-ai_config)
9.  [Tratamento de Erros e Status de Resposta](#-tratamento-de-erros-e-status-de-resposta)
    *   [Status `success`](#status-success)
    *   [Status `error`](#status-error)
    *   [Status `blocked`](#status-blocked)
    *   [Status `timeout`](#status-timeout)
10. [Estrutura do Projeto](#-estrutura-do-projeto)
11. [Referência Rápida](#-referência-rápida)

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
*   **Explicação de Erros por IA:** Quando um erro ocorre, a IA pode gerar uma explicação e código corrigido.
*   **Chat Contextual:** Converse com a IA sobre o código no editor.
*   **Multi-Provedor de IA:** Suporte a OpenAI, Gemini, Anthropic, DeepSeek, OpenRouter (400+ modelos) e Ollama (local).

---

## 🛠️ Instalação e Configuração

### 1. Instalando Dependências

Certifique-se de ter **Python 3.11+** instalado. No diretório raiz do projeto:

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
| `PYFLOW_AI_MAX_TOKENS`           | Máximo de tokens para respostas da IA                  | `800`         |
| `PYFLOW_AI_TEMPERATURE`          | Temperatura para geração da IA                         | `1.0`         |
| `OPENAI_API_KEY`                 | Chave de API da OpenAI (fallback)                      | `null`        |
| `GEMINI_API_KEY`                 | Chave de API do Google Gemini (fallback)               | `null`        |
| `ANTHROPIC_API_KEY`              | Chave de API da Anthropic (fallback)                   | `null`        |
| `DEEPSEEK_API_KEY`               | Chave de API do DeepSeek (fallback)                    | `null`        |
| `OPENROUTER_API_KEY`             | Chave de API do OpenRouter (fallback)                  | `null`        |

> **Nota:** As chaves de API também podem ser passadas diretamente no corpo da requisição via `ai_config.api_key`.

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
2.  Cria um arquivo `~/.pyflow/connection.json` para que clientes descubram a porta.

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

Executa código Python em um subprocesso isolado e retorna o resultado.

**Requisição:**
```http
POST /run
Content-Type: application/json
```

**Corpo da Requisição (Todos os Campos):**
```json
{
  "code": "print('Olá')\nx = 1/0",
  "stdin": null,
  "timeout_seconds": 30,
  "max_output_chars": 100000,
  "include_raw_traceback": false,
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
| `ai_error_help`    | object \| null | Explicação da IA sobre o erro (ver abaixo)                                       |
| `request_id`       | string         | Identificador único da requisição                                                |

---

### 3. `POST /chat` - Chat Contextual com IA

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

### 4. `GET /models/openrouter` - Listar Modelos do OpenRouter

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
  "provider": "openai | anthropic | google | openrouter | deepseek | ollama",
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
│   │   ├── routes_health.py   # GET /health
│   │   ├── routes_run.py      # POST /run
│   │   ├── routes_chat.py     # POST /chat
│   │   └── routes_models.py   # GET /models/openrouter
│   ├── core/                  # Lógica central
│   │   ├── config.py          # Configurações (Pydantic Settings)
│   │   ├── models.py          # Schemas Pydantic
│   │   ├── engine.py          # Motor de execução de código
│   │   ├── diagnostics.py     # Parser de traceback
│   │   ├── ai_service.py      # Integração com IA (LiteLLM)
│   │   └── connection.py      # Arquivo de conexão (~/.pyflow)
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

| Endpoint               | Método | Descrição                           |
| ---------------------- | ------ | ----------------------------------- |
| `/health`              | GET    | Verifica se o servidor está online  |
| `/run`                 | POST   | Executa código Python               |
| `/chat`                | POST   | Chat contextual com IA              |
| `/models/openrouter`   | GET    | Lista modelos do OpenRouter         |

**Exemplos de Código (cURL):**

```bash
# Health Check
curl http://localhost:8000/health

# Executar Código
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"code": "print(1+1)", "ai_explain_on_error": false}'

# Chat com IA
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "O que é Python?",
    "ai_config": {"provider": "openai", "model_id": "gpt-4o", "api_key": "sk-..."}
  }'
```

---

## 📝 Licença

Este projeto é de uso interno e educacional.

---

**Desenvolvido com ❤️ para tornar a programação mais acessível.**
