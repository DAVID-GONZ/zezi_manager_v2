# Tasks: mejora_07 — Scoping completo de tablas globales

> Aprobado: pendiente confirmación de David.
> Scope: ver design.md.

## Regla de implementación (R12)
Después de CADA tarea T1-T7, ejecutar `python -m pytest tests/ -q --tb=short` antes
de continuar. Una tarea que deje tests rojos NO se marca como completada.

---

## T0 — Verificación R13 (audit de tablas raíz)

**Acción:** Solo lectura. Verificar que los 8 repos/servicios ya scopeados
(`configuracion_anio`, `usuarios`, `estudiantes`, `grupos`, `asignaturas`,
`plantillas_franja`, `salas`) usan `verificar_pertenencia()` consistentemente.

Comprobar con Grep en `src/services/`:
```python
# Verificar presencia de verificar_pertenencia en servicios de tablas raíz
grep -rn "verificar_pertenencia" src/services/
```

Escribir hallazgos en `progress/audit_r13.md` con tabla de cobertura. No cambiar código.

**Verificación:**
```bash
python -c "
from src.services.contexto_tenant import verificar_pertenencia
from src.services.configuracion_service import ConfiguracionService
print('R13 verificado — ver progress/audit_r13.md')
"
```

---

## T1 — `areas_conocimiento`

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/infraestructura.py`
- `src/domain/ports/infraestructura_repo.py`
- `src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`
- `src/services/catalogo_academico_service.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:** En `CREATE TABLE IF NOT EXISTS areas_conocimiento`, añadir:
```sql
    institucion_id  INTEGER REFERENCES instituciones(id),
    UNIQUE(institucion_id, nombre)
```
Y eliminar el `nombre TEXT NOT NULL UNIQUE` → cambiarlo a `nombre TEXT NOT NULL`.
(Para nuevas instalaciones; las BDs existentes conservan el UNIQUE anterior.)

**infraestructura.py:** Añadir a `AreaConocimiento`:
```python
institucion_id: int | None = None
```

**infraestructura_repo.py:** Actualizar firma de `listar_areas`:
```python
@abstractmethod
def listar_areas(self, institucion_id: int | None = None) -> list[AreaConocimiento]: ...
```

**sqlite_infraestructura_repo.py:**
- `listar_areas(self, institucion_id=None)`:
  ```python
  sql = "SELECT * FROM areas_conocimiento WHERE 1=1"
  params = []
  if institucion_id is not None:
      sql += " AND institucion_id = ?"
      params.append(institucion_id)
  sql += " ORDER BY nombre"
  ```
- `guardar_area(area)`: añadir `institucion_id` al INSERT.
- `actualizar_area(area)`: SET incluye `institucion_id` (pero no se cambia: `WHERE id=?`).

**catalogo_academico_service.py:**
```python
def listar_areas(self) -> list[AreaConocimiento]:
    from src.services.contexto_tenant import institucion_actual
    return self._repo.listar_areas(institucion_id=institucion_actual())

@requiere_escritura
def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
    from src.services.contexto_tenant import institucion_actual
    if not area.institucion_id:
        area = area.model_copy(update={"institucion_id": institucion_actual()})
    return self._repo.guardar_area(area)
```

**seed.py:** Añadir función (llamar al final de `_seed_institucion`):
```python
def _migrate_areas_conocimiento_scoping(conn, inst_id: int) -> None:
    existing = {r[1] for r in conn.execute("PRAGMA table_info(areas_conocimiento)").fetchall()}
    if "institucion_id" not in existing:
        conn.execute("ALTER TABLE areas_conocimiento ADD COLUMN institucion_id INTEGER REFERENCES instituciones(id)")
    conn.execute("UPDATE areas_conocimiento SET institucion_id = ? WHERE institucion_id IS NULL", (inst_id,))
```

