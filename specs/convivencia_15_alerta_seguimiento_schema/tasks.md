# convivencia_15_alerta_seguimiento_schema — Tasks
> ⚠️ TOCA BD/enum/CHECK — puerta de aprobación de David antes del implementer.

## Objetivo
Añadir el nuevo tipo de alerta `SEGUIMIENTO_REQUERIDO` al enum `TipoAlerta`
en Python y a los CHECKs de las tablas `alertas` y `configuracion_alertas` en
SQLite. Añadir la columna `usuario_destino_id` (FK nullable a `usuarios`) en
`alertas` para alertas dirigidas a un profesor específico.

## Scope
```
src/domain/models/alerta.py
src/infrastructure/db/schema.py
src/infrastructure/db/repositories/sqlite_alerta_repo.py
src/infrastructure/db/seed.py
tests/
```

## Diseño

### Por qué este paso es el más delicado de la Fase 5
SQLite **no soporta `ALTER TABLE ... MODIFY COLUMN`** — los CHECKs existentes
no se pueden ampliar en tablas con datos. La estrategia es la misma que usa el
proyecto para migraciones complejas: **recrear la tabla** usando la secuencia
`CREATE TABLE nuevo ... INSERT INTO nuevo SELECT ... FROM viejo DROP TABLE viejo
RENAME TABLE nuevo TO viejo`, todo dentro de una transacción.

Sin embargo, el proyecto **ya usa `_asegurar_columna`** para añadir columnas
sin recrear. Para el CHECK, la solución más pragmática (y la que usa el proyecto
en el resto de tablas) es:

> **Recrear la tabla con el CHECK ampliado** solo si la BD es de prueba/vacía
> (en `create_schema` puro) y usar **`_asegurar_columna`** para la columna nueva
> `usuario_destino_id` en BDs existentes. El nuevo valor del enum Python funciona
> aunque la BD tenga el CHECK antiguo porque SQLite no valida el CHECK al SELECT —
> solo al INSERT/UPDATE. La validación de que el valor es válido la hace el
> dominio Python, no la BD.

**Estrategia concreta:**
1. En `schema.py`: actualizar el `CREATE TABLE IF NOT EXISTS alertas` y
   `configuracion_alertas` con el CHECK ampliado (incluye `seguimiento_requerido`).
   Esto aplica a BDs nuevas creadas desde cero.
2. Para BDs existentes: añadir `usuario_destino_id` con `_asegurar_columna`.
   El CHECK del string `seguimiento_requerido` en una BD existente se salta con
   `PRAGMA ignore_check_constraints = ON` durante la inserción, o —más limpio—
   se realiza una reconstrucción de la tabla si es necesario.
   **Decisión de diseño**: dado que la app usa SQLite en modo desarrollo y el
   seed recrea la BD en tests, la reconstrucción se hace **solo si el CHECK
   antiguo falta el nuevo valor** (detectado con `.fetchall()` sobre
   `sqlite_master` para leer el DDL de la tabla). Si el DDL ya contiene
   `seguimiento_requerido`, se omite. De lo contrario, se ejecuta la
   reconstrucción dentro de una transacción.

### Enum actualizado (`alerta.py`)
```python
class TipoAlerta(str, Enum):
    FALTAS_INJUSTIFICADAS     = "faltas_injustificadas"
    PROMEDIO_BAJO             = "promedio_bajo"
    MATERIAS_EN_RIESGO        = "materias_en_riesgo"
    PLAN_MEJORAMIENTO_VENCIDO = "plan_mejoramiento_vencido"
    HABILITACION_PENDIENTE    = "habilitacion_pendiente"
    SEGUIMIENTO_REQUERIDO     = "seguimiento_requerido"    # NUEVO
```

### Modelo `Alerta` actualizado
```python
usuario_destino_id: int | None = None   # NUEVO — profesor destinatario
```

### Columna nueva en `alertas` (migración idempotente)
```python
_asegurar_columna(
    conn, "alertas", "usuario_destino_id",
    "INTEGER REFERENCES usuarios(id) ON DELETE SET NULL"
)
```

