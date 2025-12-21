"""
Funções de diagnóstico e parsing de erros do PyFlow.

Este módulo fornece funções para analisar tracebacks do Python,
extrair informações estruturadas de erros e criar diagnósticos
para diferentes situações de erro.

O parsing de traceback identifica:
    - Tipo do erro (NameError, SyntaxError, etc)
    - Mensagem de erro
    - Número da linha no código do usuário
    - Contexto (snippet de código e caret)

Funções principais:
    - parse_traceback_str: Analisa string de traceback
    - sanitize_path: Remove informações sensíveis de caminhos
    - create_*_diagnostics: Cria diagnósticos para situações específicas
"""

import re
from typing import Optional
from pyflow.core.models import Diagnostics

# Regex para extrair tipo e mensagem de erro (última linha do traceback)
ERROR_REGEX = re.compile(r"^(\w+): (.+)$")

# Regex para extrair arquivo, linha e função do traceback
FILE_LINE_REGEX = re.compile(r'\s*File "([^"]+)", line (\d+)(?:, in (.+))?')


def sanitize_path(path: str, user_filename: str = "<user_code>") -> str:
    """
    Substitui o nome do arquivo temporário por um nome genérico.

    Remove informações de caminho que podem expor detalhes do sistema
    ou estrutura de diretórios do servidor.

    Args:
        path: Caminho ou string contendo caminhos para sanitizar.
        user_filename: Nome genérico para substituir (padrão: '<user_code>').

    Returns:
        String com caminhos sanitizados.

    Example:
        >>> sanitize_path("/tmp/pyflow_tmp_abc123.py")
        '<user_code>'
    """
    if user_filename in path or "pyflow_tmp_" in path:
        return "<user_code>"
    # Simple heuristic to shorten venv/system paths could go here,
    # but strictly replacing the temp file is the main requirement.
    return path


def parse_traceback_str(stderr: str, user_filename: str) -> Diagnostics:
    """
    Analisa uma string de traceback e extrai informações estruturadas.

    Processa o stderr capturado de uma execução de código para extrair
    tipo de erro, mensagem, número da linha e contexto.

    Args:
        stderr: String contendo o traceback completo.
        user_filename: Nome do arquivo temporário para buscar no traceback.

    Returns:
        Diagnostics: Objeto com informações estruturadas do erro.

    Note:
        O parsing procura de baixo para cima no traceback para encontrar
        a última referência ao arquivo do usuário, que geralmente é
        a posição real do erro.
    """
    lines = stderr.strip().splitlines()
    if not lines:
        return Diagnostics(error_type="UnknownError", message="No stderr output")

    # Last line is usually "ErrorType: message"
    last_line = lines[-1]
    error_match = ERROR_REGEX.match(last_line)

    error_type = "Error"
    message = last_line

    if error_match:
        error_type = error_match.group(1)
        message = error_match.group(2)

    # Traceback parsing to find line number in user code
    # We look efficiently from bottom up for the user's file
    line_num = None
    context = None

    # We attempt to find the last reference to 'user_filename'
    found_frame_idx = -1

    for i in range(len(lines) - 2, -1, -1):
        m = FILE_LINE_REGEX.match(lines[i])
        if m:
            filename = m.group(1)
            if user_filename in filename:
                line_num = int(m.group(2))
                found_frame_idx = i
                break

    # Extract context if present (sometimes traceback shows the line and a caret)
    # Usually Python tracebacks show:
    #   File "...", line X, in ...
    #     code_snippet
    #   ^^^^
    if found_frame_idx != -1:
        # Check lines after the "File" line
        # Typically:
        # lines[found_frame_idx] -> "File ..."
        # lines[found_frame_idx+1] -> code content
        # lines[found_frame_idx+2] -> possible caret (in 3.11+) or invalid syntax caret

        ctx_lines = []
        if found_frame_idx + 1 < len(lines):
            line_content = lines[found_frame_idx + 1].strip()
            # Avoid including another "File ..." line as context if we are at edge
            if not FILE_LINE_REGEX.match(lines[found_frame_idx + 1]):
                ctx_lines.append(line_content)

                if found_frame_idx + 2 < len(lines):
                    caret_line = lines[found_frame_idx + 2]
                    # Check if it looks like a caret line (contains ^ or ~)
                    if set(caret_line.strip()).issubset({'^', '~', ' '}):
                        ctx_lines.append(caret_line)

        if ctx_lines:
            context = "\n".join(ctx_lines)

    # Sanitize traceback if requested (we allow caller to handle strictly raw,
    # but here we populate parts).
    # The requirement says "raw_traceback" is optional.

    return Diagnostics(
        error_type=error_type,
        message=message,
        line=line_num,
        context=context,
        raw_traceback=None  # Filled by caller if needed
    )


def create_blocked_diagnostics(reason: str, error_type: str = "InputRequiresStdin") -> Diagnostics:
    """
    Cria diagnóstico para execução bloqueada.

    Utilizado quando o código requer input() mas stdin não foi fornecido.

    Args:
        reason: Descrição do motivo do bloqueio.
        error_type: Tipo do erro (padrão: 'InputRequiresStdin').

    Returns:
        Diagnostics: Objeto de diagnóstico para execução bloqueada.
    """
    return Diagnostics(
        error_type=error_type,
        message=reason,
        line=None,
        context=None
    )


def create_timeout_diagnostics(limit_seconds: int) -> Diagnostics:
    """
    Cria diagnóstico para timeout de execução.

    Utilizado quando a execução excede o tempo limite configurado.

    Args:
        limit_seconds: Limite de tempo que foi excedido.

    Returns:
        Diagnostics: Objeto de diagnóstico para timeout.
    """
    return Diagnostics(
        error_type="Timeout",
        message=f"Execução excedeu o tempo limite ({limit_seconds}s).",
        line=None,
        context=None
    )


def create_output_limit_diagnostics() -> Diagnostics:
    """
    Cria diagnóstico para limite de saída excedido.

    Utilizado quando a saída do programa excede o limite configurado
    e o processo foi encerrado prematuramente.

    Returns:
        Diagnostics: Objeto de diagnóstico para limite de saída.
    """
    return Diagnostics(
        error_type="OutputLimitExceeded",
        message="A saída excedeu o limite configurado e o processo foi encerrado.",
        line=None,
        context=None
    )
