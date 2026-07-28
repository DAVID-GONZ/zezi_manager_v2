# convivencia_11_observaciones_categoria_autz — Tasks
> ⚠️ TOCA BD — puerta de aprobación de David antes del implementer.
> Prerequisito: convivencia_09 y convivencia_10 DONE.

## Objetivo
1. Añadir `categoria_id` (FK nullable a `categorias_observacion`) y `origen`
   (TEXT: `"libre"` | `"plantilla"`) a la tabla `observaciones_periodo`.
2. Hacer obligatoria la categoría al crear una observación nueva.
3. Reforzar la autorización por objeto: solo profesores **con asignación
   activa en el grupo** del contexto pueden crear/ver observaciones de ese
   grupo. La visibilidad privada/pública se resuelve en el servidor, no en el
   cliente.

## Scope
```
src/infrastructure/db/schema.py
src/domain/models/convivencia.py
src/domain/ports/convivencia_repo.py
src/infrastructure/db/repositories/sqlite_convivencia_repo.py
src/services/convivencia_service.py
src/interface/pages/convivencia/observaciones.py
tests/
```

## Diseño

### Columnas nuevas en `observaciones_periodo` (migración idempotente)
Usar `_asegurar_columna` (patrón ya existente en `schema.py`):
```python
_asegurar_columna(conn, "observaciones_periodo", "categoria_id",
                  "INTEGER REFERENCES categorias_observacion(id) ON DELETE SET NULL")
_asegurar_columna(conn, "observaciones_periodo", "origen",
                  "TEXT NOT NULL DEFAULT 'libre' CHECK(origen IN ('libre','plantilla'))")
```
No se modifica el `CREATE TABLE IF NOT EXISTS` existente (la tabla ya existe en producción).

### Modelo `ObservacionPeriodo` actualizado
Añadir campos:
```python
categoria_id: int | None = None
origen:       str        = "libre"
```

### DTO `NuevaObservacionDTO` actualizado
Añadir campo obligatorio:
```python
categoria_id: int   # ya no es None — obligatorio al crear
```
(Cuando venga de plantilla, `origen` se pone automáticamente en el servicio.)

### Autorización por objeto
En `ConvivenciaService.registrar_observacion()`:
- Si `usuario_rol == Rol.PROFESOR`, verificar que el `asignacion_id` del DTO
  pertenece al grupo del contexto Y que el `usuario_id` es el docente titular
  de esa asignación. Usar `catalogo_academico_svc_provider` (ya inyectado)
  para resolver `asignacion.usuario_id`.
- Si `usuario_rol in (Rol.DIRECTOR, Rol.COORDINADOR)`: acceso pleno.
- Director de grupo: acceso de lectura completa del grupo.

En `ConvivenciaService.listar_observaciones()`:
- Añadir parámetro `usuario_id: int | None = None` y `usuario_rol: str | None = None`.
- Si `usuario_rol == Rol.PROFESOR`: filtrar al servidor solo las observaciones
  de asignaciones del profesor (`asignacion_id` donde `usuario_id = usuario_id`).
  Esto elimina el filtrado manual en la página.

### UI actualizada
En `observaciones.py`:
- El `form_dialog` de nueva observación añade un selector de categoría
  (lista de `listar_categorias(solo_activas=True)`).
- La llamada a `listar_observaciones` pasa `usuario_id` y `usuario_rol`
  desde el contexto; la página ya no filtra en cliente.

## Tareas

### T1 — `schema.py`: migración idempotente
Añadir llamadas a `_asegurar_columna` dentro de la función `create_schema` o
en la función `migrate_schema` (donde vivan las migraciones idempotentes actuales).

**Verificación**:
```
.venv/Scripts/python.exe -c "
from src.infrastructure.db.schema import create_schema
import sqlite3; conn = sqlite3.connect(':memory:')
create_schema(conn)
cols = [r[1] for r in conn.execute('PRAGMA table_info(observaciones_periodo)').fetchall()]
assert 'categoria_id' in cols and 'origen' in cols
print('OK')
"
```

### T2 — `convivencia.py`: actualizar `ObservacionPeriodo` y `NuevaObservacionDTO`
Añadir `categoria_id: int | None = None` y `origen: str = "libre"` al modelo.
Añadir `categoria_id: int` (sin default) a `NuevaObservacionDTO`.

### T3 — `convivencia_repo.py` y `sqlite_convivencia_repo.py`: propagar campos
- Actualizar `guardar_observacion` para incluir `categoria_id` y `origen` en el INSERT.
- Actualizar `actualizar_observacion` para incluir los nuevos campos en el UPDATE.
- Actualizar `_row_to_observacion` para mapear los nuevos campos.
- Actualizar `listar_observaciones_por_estudiante` para aceptar `solo_publicas` con lógica
  ya existente (sin cambios en firma pública, los campos se incluyen automáticamente).

### T4 — `convivencia_service.py`: autorización por objeto + `listar_observaciones` con filtro
- `registrar_observacion`: validar que el profesor es titular de la asignación.
- `listar_observaciones`: añadir parámetros `usuario_id` y `usuario_rol`; cuando es
  profesor, filtrar al repo las observaciones de sus asignaciones.

### T5 — `observaciones.py`: selector de categoría + pasar rol/usuario_id
- Añadir selector de categoría en `form_dialog`.
- Pasar `usuario_id=ctx.usuario_id, usuario_rol=ctx.rol` al listar.

**Verificación**:
```
.venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/convivencia/observaciones.py
.venv/Scripts/python.exe scripts/check_imports.py --layer interface
```

### T6 — Tests
- `tests/integration/test_convivencia_categorias.py`: añadir `test_guardar_observacion_con_categoria`.
- `tests/unit/services/test_convivencia_service.py`: añadir `test_profesor_no_autorizado_registrar_observacion_ajena`.

## criterio_done
- [ ] Columnas `categoria_id` y `origen` existen en `observaciones_periodo` (migración idempotente).
- [ ] `NuevaObservacionDTO` exige `categoria_id`.
- [ ] Profesor sin asignación en el grupo → `PermissionError` al registrar.
- [ ] `listar_observaciones` filtra en servidor para profesores.
- [ ] Selector de categoría en UI.
- [ ] `check_design` y `check_imports` verdes.
- [ ] Tests nuevos verdes.
- [ ] `init.py --quick` → ENTORNO OK.