### CHECK ampliado en las dos tablas (script de reconstrucción)
Función `_migrar_alertas_check(conn)` que:
1. Lee el DDL de `alertas` con `SELECT sql FROM sqlite_master WHERE name='alertas'`.
2. Si `'seguimiento_requerido'` ya está en el DDL → return (idempotente).
3. Executa dentro de transacción:
   ```sql
   PRAGMA foreign_keys = OFF;
   CREATE TABLE alertas_new (... CHECK ampliado ...);
   INSERT INTO alertas_new SELECT id, estudiante_id, tipo_alerta, nivel, descripcion,
       fecha_generacion, resuelta, fecha_resolucion, usuario_resolucion_id,
       observacion_resolucion, NULL AS usuario_destino_id FROM alertas;
   DROP TABLE alertas;
   ALTER TABLE alertas_new RENAME TO alertas;
   PRAGMA foreign_keys = ON;
   ```
4. Misma operación para `configuracion_alertas`.

### Seed de `configuracion_alertas` para el nuevo tipo
```python
("seguimiento_requerido", 1.0, True, True, False),
```
(notifica al docente y al director; umbral 1 → cualquier alerta manual activa la config.)

### Repo actualizado (`sqlite_alerta_repo.py`)
- Mapper `_row_to_alerta(row)`: añadir `usuario_destino_id` (puede ser None).
- Métodos de escritura: incluir `usuario_destino_id` en INSERT de `guardar_alerta`.

## Tareas

### T1 — `alerta.py`: añadir valor `SEGUIMIENTO_REQUERIDO` al enum `TipoAlerta` y campo `usuario_destino_id` al modelo `Alerta`

### T2 — `schema.py`:
- Actualizar `CREATE TABLE IF NOT EXISTS alertas` y `configuracion_alertas` con CHECK ampliado.
- Añadir función `_migrar_alertas_check(conn)` con la reconstrucción idempotente.
- Llamar `_migrar_alertas_check(conn)` y `_asegurar_columna(conn, "alertas", "usuario_destino_id", ...)` en `create_schema`.

**Verificación**:
```
.venv/Scripts/python.exe -c "
from src.infrastructure.db.schema import create_schema
import sqlite3; conn = sqlite3.connect(':memory:')
create_schema(conn)
# Tabla nueva debe tener el CHECK con seguimiento_requerido
conn.execute(\"INSERT INTO alertas (estudiante_id, tipo_alerta, nivel, descripcion) VALUES (1,'seguimiento_requerido','advertencia','test')\")
cols = [r[1] for r in conn.execute('PRAGMA table_info(alertas)').fetchall()]
assert 'usuario_destino_id' in cols
print('OK')
"
```

### T3 — `sqlite_alerta_repo.py`: propagar `usuario_destino_id` en mapper e INSERT

### T4 — `seed.py`: añadir `seguimiento_requerido` a `_TIPOS_ALERTAS`

### T5 — Tests
`tests/integration/test_alertas_seguimiento.py` (crear):
- `test_crear_alerta_seguimiento_requerido` — INSERT de `Alerta(tipo=SEGUIMIENTO_REQUERIDO, usuario_destino_id=X)` → se lee correctamente.
- `test_migracion_check_idempotente` — llamar `create_schema` dos veces no falla.

## criterio_done
- [ ] `TipoAlerta.SEGUIMIENTO_REQUERIDO` existe en el enum.
- [ ] `Alerta.usuario_destino_id` existe en el modelo.
- [ ] `alertas` y `configuracion_alertas` aceptan `seguimiento_requerido` en su CHECK (BDs nuevas y migradas).
- [ ] `_migrar_alertas_check` es idempotente.
- [ ] `usuario_destino_id` existe como columna en `alertas`.
- [ ] Seed incluye el nuevo tipo.
- [ ] Mapper del repo incluye el nuevo campo.
- [ ] Tests de integración verdes.
- [ ] `init.py --quick` → ENTORNO OK.
