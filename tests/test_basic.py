"""
Testes básicos do PyFlow.

Este módulo contém testes unitários para funções críticas do PyFlow,
focando no módulo de diagnósticos.

Testes incluídos:
    - test_sanitize_path: Verifica sanitização de caminhos
    - test_parse_simple_error: Verifica parsing de NameError
    - test_parse_syntax_error: Verifica parsing de SyntaxError

Para executar os testes:
    pytest tests/test_basic.py
"""

import pytest
from pyflow.core.diagnostics import parse_traceback_str, sanitize_path
from pyflow.core.models import Diagnostics


def test_sanitize_path():
    """
    Testa a sanitização de caminhos de arquivos temporários.

    Verifica que caminhos contendo 'pyflow_tmp_' são substituídos
    por '<user_code>', enquanto outros caminhos são mantidos.
    """
    assert sanitize_path("/tmp/pyflow_tmp_123.py") == "<user_code>"
    assert sanitize_path("/home/user/code.py") == "/home/user/code.py"


def test_parse_simple_error():
    """
    Testa o parsing de um NameError simples.

    Verifica que o parser extrai corretamente o tipo de erro,
    mensagem e número da linha de um traceback de NameError.
    """
    stderr = """
Traceback (most recent call last):
  File "pyflow_tmp_123.py", line 1, in <module>
    print(x)
NameError: name 'x' is not defined
"""
    d = parse_traceback_str(stderr, "pyflow_tmp_123.py")
    assert d.error_type == "NameError"
    assert d.message == "name 'x' is not defined"
    assert d.line == 1


def test_parse_syntax_error():
    """
    Testa o parsing de um SyntaxError.

    Verifica que o parser extrai corretamente o tipo de erro,
    mensagem, número da linha e contexto (incluindo caret)
    de um traceback de SyntaxError.
    """
    stderr = """
  File "pyflow_tmp_99.py", line 1
    if True
          ^
SyntaxError: expected ':'
"""
    d = parse_traceback_str(stderr, "pyflow_tmp_99.py")
    assert d.error_type == "SyntaxError"
    assert d.message == "expected ':'"
    assert d.line == 1
    # Check context contains the caret
    assert d.context is not None
    assert "^" in d.context


# Integration tests would require the server to be running or mocking execution
