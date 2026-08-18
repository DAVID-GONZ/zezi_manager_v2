# seguridad_web_02_secretos_config — Spec

## Contexto

Salir a produccion con la landing publica (`portal_36`) obliga a endurecer el manejo de
secretos. `config.py` ya bloquea el arranque en `APP_ENV=production` si `JWT_SECRET` o
`STORAGE_SECRET` conservan su valor por defecto (`config.py:148-164`) — eso esta hecho y
solo se verifica. Pero quedan huecos verificados en el codigo actual:

1. `.gitignore` ignora `.env` (`.gitignore:74`) pero **no** `.env.*` — un `.env.local` o
   `.env.production` podria commitearse por accidente.
2. `Settings` (pydantic `BaseSettings`, `config.py:49`) **no enmascara** `JWT_SECRET` /
   `STORAGE_SECRET` en su `__repr__`/serializacion: cualquier log de la config expondria
   los secretos.
3. No existe `.env.example` con instrucciones de generacion.

El stack sigue en **SQLite**: no existe `DATABASE_URL`. Por eso la parte del roadmap
original atada a Postgres (bloqueo de arranque por `DATABASE_URL`) **se difiere** hasta la
Etapa A de backend (`roadmaps/backend_00_roadmap_sqlalchemy_api`), y este paso cubre solo
lo que aplica hoy.

Scope: `src/config.py` (enmascarado), `.gitignore` (anadir `.env.*`),
`.env.example` (nuevo), `tests/unit/test_config_secretos.py` (nuevo),
`docs/seguridad.md` (generacion/rotacion/permisos).

## Requisitos (EARS)

- **R1** — Cada entorno DEBE tener `JWT_SECRET` y `STORAGE_SECRET` distintos e
  independientes. `DATABASE_URL` queda **diferido** (no existe en el stack SQLite actual;
  se retomara en `backend_00`).
- **R2** — EN PRODUCCION los secretos DEBEN provenir de variables de entorno del SO o de
  un gestor de secretos, nunca de un `.env` en disco.
- **R3** — `.gitignore` DEBE incluir `.env` **y `.env.*`** (hoy falta el segundo). El
  historial DEBE verificarse limpio de secretos.
- **R4** — `Settings` DEBE enmascarar `JWT_SECRET` y `STORAGE_SECRET` en `__repr__` y en
  cualquier serializacion de la config. NUNCA `.dict()` → `model_dump()`.
- **R5** — DEBE existir `.env.example` commiteado, con instrucciones de generacion
  (`secrets.token_urlsafe(48)`) y sin valores reales.
- **R6** — El proceso DEBE poder correr como usuario no-root con permisos 600 en archivos
  de config (tarea de deploy/documentacion).
- **R7** — La rotacion de secretos DEBE ser posible sin downtime (recarga/reinicio rapido,
  sin redesplegar codigo). Documentar el procedimiento.
- **R8** *(verificacion, no desarrollo)* — DEBE existir test que confirme que el arranque
  aborta en `production` con secretos por defecto (comportamiento ya presente en
  `config.py:148-164`) y que `JWT_SECRET != STORAGE_SECRET`.

## Diseño

### T1 — `.gitignore` + auditoria de historial

Anadir `.env.*` bajo la seccion `# Environments` (`.gitignore:73-80`). Ejecutar
`git log --all -S "token_urlsafe" -- "*.env*"` y confirmar que no hay commits con valores
reales; documentar el hallazgo en `docs/seguridad.md`.

### T2 — Enmascarado en `Settings` (`src/config.py`)

Anadir a `Settings` un `__repr__` que reemplace los campos sensibles por `***`. Ejemplo:

```python
_SENSIBLES = ("JWT_SECRET", "STORAGE_SECRET")

def __repr__(self) -> str:
    d = self.model_dump()
    for k in self._SENSIBLES:
        if d.get(k):
            d[k] = "***"
    return f"Settings({d})"
```

No cambia el acceso normal a los atributos; solo la representacion/logging.

### T3 — `.env.example` (nuevo)

Claves requeridas (`APP_ENV`, `JWT_SECRET`, `STORAGE_SECRET`, `HOST`, `RELOAD`) con
comentario de generacion: `python -c "import secrets;print(secrets.token_urlsafe(48))"`.
Sin valores reales. DEBE commitearse (no matchea `.gitignore`).

### T4 — Tests (`tests/unit/test_config_secretos.py`, nuevo)

- Arranque en `production` con `JWT_SECRET` por defecto → aborta (R8).
- `repr(settings)` no contiene el valor de los secretos (R4).
- `JWT_SECRET != STORAGE_SECRET` cuando ambos setteados.

### T5 — Documentacion (`docs/seguridad.md`)

Procedimiento de generacion, rotacion sin downtime, usuario no-root, permisos 600.

## Tareas

- [ ] **T1** — Anadir `.env.*` a `.gitignore` y auditar historial con `git log -S`.
  Verificacion: `git check-ignore .env.local` devuelve match; `git check-ignore .env.example` NO matchea.
- [ ] **T2** — `Settings.__repr__` enmascara secretos usando `model_dump()`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/test_config_secretos.py -q`
- [ ] **T3** — Crear `.env.example` con instrucciones de generacion, sin valores reales.
  Verificacion: revision + `git check-ignore .env.example` NO matchea.
- [ ] **T4** — Tests de aborto en prod, enmascarado y secretos distintos.
  Verificacion: incluida en T2.
- [ ] **T5** — Documentar generacion/rotacion/permisos en `docs/seguridad.md`.
  Verificacion: revision (documento).

## Verificacion final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/test_config_secretos.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer domain
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Criterios: `.gitignore` cubre `.env.*`; `repr(settings)` enmascara secretos (test verde);
`.env.example` commiteado sin valores reales; aborto en produccion probado; `init.py` verde.

## Dependencias

Ninguna spec previa. **Gate de deploy** de `portal_36_landing_marketing`. La parte de
`DATABASE_URL` se retoma en `backend_00` (Etapa A).
