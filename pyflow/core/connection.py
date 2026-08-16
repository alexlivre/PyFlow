"""
Gerenciamento de arquivo de conexão do PyFlow.

Este módulo gerencia o arquivo de conexão que armazena informações
sobre o servidor PyFlow em execução. Isso permite que outros processos
(como a UI) descubram automaticamente a URL do servidor.

O arquivo de conexão é armazenado em ~/.pyflow/connection.json e contém:
    - host: Endereço do host do servidor
    - port: Porta do servidor
    - url: URL completa do servidor
    - pid: PID do processo do servidor
    - version: Versão do PyFlow
    - status: Status atual ("online")

Funções:
    write_connection_file: Escreve o arquivo de conexão
    remove_connection_file: Remove o arquivo de conexão
    register_cleanup: Registra limpeza automática ao encerrar
"""

import json
import os
import atexit
from loguru import logger
from pyflow import __version__
from pyflow.core.config import CONNECTION_DIR, CONNECTION_FILE
from pyflow.core.security import get_or_create_token


def _ensure_dir():
    """
    Garante que o diretório de conexão existe.

    Cria o diretório ~/.pyflow se não existir, incluindo
    quaisquer diretórios pais necessários.
    """
    CONNECTION_DIR.mkdir(parents=True, exist_ok=True)

def write_connection_file(host: str, port: int, pid: int):
    """
    Escreve o arquivo de conexão com informações do servidor.

    Cria ou sobrescreve o arquivo ~/.pyflow/connection.json com
    informações sobre o servidor em execução.

    Args:
        host: Endereço do host do servidor.
        port: Porta do servidor.
        pid: ID do processo do servidor.

    Note:
        Em caso de falha na escrita, apenas loga o erro sem
        propagar a exceção.
    """
    _ensure_dir()
    data = {
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}",
        "pid": pid,
        "version": __version__,
        "status": "online",
        "token": get_or_create_token(),
    }
    try:
        with open(CONNECTION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Connection file written to {CONNECTION_FILE}")
    except Exception as e:
        logger.error(f"Failed to write connection file: {e}")


def remove_connection_file():
    """
    Remove o arquivo de conexão.

    Remove o arquivo ~/.pyflow/connection.json se existir.
    Utilizado para limpeza quando o servidor é encerrado.

    Note:
        Em caso de falha na remoção, apenas loga o erro sem
        propagar a exceção.
    """
    try:
        if CONNECTION_FILE.exists():
            CONNECTION_FILE.unlink()
            logger.info(f"Connection file removed: {CONNECTION_FILE}")
    except Exception as e:
        logger.error(f"Failed to remove connection file: {e}")


def register_cleanup():
    """
    Registra a limpeza automática do arquivo de conexão.

    Registra a função remove_connection_file para ser chamada
    automaticamente quando o processo Python for encerrado
    normalmente (via atexit).

    Note:
        Uvicorn gerencia sinais separadamente, mas atexit
        cobre a maioria dos casos de encerramento normal.
    """
    atexit.register(remove_connection_file)
