# split_01_adapt_backend — Diseno

## Estructura del stub FastAPI

```
avedra-backend/
├── app/
│   ├── __init__.py          # vacio
│   ├── main.py              # create_app() factory
│   ├── deps.py              # get_container() dependency
│   └── routes/
│       └── __init__.py      # router vacio, placeholder
├── src/                     # dominio y servicios (ya existen)
├── tests/                   # ya existen
├── config.py                # ya existe
├── container.py             # limpiar registros de interfaz
└── pyproject.toml           # limpiar deps NiceGUI
```

## app/main.py

```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="AVEDRA", version="2.0.0")
    # Las rutas se agregan en pasos posteriores del backend roadmap
    return app

app = create_app()
```

## Dependencias a eliminar de pyproject.toml

Todo lo relacionado con NiceGUI y su ecosistema UI:
- `nicegui` (cualquier variante)
- Paquetes de ag-Grid si estan listados
- Cualquier dependencia exclusiva de la capa de interfaz

## Dependencias a agregar

- `fastapi` (si no esta)
- `uvicorn[standard]` (si no esta)
- `pydantic` (probablemente ya esta por los modelos de dominio)

## init.py — Secciones a eliminar

| Seccion actual | Accion |
|---|---|
| check_design.py --all | Eliminar |
| sync_tokens.py --check | Eliminar |
| audit_design.py [--strict] | Eliminar |
| Ruff (defectos F821, F811, etc.) | Conservar |
| pytest | Conservar |
| Verificacion de imports | Conservar |

## container.py — Registros a eliminar

Todo lo que referencie `src.interface`:
- Presenters
- Pages
- ThemeManager
- Cualquier componente de UI

Conservar:
- Repositorios (`src.infrastructure.db.repositories`)
- Servicios (`src.services`)
- Config
- Contextos (`src.infrastructure.context`)

## Riesgo

Medio. El filter-repo ya elimino los archivos de interfaz, pero los imports
pueden estar dispersos en container.py e init.py. La clave es no romper
los tests existentes.