**Verificación:**
```bash
python -c "
from src.domain.models.infraestructura import AreaConocimiento
a = AreaConocimiento(nombre='Matemáticas')
assert a.institucion_id is None
a2 = a.model_copy(update={'institucion_id': 1})
assert a2.institucion_id == 1
print('T1 dominio OK')
"
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T2 — `plan_estudios`

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/infraestructura.py`
- `src/domain/ports/infraestructura_repo.py`
- `src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`
- `src/services/plan_estudios_service.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:** En `CREATE TABLE IF NOT EXISTS plan_estudios`, añadir `institucion_id` y cambiar UNIQUE:
```sql
    institucion_id  INTEGER REFERENCES instituciones(id),
    UNIQUE(institucion_id, grado, asignatura_id)
```
(Eliminar `UNIQUE(grado, asignatura_id)` del bloque nuevo.)

**infraestructura.py:** Añadir a `PlanEstudios`:
```python
institucion_id: int | None = None
```

**infraestructura_repo.py:** Actualizar firmas:
```python
def listar_plan_estudios(self, institucion_id: int | None = None) -> list[PlanEstudios]: ...
def get_plan_estudios_por_grado(self, grado: int, institucion_id: int | None = None) -> list[PlanEstudios]: ...
```

**sqlite_infraestructura_repo.py:**
- `listar_plan_estudios(institucion_id=None)` — filtro condicional.
- `get_plan_estudios_por_grado(grado, institucion_id=None)` — añadir filtro.
- `agregar_plan_estudios(...)` — incluir `institucion_id` en INSERT.

**plan_estudios_service.py:** Añadir helper de tenant e inyectar en métodos:
```python
@staticmethod
def _resolver_institucion(institucion_id: int | None) -> int | None:
    if institucion_id is not None:
        return institucion_id
    from src.services.contexto_tenant import institucion_actual
    scope = institucion_actual()
    if scope is not None:
        return scope
    try:
        from container import Container
        return Container.institucion_service().id_por_defecto()
    except Exception:
        return None

def listar_plan_estudios(self) -> list[PlanEstudios]:
    return self._repo.listar_plan_estudios(
        institucion_id=self._resolver_institucion(None)
    )

def get_plan_estudios_por_grado(self, grado: int) -> list[PlanEstudios]:
    return self._repo.get_plan_estudios_por_grado(
        grado=grado,
        institucion_id=self._resolver_institucion(None),
    )
```

En `agregar_plan_estudios(...)`:
```python
inst_id = self._resolver_institucion(None)
# ... asignar inst_id al plan antes de insertar
```

**seed.py:** `_migrate_plan_estudios_scoping(conn, inst_id)` — ALTER + backfill.

**Verificación:**
```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T3 — `categorias_observacion` + `plantillas_observacion`

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/convivencia.py`
- `src/domain/ports/convivencia_repo.py`
- `src/infrastructure/db/repositories/sqlite_convivencia_repo.py`
- `src/services/convivencia_service.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:**
- `categorias_observacion`: `institucion_id` + `UNIQUE(institucion_id, nombre)`.
- `plantillas_observacion`: `institucion_id` (sin UNIQUE propio).

**convivencia.py:** Añadir a `CategoriaObservacion` y `PlantillaObservacion`:
```python
institucion_id: int | None = None
```

**convivencia_repo.py:** Actualizar firmas:
```python
def listar_categorias(self, institucion_id: int | None = None) -> list[CategoriaObservacion]: ...
def listar_plantillas(self, categoria_id: int | None = None, institucion_id: int | None = None) -> list[PlantillaObservacion]: ...
```

**sqlite_convivencia_repo.py:**
- `listar_categorias(institucion_id=None)` — filtro condicional.
- `crear_categoria(cat)` — incluir `institucion_id` en INSERT.
- `listar_plantillas(categoria_id, institucion_id=None)` — filtro condicional.
- `crear_plantilla(plt)` — incluir `institucion_id` en INSERT.

**convivencia_service.py:** 
- `listar_categorias_observacion()` → pasa `institucion_actual()`.
- `crear_categoria_observacion(dto)` → inyecta tenant.
- `listar_plantillas_observacion(...)` → pasa `institucion_actual()`.
- `crear_plantilla_observacion(dto)` → inyecta tenant.
- Verificar que `_resolver_institucion` o patrón equivalente existe; si no, añadirlo.

