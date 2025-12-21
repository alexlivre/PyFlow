"""
Gerador de IDs de requisição do PyFlow.

Este módulo fornece funções para gerar identificadores únicos
para requisições da API, facilitando rastreamento e debug.

O formato do ID é: req_<16 caracteres hexadecimais>
Exemplo: req_a1b2c3d4e5f67890
"""

import uuid


def generate_request_id() -> str:
    """
    Gera um ID único para uma requisição.

    Utiliza UUID4 para garantir unicidade e retorna
    um ID formatado com prefixo 'req_'.

    Returns:
        str: ID formatado (ex: 'req_a1b2c3d4e5f67890').

    Example:
        >>> request_id = generate_request_id()
        >>> print(request_id)
        'req_a1b2c3d4e5f67890'
    """
    return f"req_{uuid.uuid4().hex[:16]}"
