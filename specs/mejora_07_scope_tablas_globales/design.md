# Design: mejora_07 — Scoping completo de tablas globales

## Visión general

Nueve tablas actualmente globales reciben `institucion_id`. Cada tabla sigue el
mismo patrón de 5 pasos: (1) schema, (2) modelo de dominio, (3) puerto, (4) repo,
(5) servicio. La migración de cada tabla es idempotente y se verifica con la
suite de tests antes de pasar a la siguiente (R12).

---

## Patrón estándar (aplica a T1-T7)

### Schema (`schema.py`)
```sql
-- Añadir al CREATE TABLE:
institucion_id  INTEGER REFERENCES instituciones(id),
-- Cambiar UNIQUE simple → compound:
UNIQUE(institucion_id, nombre)   -- o el campo clave de cada tabla
```

### Modelo de dominio
```python
institucion_id: int | None = None
```

### Puerto (`IXxxRepository`)
Métodos de lectura colectiva reciben `institucion_id: int | None = None`.
```python
def listar_xxx(self, institucion_id: int | None = None) -> list[Xxx]: ...
```

### Repositorio SQLite
```python
# SELECT con filtro condicional
sql = "SELECT ... FROM tabla WHERE 1=1"
params = []
if institucion_id is not None:
    sql += " AND institucion_id = ?"
    params.append(institucion_id)
# INSERT con institucion_id
# UPDATE conserva el institucion_id original (no se cambia)
```

### Servicio
```python
def listar_xxx(self) -> list[Xxx]:
    from src.services.contexto_tenant import institucion_actual
    return self._repo.listar_xxx(institucion_id=institucion_actual())

@requiere_escritura
def crear_xxx(self, dto: NuevoXxxDTO) -> Xxx:
    from src.services.contexto_tenant import institucion_actual
    inst_id = self._resolver_institucion(None)  # o institucion_actual()
    obj = Xxx(**dto.model_dump(), institucion_id=inst_id)
    return self._repo.guardar_xxx(obj)
```

### Seed migration (idempotente)
```python
def _migrate_xxx_scoping(conn: sqlite3.Connection, inst_id: int) -> None:
    existing = {r[1] for r in conn.execute("PRAGMA table_info(xxx)").fetchall()}
    if "institucion_id" not in existing:
        conn.execute("ALTER TABLE xxx ADD COLUMN institucion_id INTEGER REFERENCES instituciones(id)")
    conn.execute("UPDATE xxx SET institucion_id = ? WHERE institucion_id IS NULL", (inst_id,))
```

---

## Archivos y responsabilidades por tarea

### T0 — Verificación R13 (solo lectura)
Verificar que las 8 tablas raíz ya scopeadas (`configuracion_anio`, `usuarios`,
`estudiantes`, `grupos`, `asignaturas`, `plantillas_franja`, `salas`) tienen
`verificar_pertenencia()` en sus servicios y filtro `institucion_id` en sus
repos. Reportar hallazgos en `progress/audit_r13.md`. Sin cambios de código.

---

### T1 — `areas_conocimiento`

**Schema:** añadir `institucion_id`, cambiar `nombre UNIQUE` → `UNIQUE(institucion_id, nombre)`.

**Modelo:** `AreaConocimiento` en `src/domain/models/infraestructura.py` — campo `institucion_id: int | None = None`.

**Puerto:** `IInfraestructuraRepository` (o su sección de áreas) — añadir parámetro `institucion_id: int | None = None` a `listar_areas()`.

**Repo:** `sqlite_infraestructura_repo.py`
- `listar_areas(institucion_id)` — WHERE filtro
- `guardar_area(area)` — incluir `institucion_id` en INSERT
- `actualizar_area(area)` — NOT cambiar `institucion_id`
- `eliminar_area(area_id)` — sin cambio
- `get_area_by_id(area_id)` — sin cambio

**Servicio:** `catalogo_academico_service.py`
- `listar_areas()` → pasa `institucion_actual()`
- `guardar_area()` → resuelve tenant y asigna
- `actualizar_area()` → chequea pertenencia antes de actualizar

**Seed:** `_migrate_areas_conocimiento_scoping(conn, inst_id)` — ALTER + backfill + llamada desde `_seed_institucion`.

---

### T2 — `plan_estudios`

**Schema:** añadir `institucion_id`, cambiar `UNIQUE(grado, asignatura_id)` → `UNIQUE(institucion_id, grado, asignatura_id)`.

