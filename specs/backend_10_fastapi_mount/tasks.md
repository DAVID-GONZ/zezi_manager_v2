# Tareas: backend_10_fastapi_mount

> SCOPE — archivos que pueden editarse:
> `src/api/` (crear, hermano de `src/interface/`), `main.py`, `config.py`,
> `.env.example`, `requirements.txt`.
>
> Fuera de scope: servicios, repositorios, modelos de dominio, paginas NiceGUI.
> Si una tarea exige tocar algo de ahi -> PARAR y reportar al leader.

---

## T1 — Crear estructura src/api/

Crear el arbol de directorios y archivos vacios:
- `src/api/__init__.py`
- `src/api/router.py`
- `src/api/deps.py`
- `src/api/errors.py`
- `src/api/schemas/__init__.py`
- `src/api/schemas/common.py`

**Verificacion:** `python -c "from src.api import router"` no falla.

---

## T2 — Schemas comunes de response

En `schemas/common.py`, definir:
- `HealthResponse(status: str, version: str)`
- `ErrorResponse(detail: str, code: str)`
- `PaginatedResponse(items: list, total: int, page: int, per_page: int)` (generico)

**Verificacion:** `python -c "from src.api.schemas.common import HealthResponse; print(HealthResponse.model_json_schema())"`.

---

## T3 — Router raiz con /api/v1/health

En `router.py`, crear `api_router = APIRouter(prefix="/api/v1")` con
el endpoint `GET /health` segun D2.

En `deps.py`, crear funciones `get_engine()` y `get_auth_service()` segun D3.

**Verificacion:** importar el router sin errores.

---

## T4 — Registrar el router en main.py

En `registrar_rutas_internas(app)`, anadir:
```python
from src.api.router import api_router
app.include_router(api_router)
```

**Verificacion:** arrancar la app, `curl http://localhost:8080/api/v1/health`
retorna `{"status": "ok", "version": "2.0.0"}`.

---

## T5 — Exception handlers para AvedraError

Implementar `errors.py` segun D4. Registrar el handler en
`registrar_rutas_internas()`.

**Verificacion:** un endpoint de test que lance `NoEncontradoError` retorna 404
con `{"detail": "...", "code": "..."}`.

---

## T6 — Configurar CORS

Anadir `CORS_ORIGINS` a `config.py` y `.env.example`. Aplicar el middleware
CORS en `registrar_rutas_internas()` segun D5.

**Verificacion:** request con `Origin: http://localhost:5173` recibe
`Access-Control-Allow-Origin`.

---

## T7 — Habilitar OpenAPI docs

Configurar `docs_url`, `redoc_url` y `openapi_url` para que el spec
se sirva bajo `/api/`. Si NiceGUI los bloquea, servir el JSON desde
un endpoint del router y Swagger UI como pagina estatica.

**Verificacion:** `http://localhost:8080/api/docs` muestra Swagger UI con
el endpoint /health.

---

## T8 — Verificacion de no regresion y cierre

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. La app NiceGUI funciona identica. `/api/v1/health` responde.

**Artefacto:** `progress/impl_backend_10.md`.
