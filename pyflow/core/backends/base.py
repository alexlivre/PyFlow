"""
Abstração de backend de execução de código.

Define o contrato mínimo entre o motor (orquestração) e os mecanismos
de execução (subprocesso local ou sandbox Docker).
"""

from dataclasses import dataclass
from typing import Callable, Optional
from abc import ABC, abstractmethod


@dataclass
class RawExecution:
    """Saída bruta de uma execução, sem qualquer pós-processamento.

    Attributes:
        stdout: Saída capturada de stdout (truncada se `output_truncated`).
        stderr: Saída capturada de stderr (truncada se `output_truncated`).
        exit_code: Código de saída do processo, ou None se foi morto.
        timed_out: True se o processo estourou o timeout e foi morto.
        output_truncated: True se a saída excedeu o limite e foi truncada.

    Streams truncadas carregam o sufixo "\n(truncado)" na stream afetada.
    """
    stdout: str
    stderr: str
    exit_code: Optional[int]
    timed_out: bool
    output_truncated: bool = False


class ExecutionBackend(ABC):
    """Executa código Python isolado e devolve a saída bruta.

    O motor (pyflow.core.engine) é o orquestrador: ele faz validação,
    parsing de diagnóstico, sanitização de caminhos, extração de imagens
    e construção do RunResponse. O backend apenas roda o código e captura
    stdout/stderr com limites de timeout e tamanho de saída.
    """

    @abstractmethod
    async def run(
        self,
        code: str,
        stdin: Optional[str],
        timeout_seconds: int,
        max_output_chars: int,
        cwd: str,
        on_output: Optional[Callable[[str, str], None]] = None,
    ) -> RawExecution:
        """Executa `code` e retorna a saída bruta.

        Args:
            code: Código Python a executar.
            stdin: Entrada padrão para o código (None se não houver).
            timeout_seconds: Tempo máximo em segundos; estourado, o
                processo é morto e `timed_out` é marcado.
            max_output_chars: Limite de caracteres por stream; excedido,
                a stream é truncada e `output_truncated` é marcado.
            cwd: Diretório de trabalho do processo.
            on_output: Callback síncrono chamado com (stream, chunk) para
                cada chunk lido, antes da checagem de limite.

        Returns:
            RawExecution com stdout/stderr já limitados.
        """
