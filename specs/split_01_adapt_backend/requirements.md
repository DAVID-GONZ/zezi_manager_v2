# split_01_adapt_backend — Requisitos

## Contexto

Fase 2.3-2.6 del repo split. Tras ejecutar `git filter-repo` (paso manual 2.2),
el repo `avedra-backend` tiene todo el codigo pero aun referencia NiceGUI en
pyproject.toml, init.py y container.py. Este paso lo limpia y agrega el stub
de FastAPI.

**Repo destino:** `avedra-backend` (NO el mono-repo actual).

## Requisitos (EARS)

**R1** — Existe un directorio `app/` con la estructura minima de FastAPI:
`app/__init__.py`, `app/main.py` (factory), `app/deps.py` (DI),
`app/routes/__init__.py`.

**R2** — `app/main.py` crea una instancia de FastAPI, importa rutas y expone
Container via `app/deps.py`. No implementa endpoints reales (eso va en el
backend roadmap).

**R3** — `pyproject.toml` no contiene dependencias de NiceGUI: `nicegui`,
`nicegui[*]`, paquetes de Quasar o ag-Grid.

**R4** — `pyproject.toml` incluye `fastapi` y `uvicorn` como dependencias.

**R5** — `scripts/init.py` no ejecuta chequeos de design system:
`check_design.py`, `audit_design.py`, `sync_tokens.py`. Conserva: ruff
(defectos de ejecucion), tests, verificacion de imports.

**R6** — `container.py` no registra componentes de `src/interface/`.
Mantiene: repos, servicios, config.

**R7** — `grep -rn "src.interface\|src/interface\|from interface" src/ tests/`
retorna 0 resultados.

## Fuera de alcance

- Implementacion de endpoints (va en `backend_00_roadmap`).
- Configuracion de CORS, autenticacion, middleware (pasos posteriores del backend roadmap).
- Tests de la API (los tests existentes del dominio/servicios deben seguir verdes).