**seed.py:** `_migrate_categorias_scoping(conn, inst_id)` — dos ALTER + dos backfills.

**Verificación:**
```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T4 — `acudientes`

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/acudiente.py`
- `src/domain/ports/acudiente_repo.py`
- `src/infrastructure/db/repositories/sqlite_acudiente_repo.py`
- `src/services/acudiente_service.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:** `acudientes` — añadir `institucion_id`, cambiar `numero_documento UNIQUE` → `UNIQUE(institucion_id, numero_documento)`.

**acudiente.py:** Añadir a `Acudiente`:
```python
institucion_id: int | None = None
```

**acudiente_repo.py:** Actualizar:
```python
def listar(self, activos_solo: bool = False, institucion_id: int | None = None) -> list[Acudiente]: ...
def buscar_por_documento(self, numero: str, institucion_id: int | None = None) -> Acudiente | None: ...
```

**sqlite_acudiente_repo.py:** Filtros condicionales + `institucion_id` en INSERT.

**acudiente_service.py:** Añadir `_resolver_institucion()`, pasar a queries de lectura. En `crear_acudiente(dto)` inyectar tenant.

**seed.py:** `_migrate_acudientes_scoping(conn, inst_id)` — ALTER + backfill.

**Verificación:**
```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T5 — `franjas_reunion`

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/infraestructura.py`
- `src/domain/ports/infraestructura_repo.py`
- `src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`
- `src/services/restriccion_generacion_service.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:** `franjas_reunion` — añadir `institucion_id`.

**infraestructura.py:** Añadir a `FranjaReunion`:
```python
institucion_id: int | None = None
```

**infraestructura_repo.py:**
```python
def listar_franjas_reunion(self, institucion_id: int | None = None) -> list[FranjaReunion]: ...
```

**sqlite_infraestructura_repo.py:**
- `listar_franjas_reunion(institucion_id=None)` — filtro condicional.
- `crear_franja_reunion(f)` — incluir `institucion_id` en INSERT.
- `actualizar_franja_reunion(f)` — sin cambio de `institucion_id`.

**restriccion_generacion_service.py:**
- `listar_franjas_reunion()` → pasa `institucion_actual()`.
- `crear_franja_reunion(f)` → inyecta tenant si no viene.

**seed.py:** `_migrate_franjas_reunion_scoping(conn, inst_id)` — ALTER + backfill.

**Verificación:**
```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T6 — `configuracion_grado_institucion` (nueva tabla)

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/infraestructura.py`
- `src/domain/ports/infraestructura_repo.py`
- `src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`
- `src/services/plan_estudios_service.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:** Añadir al final de SCHEMA (antes de `]`):
```sql
CREATE TABLE IF NOT EXISTS configuracion_grado_institucion (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    grado_id         INTEGER NOT NULL REFERENCES grados(id) ON DELETE CASCADE,
    institucion_id   INTEGER NOT NULL REFERENCES instituciones(id),
    min_estudiantes  INTEGER NOT NULL DEFAULT 0  CHECK(min_estudiantes >= 0),
    max_estudiantes  INTEGER NOT NULL DEFAULT 40 CHECK(max_estudiantes >= 1),
    horas_semanales  INTEGER NOT NULL DEFAULT 0  CHECK(horas_semanales >= 0),
    UNIQUE(grado_id, institucion_id)
)
```
Y en INDICES:
```python
"CREATE INDEX IF NOT EXISTS idx_cfg_grado_inst ON configuracion_grado_institucion(institucion_id)",
```

**infraestructura.py:** Añadir modelo:
```python
class ConfiguracionGradoInstitucion(BaseModel):
    id:              int | None = None
    grado_id:        int
    institucion_id:  int
    min_estudiantes: int = 0
    max_estudiantes: int = 40
    horas_semanales: int = 0
