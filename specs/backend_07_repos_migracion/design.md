# Diseño: backend_07_repos_migracion

## Punto de partida medido

| Métrica | Valor |
|---|---|
| Repositorios | 20 |
| Métodos totales | ~500 |
| LOC total | ~9,000 |
| Placeholders `?` | ~687 |
| `lastrowid` / `last_insert_rowid` | ~99 |
| `INSERT OR REPLACE/IGNORE` | 12 |
| Funciones de fecha SQLite | ~24 |
| Repos sin transacciones (D6) | 20 de 20 (tras normalizar plan_mejoramiento) |

### Repos por tamaño (métodos)

| Repo | Métodos |
|---|---|
| infraestructura | 121 |
| convivencia | 52 |
| auditoria | 34 |
| evaluacion | 30 |
| estudiante | 25 |
| usuario | 22 |
| plan_mejoramiento | 21 |
| periodo | 20 |
| estadisticos | 20 |
| configuracion | 20 |
| asistencia | 18 |
| acudiente | 18 |
| cierre | 17 |
| alerta | 17 |
| nivelacion | 16 |
| habilitacion | 16 |
| asignacion | 15 |
| siee | 12 |
| institucion | 10 |
| preferencias | 7 |

## D1 — Orden de migración

De menor a mayor superficie, para construir confianza en el patrón:

1. **Ola 1 — repos pequeños (≤12 métodos):** preferencias, institucion, siee.
2. **Ola 2 — repos medianos (13-20):** asignacion, habilitacion, nivelacion,
   cierre, alerta, acudiente, asistencia, configuracion, estadisticos, periodo,
   plan_mejoramiento.
3. **Ola 3 — repos grandes (>20):** usuario, estudiante, evaluacion, auditoria,
   convivencia, infraestructura.

Cada ola es un commit (o varios) con tests verdes al final.

## D2 — Patrón de migración por método

Antes (SQLite crudo):
```python
def listar_grados(self, institucion_id):
    sql = "SELECT * FROM grados WHERE institucion_id = ? ORDER BY nombre"
    rows = self._conn.execute(sql, (institucion_id,)).fetchall()
    return [Grado(**dict(row)) for row in rows]
```

Después (SQLAlchemy Core):
```python
from src.infrastructure.db.schema import grados

def listar_grados(self, institucion_id):
    stmt = select(grados).where(
        grados.c.institucion_id == institucion_id
    ).order_by(grados.c.nombre)
    rows = self._conn.execute(stmt)
    return [Grado(**row._mapping) for row in rows]
```

## D3 — Upserts portables (D3)

`INSERT OR REPLACE` → upsert de SQLAlchemy:

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

stmt = sqlite_insert(tabla).values(...)
stmt = stmt.on_conflict_do_update(
    index_elements=[tabla.c.col_unique],
    set_={col: stmt.excluded.col for col in cols_to_update}
)
conn.execute(stmt)
```

Para Postgres (`backend_09`), se usa `sqlalchemy.dialects.postgresql.insert`.
Se crea un helper `upsert(tabla, values, conflict_cols)` que detecta el
dialecto.

## D4 — Fechas neutras (funciones SQLite)

| SQLite | SQLAlchemy Core |
|---|---|
| `strftime('%Y-%m-%d', ...)` | `func.date(...)` o Python `date.isoformat()` |
| `date('now')` | `func.current_date()` — EVITAR, mismos problemas de UTC |
| `julianday(...)` | Cálculo en Python |

La regla de `datos_08`: los defaults de fecha los controla el dominio
(Python con zona horaria correcta), no la base de datos.

## D5 — RepositorioBase con filtro de tenant (tenant_06)

```python
class RepositorioBase:
    def __init__(self, conn, tabla: Table):
        self._conn = conn
        self._tabla = tabla

    def _select(self, *cols):
        stmt = select(*cols) if cols else select(self._tabla)
        if "institucion_id" in self._tabla.c:
            # El filtro se aplica en el servicio via TenantScope
            pass
        return stmt
```

`tenant_06` originalmente proponía `do_orm_execute` y `with_loader_criteria`,
que son mecanismos del ORM. Con Core, el filtro se aplica explícitamente
en un método base que los repos heredan.

Un test de conformidad (T9) verifica que toda query sobre tabla con
`institucion_id` lo filtra.

## D6 — Transacciones (D6 de la auditoría)

Los repos migrados usan `conn.begin()`:

```python
def operacion_compuesta(self, ...):
    with self._conn.begin():
        self._conn.execute(insert_1)
        self._conn.execute(insert_2)
        self._conn.execute(insert_auditoria)
```

Si cualquier execute falla, el bloque `begin()` hace rollback automático.

## Alternativa descartada

**Migrar todos los repos de golpe en un solo commit.** Un diff de ~9,000
líneas es irrevisable (precedente documentado en CLAUDE.md). La migración
por olas permite verificar el patrón con repos pequeños antes de tocar los
grandes.