**Modelo:** `PlanEstudios` en `infraestructura.py` — campo `institucion_id: int | None = None`.
También `NuevoPlanEstudiosDTO` — sin `institucion_id` (lo inyecta el servicio).

**Puerto:** `listar_plan_estudios(institucion_id: int | None = None)`, `get_plan_estudios_por_grado(grado, institucion_id)`.

**Repo:** `sqlite_infraestructura_repo.py` — añadir filtro `institucion_id` a SELECTs; incluir en INSERT.

**Servicio:** `plan_estudios_service.py`
- Añadir `_resolver_institucion()` (mismo patrón que `catalogo_academico_service.py`)
- `listar_plan_estudios()` → filtra por tenant
- `get_plan_estudios_por_grado(grado)` → filtra por tenant
- `agregar_plan_estudios(dto)` → inyecta `institucion_id`

**Seed:** `_migrate_plan_estudios_scoping(conn, inst_id)`.

---

### T3 — `categorias_observacion` + `plantillas_observacion`

**Schema:**
- `categorias_observacion`: añadir `institucion_id`, cambiar `nombre UNIQUE` → `UNIQUE(institucion_id, nombre)`.
- `plantillas_observacion`: añadir `institucion_id` (sin UNIQUE propio, scope heredado de la categoría).

**Modelos:** `CategoriaObservacion` y `PlantillaObservacion` en `src/domain/models/convivencia.py` — campo `institucion_id: int | None = None`.

**Puerto:** `IConvivenciaRepository` — añadir `institucion_id` a `listar_categorias()` y `listar_plantillas()`.

**Repo:** `sqlite_convivencia_repo.py` — filtro en SELECTs, incluir en INSERTs.

**Servicio:** `convivencia_service.py`
- `listar_categorias_observacion()` → filtra por tenant
- `crear_categoria_observacion(dto)` → inyecta tenant
- `listar_plantillas_observacion(...)` → filtra por tenant
- `crear_plantilla_observacion(dto)` → inyecta tenant

**Seed:** `_migrate_categorias_scoping(conn, inst_id)`.

---

### T4 — `acudientes`

**Schema:** añadir `institucion_id`, cambiar `numero_documento UNIQUE` → `UNIQUE(institucion_id, numero_documento)`.

**Modelo:** `Acudiente` en `src/domain/models/acudiente.py` — campo `institucion_id: int | None = None`.

**Puerto:** `IAcudienteRepository` — `listar(institucion_id: int | None = None)`, `buscar_por_documento(doc, institucion_id)`.

**Repo:** `sqlite_acudiente_repo.py` — filtro en SELECTs, incluir en INSERT.

**Servicio:** `acudiente_service.py`
- Añadir `_resolver_institucion()` (mismo patrón)
- Todos los listados filtran por tenant

**Seed:** `_migrate_acudientes_scoping(conn, inst_id)`.

---

### T5 — `franjas_reunion`

**Schema:** añadir `institucion_id`.

**Modelo:** `FranjaReunion` en `infraestructura.py` — campo `institucion_id: int | None = None`.

**Puerto:** `listar_franjas_reunion(institucion_id: int | None = None)`.

**Repo:** `sqlite_infraestructura_repo.py` — filtro en SELECT, incluir en INSERT/UPDATE.

**Servicio:** `restriccion_generacion_service.py`
- `listar_franjas_reunion()` → filtra por tenant
- `crear_franja_reunion(f)` → inyecta tenant

**Seed:** `_migrate_franjas_reunion_scoping(conn, inst_id)`.

---

