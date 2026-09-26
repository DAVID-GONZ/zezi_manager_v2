# Diseño: backend_06_queries_sqlalchemy

## Punto de partida medido

`queries.py` tiene 5 funciones, 237 líneas. Todas:
1. Llaman `get_connection()` de `connection.py` (sqlite3).
2. Ejecutan SQL como string con `conn.execute(query, params)`.
3. Atrapan `Exception` y devuelven valores vacíos silenciosamente (D8).
4. Usan `_normalize_params` para convertir numpy a nativos.

Los repos llaman estas funciones con SQL crudo y placeholders `?`.

## D1 — Conexión via engine

Las funciones pasan de `get_connection()` (sqlite3) a
`Container.engine().connect()` (SQLAlchemy):

```python
from sqlalchemy import text

def fetch_one(query: str, params=None):
    with Container.engine().connect() as conn:
        result = conn.execute(text(query), _adapt_params(params))
        row = result.mappings().first()
        return dict(row) if row else None
```

`text(query)` convierte el string SQL en un TextClause de SQLAlchemy.
Los placeholders `:nombre` funcionan directamente; los `?` de SQLite
requieren adaptación (ver D2).

## D2 — Adaptación de placeholders

SQLAlchemy `text()` usa `:nombre` para params nombrados. Los repos
actuales usan `?` (qmark de sqlite3) con parámetros posicionales.

Opciones:
1. **Convertir `?` a `:p0, :p1, ...` automáticamente** en `_adapt_params`.
2. **Usar `conn.exec_driver_sql(query, params)`** que pasa directo al DBAPI
   sin parsear — acepta `?` tal cual en SQLite.

Se elige **opción 2** (`exec_driver_sql`) para las funciones que reciben
SQL crudo con `?`. Es la ruta de menor riesgo: no se transforma la query,
se pasa directo al driver DBAPI subyacente.

Para funciones que reciben `:nombre` (como `execute` con `dict` params),
se usa `text()` normalmente.

## D3 — Manejo de errores (D8)

**Escrituras (`execute`):** se propagan excepciones. Un `INSERT` fallido
no devuelve `False` silenciosamente — el servicio decide qué hacer.

**Lecturas:** se mantiene el logging de error pero se añade una opción
`raise_on_error=False` (default) para compatibilidad. Los repos que quieran
propagar el error pasan `raise_on_error=True`.

Esto permite migrar gradualmente sin romper los 20 repos de golpe.

## D4 — fetch_df con SQLAlchemy

`pd.read_sql(query, conn)` funciona con conexiones SQLAlchemy directamente.
Se cambia el context manager:

```python
def fetch_df(query, params=None, ...):
    with Container.engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=_adapt_params(params))
```

## D5 — _normalize_params adaptado

La normalización de numpy/pandas a nativos se conserva. Se renombra a
`_adapt_params` y además convierte la tupla posicional a dict si es
necesario para `text()`.

## Alternativa descartada

**Eliminar `queries.py` directamente y que los repos usen SQLAlchemy Core
constructs (`select`, `insert`).** Eso es el contenido de `backend_07`.
Este paso solo cambia el transporte (sqlite3 → SQLAlchemy connection),
no el lenguaje de las queries.
