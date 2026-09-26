# Tareas: backend_05_engine_factory

> SCOPE — archivos que pueden editarse:
> `container.py`, `config.py`, `.env.example`, `requirements.txt` (psycopg).
>
> Fuera de scope: `connection.py` (no se elimina), repositorios, servicios.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**
>
> ⚠️ PUERTA DE APROBACIÓN: toca container.py.

---

## T1 — Añadir variables de configuración  [ ]

En `config.py`, añadir `DB_BACKEND` y `DATABASE_URL` desde env vars con
defaults.

En `.env.example`, documentar las variables con comentarios explicativos.

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from config import DB_BACKEND; print(DB_BACKEND)"
```
Debe imprimir `sqlite`.

---

## T2 — Crear la factory de engine  [ ]

En `container.py`, implementar `_create_engine()` y `Container.engine()`
según D1.

Para SQLite: event listener que aplica pragmas en cada conexión (D3).

**Restricciones:**
- El engine es singleton, almacenado en `_cache["engine"]`.
- Los pragmas de SQLite son idénticos a los de `get_connection()`.
- Para Postgres: `pool_pre_ping=True` para detectar conexiones muertas.

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from container import Container; Container.inicializar(); e = Container.engine(); print(e.url)"
```

---

## T3 — Exponer Container.connection()  [ ]

Context manager que devuelve una conexión del engine:

```python
@classmethod
@contextmanager
def connection(cls):
    with cls.engine().connect() as conn:
        yield conn
```

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from container import Container; Container.inicializar(); conn = Container.engine().connect(); print(conn.execute(sqlalchemy.text('SELECT 1')).scalar()); conn.close()"
```

---

## T4 — Verificar arranque de la app  [ ]

Arrancar la app con `DB_BACKEND=sqlite` y verificar que funciona
exactamente igual que antes. El engine se crea pero los repos siguen
usando `get_connection()` — la coexistencia (D2) es válida.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE.

---

## T5 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE.

**Artefacto:** `progress/impl_backend_05.md`.