```

**infraestructura_repo.py:**
```python
@abstractmethod
def get_config_grado(self, grado_id: int, institucion_id: int) -> "ConfiguracionGradoInstitucion | None": ...

@abstractmethod
def upsert_config_grado(self, cfg: "ConfiguracionGradoInstitucion") -> "ConfiguracionGradoInstitucion": ...
```

**sqlite_infraestructura_repo.py:** Implementar ambos métodos con INSERT OR REPLACE.

**plan_estudios_service.py:** Añadir:
```python
def get_config_grado(self, grado_num: int, institucion_id: int | None = None) -> ConfiguracionGradoInstitucion:
    """Retorna config del grado para la institución o defaults de grados."""
    inst_id = institucion_id or self._resolver_institucion(None)
    grado = next((g for g in self._repo.listar_grados() if g.numero == grado_num), None)
    if grado and inst_id:
        cfg = self._repo.get_config_grado(grado.id, inst_id)
        if cfg:
            return cfg
    return ConfiguracionGradoInstitucion(
        grado_id=grado.id if grado else 0,
        institucion_id=inst_id or 0,
        min_estudiantes=grado.min_estudiantes if grado else 0,
        max_estudiantes=grado.max_estudiantes if grado else 40,
        horas_semanales=grado.horas_semanales if grado else 0,
    )
```

**seed.py:** `_seed_config_grado_institucion(conn, inst_id)`:
```python
def _seed_config_grado_institucion(conn, inst_id: int) -> None:
    """Copia valores de grados → configuracion_grado_institucion para la institución indicada."""
    rows = conn.execute("SELECT id, min_estudiantes, max_estudiantes, horas_semanales FROM grados").fetchall()
    for grado_id, min_est, max_est, horas in rows:
        conn.execute(
            """INSERT OR IGNORE INTO configuracion_grado_institucion
               (grado_id, institucion_id, min_estudiantes, max_estudiantes, horas_semanales)
               VALUES (?,?,?,?,?)""",
            (grado_id, inst_id, min_est, max_est, horas),
        )
```
Llamar desde `_seed_institucion` tras el backfill.

**Verificación:**
```bash
python -c "
from src.domain.models.infraestructura import ConfiguracionGradoInstitucion
cfg = ConfiguracionGradoInstitucion(grado_id=1, institucion_id=1)
assert cfg.max_estudiantes == 40
print('T6 OK')
"
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T7 — `auditoria` + `audit_log`

**Archivos:**
- `src/infrastructure/db/schema.py`
- `src/domain/models/auditoria.py`
- `src/domain/ports/auditoria_repo.py`
- `src/infrastructure/db/repositories/sqlite_auditoria_repo.py`
- `src/infrastructure/db/seed.py`

### Cambios

**schema.py:**
- `auditoria`: añadir `institucion_id INTEGER REFERENCES instituciones(id)`. El campo es informacional; NO modifica la cadena de hash.
- `audit_log`: idem.

**auditoria.py:** Añadir a `EventoSesion` y `RegistroCambio`:
```python
institucion_id: int | None = None
```

**auditoria_repo.py:** `registrar_evento` y `registrar_cambio` reciben los modelos completos (sin cambio de firma); basta incluir el campo en el INSERT.

**sqlite_auditoria_repo.py:**
- `registrar_evento(evento)` — incluir `evento.institucion_id` en INSERT.
- `registrar_cambio(registro)` — incluir `registro.institucion_id` en INSERT.

> Los servicios que llaman `registrar_evento` / `registrar_cambio` deben
> inyectar `institucion_id` en el DTO antes de llamar. Ejemplo en
> `auditoria_service.registrar_evento`:
> ```python
> if not evento.institucion_id:
>     from src.services.contexto_tenant import institucion_actual
>     evento = evento.model_copy(update={"institucion_id": institucion_actual()})
> ```

