"""
Módulo principal do PyFlow.

Este módulo inicializa a aplicação FastAPI, registra os routers das rotas
da API e configura a limpeza de recursos ao encerrar.

A aplicação pode ser executada diretamente com 'python -m pyflow.main'
ou através do CLI com 'pyflow start'.

Rotas incluídas:
    - /health: Verificação de saúde do serviço
    - /run: Execução de código Python
    - /chat: Chat com IA contextual

Exemplo de uso:
    >>> import uvicorn
    >>> uvicorn.run("pyflow.main:app", host="127.0.0.1", port=8000)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pyflow.api import routes_auth, routes_run, routes_chat, routes_health, routes_models
from pyflow import __version__
from pyflow.core.connection import register_cleanup

app = FastAPI(
    title="PyFlow API",
    version=__version__,
    description="API local para execução de código Python e assistência IA."
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Register routes
app.include_router(routes_auth.router)
app.include_router(routes_health.router)
app.include_router(routes_run.router)
app.include_router(routes_chat.router)
app.include_router(routes_models.router)

# Register cleanup on exit (normal python exit)
# Note: Uvicorn handles signals, but atexit covers many cases.
register_cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
