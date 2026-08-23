"""Tests del endpoint interno `/health`.

Cubre `main.registrar_rutas_internas` (antes sin ningún test) y estrena la
categoría de test **async** del proyecto: `pytest-asyncio` estaba instalado pero
no se usaba. Con `asyncio_mode = "auto"` en pyproject, un `async def test_...`
se ejecuta sin decorador. Golpeamos la ruta a través de la pila ASGI real
(httpx + ASGITransport) sobre una FastAPI limpia, sin levantar el servidor
NiceGUI completo.
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from config import settings
from main import registrar_rutas_internas


def _app_con_health() -> FastAPI:
    app = FastAPI()
    registrar_rutas_internas(app)
    return app


async def test_health_responde_ok():
    app = _app_con_health()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["version"] == settings.APP_VERSION


async def test_health_ruta_desconocida_da_404():
    app = _app_con_health()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/no-existe")

    assert resp.status_code == 404
