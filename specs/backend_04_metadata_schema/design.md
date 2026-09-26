# Diseño: backend_04_metadata_schema

## Punto de partida medido

| Métrica | Valor |
|---|---|
| Tablas en `SCHEMA` | 65 |
| Líneas DDL en `schema.py` | 1,654 |
| `AUTOINCREMENT` | ~56 |
| `ON CONFLICT REPLACE` | 10 tablas |
| `CHECK` constraints existentes | ~15 |
| `CHECK` constraints faltantes (deuda) | 5 |
| FKs fantasma (D2) | al menos `grupos.sala_id` |
| Dependencias FK adelantadas (D1) | `grupos→usuarios`, `observaciones_periodo→registro_comportamiento` |
| `DEFAULT CURRENT_DATE/TIMESTAMP` | 20 columnas |
| Columnas `REAL` para notas | 29 |

### Defectos que este paso resuelve

| # | Defecto | Resolución |
|---|---|---|
| D1 | Orden de dependencias violado | `create_all()` ordena por FKs; el código fuente agrupa por módulo |
| D2 | `grupos.sala_id` FK fantasma | Declarar `ForeignKey("salas.id")` o eliminar la columna |
| D3 | `ON CONFLICT REPLACE` en 10 tablas | `UniqueConstraint` estándar; upserts van a repos (`backend_07`) |
| D4 | 5 `CHECK` faltantes | `CheckConstraint` en el `MetaData` |
| D5 | `institucion_id` nullable en tablas de scope | `nullable=False` donde aplique |
| D10 | Trigger solo `BEFORE INSERT` | Ampliar a `BEFORE UPDATE` |
| D12 | Higiene varia | Limpiar en la reescritura |

### `tenant_05_desnormalizacion_transitivas` absorbido

`tenant_05` proponía desnormalizar `institucion_id` en tablas que hoy lo
infieren por JOIN. Como el esquema se recrea desde `create_all()` (sin
migraciones), hacerlo aquí es natural: añadir la columna con `ForeignKey`
en el MetaData, sin escribirla dos veces.

## D1 — Estructura del archivo

```
src/infrastructure/db/schema.py      ← reescritura completa

# Contenido:
metadata = MetaData()

# --- 1. Configuración institucional ---
instituciones = Table("instituciones", metadata, ...)
configuracion_anio = Table("configuracion_anio", metadata, ...)

# --- 2. Infraestructura académica ---
grados = Table("grados", metadata, ...)
# ... etc.

# --- 11. Auditoría ---
auditoria = Table("auditoria", metadata, ...)
audit_log = Table("audit_log", metadata, ...)
```

Se conserva la misma organización por 11 módulos funcionales.
Las listas `SCHEMA`, `INDICES` y `TRIGGERS` desaparecen.
Los índices se declaran con `Index(...)` en el mismo archivo.

## D2 — Triggers como DDL condicional

SQLAlchemy Core no tiene objeto nativo para triggers. Se declaran como
`DDL(...)` con `event.listen(metadata, "after_create", ...)` o se ejecutan
condicionalmente.

Para SQLite: triggers con `CREATE TRIGGER IF NOT EXISTS`.
Para Postgres (futuro): los mismos triggers o equivalentes con funciones.

Los triggers se mantienen como strings pero asociados al engine event,
no como lista suelta.

## D3 — Tipos neutros

| DDL actual | SQLAlchemy Core |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `Column("id", Integer, primary_key=True, autoincrement=True)` |
| `TEXT NOT NULL` | `Column("nombre", String, nullable=False)` |
| `REAL` (notas) | `Column("valor", Numeric(4, 2))` |
| `BOOLEAN NOT NULL DEFAULT 1` | `Column("activa", Boolean, nullable=False, server_default="1")` |
| `DATE NOT NULL DEFAULT CURRENT_DATE` | `Column("fecha", Date, nullable=False)` (default en dominio) |
| `TEXT CHECK(col IN ...)` | `Column(...) + CheckConstraint(...)` |

## D4 — ON CONFLICT REPLACE → UniqueConstraint

Las 10 tablas con `ON CONFLICT REPLACE` pasan a `UniqueConstraint` estándar.
El comportamiento de upsert se implementará en los repos (`backend_07`) con
`INSERT ... ON CONFLICT DO UPDATE`.

En este paso los repos siguen usando `INSERT OR REPLACE` que SQLite soporta.
No se rompe nada: el `UNIQUE` sin `ON CONFLICT` hace que SQLite lance error
en duplicados, pero los repos que usan `INSERT OR REPLACE` siguen funcionando
porque esa sintaxis es del `INSERT`, no del constraint.

**Corrección:** en realidad, `INSERT OR REPLACE` funciona independientemente
del constraint declaration. Lo que cambia es que un `INSERT` simple (sin
`OR REPLACE`) ahora fallará en duplicado en vez de reemplazar silenciosamente.
Verificar que ningún repo usa `INSERT` simple en esas tablas.

## D5 — Conftest actualizado

`_apply_schema` en conftest pasa de ejecutar strings DDL a llamar
`metadata.create_all(engine)` (donde engine es la conexión SQLite envuelta).

Si `backend_02` ya parametrizó el conftest, la conexión puede venir de la
factory. Si no, se crea un engine SQLAlchemy sobre SQLite en memoria.

## D6 — Dependencia nueva: sqlalchemy

Añadir `sqlalchemy>=2.0` a `requirements.txt`. Es la primera vez que entra
en el proyecto.

## Alternativa descartada

**Reescribir como ORM (declarative base con clases mapped).** La decisión
de David (roadmap línea 98) es SQLAlchemy Core estricto, no ORM. Core da
control explícito sobre las queries y evita la magia del ORM que complica
el debugging para un dev solo.
