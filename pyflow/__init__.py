"""
PyFlow - API local para execução de código Python e assistência IA.

Este pacote fornece uma API FastAPI para execução segura de código Python
em subprocessos, com captura de saída, diagnósticos de erros estruturados
e integração com modelos de IA para explicação de erros e chat contextual.

Módulos principais:
    - core: Lógica central (engine, diagnostics, ai_service, config, models)
    - api: Rotas da API FastAPI (run, chat, health)
    - utils: Utilitários auxiliares (net, ids)
    - cli: Interface de linha de comando

Versão:
    A versão atual está definida em __version__.
"""

__version__ = "2.1.0"