### T6 — `configuracion_grado_institucion` (tabla nueva)

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS configuracion_grado_institucion (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    grado_id         INTEGER NOT NULL REFERENCES grados(id) ON DELETE CASCADE,
    institucion_id   INTEGER NOT NULL REFERENCES instituciones(id),
    min_estudiantes  INTEGER NOT NULL DEFAULT 0 CHECK(min_estudiantes >= 0),
    max_estudiantes  INTEGER NOT NULL DEFAULT 40 CHECK(max_estudiantes >= 1),
    horas_semanales  INTEGER NOT NULL DEFAULT 0 CHECK(horas_semanales >= 0),
    UNIQUE(grado_id, institucion_id)
)
```
Añadir índice: `idx_config_grado_inst ON configuracion_grado_institucion(institucion_id)`.

**Modelo:** `ConfiguracionGradoInstitucion` en `infraestructura.py`.

**Puerto:** `IInfraestructuraRepository` — `get_config_grado(grado_id, institucion_id) -> ConfiguracionGradoInstitucion | None`, `upsert_config_grado(cfg) -> ConfiguracionGradoInstitucion`.

**Repo:** `sqlite_infraestructura_repo.py` — implementar ambos métodos.

**Servicio:** `plan_estudios_service.py` — `get_config_grado(grado_num, institucion_id)` retorna la config por institución si existe, o crea un `ConfiguracionGradoInstitucion` con defaults de `grados`.

**Seed:** `_seed_config_grado_institucion(conn, inst_id)` — copia valores de `grados` (min/max/horas) → `configuracion_grado_institucion` para la institución #1. Idempotente (INSERT OR IGNORE).

---

### T7 — `auditoria` + `audit_log`

**Schema:**
- `auditoria`: añadir `institucion_id INTEGER REFERENCES instituciones(id)`. Campo informacional.
- `audit_log`: idem.

> ⚠️ El `institucion_id` NO entra en el payload del hash SHA-256. El cálculo
> del hash sigue siendo `SHA256(hash_previo || payload_sin_institucion_id)`.

**Modelos:** `EventoSesion` y `RegistroCambio` en `auditoria.py` — campo `institucion_id: int | None = None`.

**Puerto:** `IAuditoriaRepository` — `registrar_evento` y `registrar_cambio` ya reciben los modelos; el `institucion_id` llega dentro del objeto si el llamador lo inyecta.

**Repo:** `sqlite_auditoria_repo.py` — incluir `institucion_id` en INSERTs. No cambiar hashes.

**Servicio:** `auditoria_service.py` — sin cambios de API. El `institucion_id` lo inyectan los servicios llamadores (login, usuario_service, etc.) via la sesión. Añadir helper `_get_institucion_actual()` en servicios que registran eventos y cambios.

> Backfill de `institucion_id` en auditoria/audit_log: desde `usuarios.institucion_id`
> WHERE `auditoria.usuario_id = usuarios.id` (o NULL si no hay match). JOIN simple.

**Seed:** `_migrate_auditoria_scoping(conn, inst_id)` — ALTER + backfill via JOIN.

---

### T8 — Seed de catálogos estándar para nuevas instituciones

Función `_seed_catalogos_institucion(conn, institucion_id)` en `seed.py`:

**Áreas estándar colombianas** (R8, 12 áreas, Ley 115 Art. 23):
```python
AREAS_ESTANDAR = [
    ("Matemáticas", "MAT"), ("Ciencias Naturales y Educación Ambiental", "NAT"),
    ("Ciencias Sociales, Historia, Geografía y C. Económicas", "SOC"),
    ("Lenguaje", "LEN"), ("Educación Física, Recreación y Deportes", "EFI"),
    ("Educación Artística y Cultural", "ART"),
    ("Tecnología e Informática", "TEC"),
    ("Educación Ética y en Valores Humanos", "ETI"),
    ("Ciencias Económicas y Políticas", "CEP"),
    ("Filosofía", "FIL"), ("Idioma Extranjero", "IDI"),
    ("Educación Religiosa", "REL"),
]
```
INSERT OR IGNORE para idempotencia.

**Categorías de observación base** (4):
```python
CATEGORIAS_BASE = [
    ("Comportamiento positivo", True),
    ("Convivencia y normas", True),
    ("Académico", False),
    ("Responsabilidad y actitud", False),
]
```

Llamar `_seed_catalogos_institucion(conn, inst_id)` desde `_seed_institucion(conn)` después del backfill.

---

## Alternativa descartada

**Catálogo global con flag `is_default` y herencia por institución.**

Se descartó por R8 y la decisión de David: catálogos 100% propios. Cada institución tiene sus registros; no hay herencia ni fallback al catálogo global. Esto simplifica las queries (sin UNION ni LEFT JOIN al catálogo global) y permite que cada institución personalice completamente sus catálogos.

---

## Notas de compatibilidad

- Las queries que actualmente leen `areas_conocimiento` sin filtro seguirán funcionando porque con un solo tenant en BD los resultados son idénticos.
- Los tests de integración existentes usan la BD de test (`seed_test`) con una sola institución; el filtro `WHERE institucion_id = 1` retorna los mismos registros.
- `grados` sigue siendo global (no cambia). La tabla puente `configuracion_grado_institucion` es aditiva.
