"""
Interface de linha de comando (CLI) do PyFlow.

Este módulo fornece comandos para gerenciar o servidor PyFlow através
do terminal usando Typer.

Comandos disponíveis:
    - start: Inicia o servidor PyFlow em uma porta disponível
    - doctor: Verifica o ambiente e dependências

Uso:
    $ pyflow start --host 127.0.0.1 --port 8000
    $ pyflow doctor

As configurações podem ser passadas via argumentos de linha de comando
ou variáveis de ambiente (PYFLOW_HOST, PYFLOW_DEFAULT_PORT).
"""

import typer
import sys
import uvicorn
import os
from pathlib import Path
from loguru import logger

from pyflow.core.config import settings
from pyflow.utils.net import find_available_port
from pyflow.core.connection import write_connection_file, CONNECTION_DIR

app = typer.Typer()

@app.command()
def start(
    host: str = typer.Option(settings.PYFLOW_HOST, envvar="PYFLOW_HOST"),
    port: int = typer.Option(settings.PYFLOW_DEFAULT_PORT, envvar="PYFLOW_DEFAULT_PORT"),
):
    """
    Inicia o servidor PyFlow.

    Busca uma porta disponível a partir da porta especificada e inicia
    o servidor Uvicorn. Também cria um arquivo de conexão em ~/.pyflow/
    para que outros processos possam descobrir o servidor.

    Args:
        host: Endereço do host para bind do servidor (padrão: 127.0.0.1).
        port: Porta inicial para busca (padrão: 8000).

    Raises:
        typer.Exit: Se não for possível encontrar uma porta disponível.
    """
    try:
        final_port = find_available_port(host, port, settings.PYFLOW_PORT_SEARCH_MAX_TRIES)
    except RuntimeError as e:
        logger.error(str(e))
        raise typer.Exit(code=1)

    logger.info(f"Starting PyFlow on http://{host}:{final_port}")
    
    # Write connection info
    write_connection_file(host, final_port, os.getpid())
    
    # Start Uvicorn
    # log_level="warning" to keep it clean, or "info"
    uvicorn.run("pyflow.main:app", host=host, port=final_port, log_level="info")

@app.command()
def doctor():
    """
    Verifica o ambiente e dependências do PyFlow.

    Executa uma série de verificações para garantir que o ambiente
    está configurado corretamente:

    1. Versão do Python instalada
    2. Permissões de escrita no diretório ~/.pyflow
    3. Presença de todas as dependências obrigatórias

    Este comando é útil para diagnóstico de problemas de instalação
    ou configuração do ambiente.

    Returns:
        None: Imprime os resultados das verificações no terminal.
    """
    typer.echo("\n🏥 PyFlow Doctor 🏥\n")
    
    # 1. Python Version
    py_ver = sys.version.split()[0]
    typer.echo(f"✅ Python Version: {py_ver}")
    
    # 2. Permissions (~/.pyflow)
    try:
        if not CONNECTION_DIR.exists():
            CONNECTION_DIR.mkdir(parents=True)
        test_file = CONNECTION_DIR / "test_write"
        test_file.touch()
        test_file.unlink()
        typer.echo(f"✅ Write Access to {CONNECTION_DIR}")
    except Exception as e:
        typer.echo(f"❌ Write Access Failed: {e}")
        
    # 3. Dependencies
    deps = ["fastapi", "uvicorn", "litellm", "psutil", "pydantic"]
    for dep in deps:
        try:
            __import__(dep)
            typer.echo(f"✅ Dependency '{dep}' installed")
        except ImportError:
            typer.echo(f"❌ Dependency '{dep}' MISSING")
            
    typer.echo("\nAll checks completed.")

if __name__ == "__main__":
    app()