**seed.py:** `_migrate_auditoria_scoping(conn, inst_id)`:
```python
def _migrate_auditoria_scoping(conn, inst_id: int) -> None:
    for tabla in ("auditoria", "audit_log"):
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
        if "institucion_id" not in existing:
            conn.execute(f"ALTER TABLE {tabla} ADD COLUMN institucion_id INTEGER REFERENCES instituciones(id)")
    # Backfill: asignar la institución del usuario actuante donde sea posible
    conn.execute("""
        UPDATE auditoria SET institucion_id = (
            SELECT u.institucion_id FROM usuarios u WHERE u.id = auditoria.usuario_id
        ) WHERE institucion_id IS NULL AND usuario_id IS NOT NULL
    """)
    conn.execute("""
        UPDATE audit_log SET institucion_id = (
            SELECT u.institucion_id FROM usuarios u WHERE u.id = audit_log.usuario_id
        ) WHERE institucion_id IS NULL AND usuario_id IS NOT NULL
    """)
    # Registros sin usuario → institución por defecto
    conn.execute("UPDATE auditoria SET institucion_id = ? WHERE institucion_id IS NULL", (inst_id,))
    conn.execute("UPDATE audit_log SET institucion_id = ? WHERE institucion_id IS NULL", (inst_id,))
```

**Verificación:**
```bash
python -c "
from src.domain.models.auditoria import EventoSesion, RegistroCambio, TipoEventoSesion, AccionCambio
e = EventoSesion(usuario='test', tipo_evento=TipoEventoSesion.LOGIN_EXITOSO)
assert e.institucion_id is None
e2 = e.model_copy(update={'institucion_id': 1})
assert e2.institucion_id == 1
print('T7 OK')
"
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## T8 — Seed de catálogos estándar para nuevas instituciones

**Archivo:** `src/infrastructure/db/seed.py`

Añadir función `_seed_catalogos_institucion(conn, institucion_id: int) -> None`
con áreas y categorías base (ver design.md §T8). Idempotente via INSERT OR IGNORE.

Llamar desde `_seed_institucion(conn)` justo después de `_seed_config_grado_institucion`.

**Verificación:**
```bash
python -c "
import sqlite3
conn = sqlite3.connect(':memory:')
conn.row_factory = sqlite3.Row
from src.infrastructure.db.schema import create_schema
create_schema(conn)
conn.execute(\"INSERT INTO instituciones (nombre, activa) VALUES ('IE', 1)\")
conn.commit()
from src.infrastructure.db.seed import _seed_catalogos_institucion
_seed_catalogos_institucion(conn, 1)
count = conn.execute('SELECT COUNT(*) FROM areas_conocimiento WHERE institucion_id=1').fetchone()[0]
assert count >= 12, f'Solo {count} areas'
count_cat = conn.execute('SELECT COUNT(*) FROM categorias_observacion WHERE institucion_id=1').fetchone()[0]
assert count_cat >= 4, f'Solo {count_cat} categorias'
# idempotente
_seed_catalogos_institucion(conn, 1)
assert conn.execute('SELECT COUNT(*) FROM areas_conocimiento WHERE institucion_id=1').fetchone()[0] == count
print('T8 OK')
"
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## Verificación final

```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

Sin regresiones en tests existentes (base: 1439 passed, 1 skipped).

```bash
python -c "
from src.domain.models.infraestructura import AreaConocimiento, PlanEstudios, FranjaReunion, ConfiguracionGradoInstitucion
from src.domain.models.convivencia import CategoriaObservacion, PlantillaObservacion
from src.domain.models.acudiente import Acudiente
from src.domain.models.auditoria import EventoSesion, RegistroCambio
# todos tienen institucion_id
for cls in [AreaConocimiento, PlanEstudios, FranjaReunion, CategoriaObservacion,
            PlantillaObservacion, Acudiente, EventoSesion, RegistroCambio]:
    obj = cls.__fields__ if hasattr(cls, '__fields__') else cls.model_fields
    assert 'institucion_id' in obj, f'{cls.__name__} sin institucion_id'
print('FINAL: todos los modelos scopeados OK')
"
```
