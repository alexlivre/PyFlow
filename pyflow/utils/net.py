"""
Utilitários de rede do PyFlow.

Este módulo fornece funções auxiliares para operações de rede,
principalmente para verificação e busca de portas disponíveis.

Funções:
    is_port_in_use: Verifica se uma porta está em uso
    find_available_port: Encontra uma porta livre para o servidor
"""

import socket
from pyflow.core.config import settings
from loguru import logger


def is_port_in_use(host: str, port: int) -> bool:
    """
    Verifica se uma porta está em uso.

    Tenta conectar na porta especificada para verificar
    se há algum serviço escutando.

    Args:
        host: Endereço do host.
        port: Número da porta a verificar.

    Returns:
        bool: True se a porta está em uso, False caso contrário.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def find_available_port(host: str, start_port: int, max_tries: int = 50) -> int:
    """
    Encontra uma porta disponível para uso.

    Itera a partir da porta inicial, tentando fazer bind em cada porta
    até encontrar uma disponível ou esgotar as tentativas.

    Args:
        host: Endereço do host para bind.
        start_port: Porta inicial para busca.
        max_tries: Máximo de tentativas (padrão: 50).

    Returns:
        int: Número da porta disponível encontrada.

    Raises:
        RuntimeError: Se não encontrar porta disponível dentro do limite.

    Note:
        Utiliza bind em vez de connect para verificação mais robusta,
        pois bind verifica se podemos usar a porta, não apenas se
        há algo escutando.
    """
    for port in range(start_port, start_port + max_tries):
        # Para ser mais robusto, tentamos bind, em vez de connect
        # Connect vê se tem algo escutando. Bind vê se podemos usar.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Could not find an available port starting from {start_port} (tries: {max_tries})")
