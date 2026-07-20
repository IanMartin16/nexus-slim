"""
main.py — ensamblado de la app.

Stateless: el lifespan solo maneja el cliente HTTP de salida (hacia el gateway)
y el cliente del cerebro. No hay BD, no hay pool a Postgres, nada que migrar
entre réplicas. Eso es lo que habilita el escalado horizontal bajo carga.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.health import router as health_router

from .clients.mcpone import MCPOneClient
from .config import settings
from .routers import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    http = httpx.AsyncClient()
    app.state.http = http
    app.state.brain = MCPOneClient(http, settings)
    try:
        yield
    finally:
        await http.aclose()


app = FastAPI(title=settings.service_name, version=settings.version, lifespan=lifespan,)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, tags=["chat"])
app.include_router(health_router)
