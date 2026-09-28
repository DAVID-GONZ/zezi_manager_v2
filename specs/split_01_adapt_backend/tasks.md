# split_01_adapt_backend — Tareas

Scope: `app/`, `pyproject.toml`, `scripts/init.py`, `container.py`.
Repo destino: `avedra-backend`.
Cualquier otro archivo fuera de scope -> PARAR y reportar al leader.

---

## T1 — Crear stub FastAPI

**Artefactos:** `app/__init__.py`, `app/main.py`, `app/deps.py`, `app/routes/__init__.py`

- Crear `app/__init__.py` (vacio).
- Crear `app/main.py` con `create_app()` que retorna `FastAPI(title="AVEDRA")`.
- Crear `app/deps.py` con `get_container()` que instancia Container.
- Crear `app/routes/__init__.py` (vacio o con router placeholder).

**Verificacion:**
```bash
python -c "from app.main import app; print(type(app))"
```

---

## T2 — Limpiar pyproject.toml

**Artefacto:** `pyproject.toml`

- Eliminar `nicegui` y cualquier dependencia exclusiva de UI.
- Agregar `fastapi` y `uvicorn[standard]` si no estan.
- Verificar que `pydantic` sigue presente.

**Verificacion:**
```bash
grep -i "nicegui" pyproject.toml  # debe retornar 0
grep "fastapi" pyproject.toml     # debe retornar 1+
```

---

## T3 — Adaptar scripts/init.py

**Artefacto:** `scripts/init.py`

- Eliminar llamadas a `check_design.py`.
- Eliminar llamadas a `sync_tokens.py`.
- Eliminar llamadas a `audit_design.py`.
- Conservar: ruff, pytest, verificacion de imports.
- Verificar que init.py no importa nada de `src.interface`.

**Verificacion:**
```bash
python scripts/init.py  # debe completar sin errores de design system
```

---

## T4 — Limpiar container.py

**Artefacto:** `container.py`

- Eliminar imports de `src.interface`.
- Eliminar registros de presenters, pages, ThemeManager.
- Conservar: repos, servicios, config, contextos.

**Verificacion:**
```bash
grep -n "interface" container.py  # debe retornar 0
python -c "from container import Container; print('OK')"
```

---

## T5 — Verificacion integral

```bash
grep -rn "src\.interface\|src/interface\|from interface" src/ tests/ app/
python -c "from src.domain import models; print('domain OK')"
python -c "from src.services import usuario_service; print('services OK')"
python -m pytest tests/ -x
python scripts/init.py
```

Todo debe pasar sin errores ni referencias a `src/interface`.

Escribir resumen en `progress/impl_split_01_adapt_backend.md` y
devolver al leader solo esa referencia.
