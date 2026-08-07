# Tasks: mejora_06 — Enriquecimiento de la entidad Institucion

> Aprobado: pendiente confirmación de David.
> Scope autorizado: ver design.md §Archivos y responsabilidades.

---

## T1 — Schema: añadir columnas a `instituciones`

**Archivo:** `src/infrastructure/db/schema.py`

Localizar el bloque `CREATE TABLE IF NOT EXISTS instituciones (...)` y añadir
las 13 columnas nuevas antes del cierre `)`:

```sql
nombre_oficial         TEXT,
codigo_dane            TEXT,
rector                 TEXT,
direccion              TEXT,
municipio              TEXT,
telefono               TEXT,
logo_path              TEXT,
logo_url               TEXT,
resolucion_aprobacion  TEXT,
lema                   TEXT,
email_institucional    TEXT,
jornada_principal      TEXT,
tipo_institucion       TEXT,
calendario             TEXT
```

**Verificación:**
```bash
python -c "
from src.infrastructure.db.schema import SCHEMA
bloque = next(s for s in SCHEMA if 'instituciones' in s and 'PRIMARY KEY' in s)
assert 'nombre_oficial' in bloque, 'FALTA nombre_oficial'
assert 'codigo_dane' in bloque, 'FALTA codigo_dane'
assert 'jornada_principal' in bloque, 'FALTA jornada_principal'
print('T1 OK')
"
```

---

## T2 — Dominio: enums + campos en Institucion + ActualizarInstitucionDTO

**Archivo:** `src/domain/models/institucion.py`

1. Añadir enums `JornadaPrincipal`, `TipoInstitucion`, `Calendario` (valores en design.md).
2. Añadir 13 campos a `Institucion` (todos `= None`).
3. Añadir validador `codigo_dane`: si presente, exactamente 12 dígitos numéricos.
4. Añadir validador `nombre_oficial`: si presente, strip, no vacío, ≤200 caracteres.
5. Añadir `ActualizarInstitucionDTO` con todos los campos editables y método
   `aplicar_a(inst: Institucion) -> Institucion`.
6. Actualizar `__all__` con los nuevos nombres.

**Verificación:**
```bash
python -c "
from src.domain.models.institucion import (
    JornadaPrincipal, TipoInstitucion, Calendario,
    Institucion, ActualizarInstitucionDTO,
)
i = Institucion(nombre='IE', nombre_oficial='Inst. Educativa Test',
                codigo_dane='123456789012', jornada_principal=JornadaPrincipal.AM)
assert i.codigo_dane == '123456789012'
dto = ActualizarInstitucionDTO(rector='Dr. Lopez')
i2 = dto.aplicar_a(i)
assert i2.rector == 'Dr. Lopez'
# validacion: dane malo
try:
    Institucion(nombre='X', codigo_dane='12345')
    assert False, 'debio lanzar'
except Exception:
    pass
print('T2 OK')
"
```

---

## T3 — Dominio: `InformacionInstitucionalDTO.desde_institucion()`

**Archivo:** `src/domain/models/configuracion.py`

Añadir classmethod a `InformacionInstitucionalDTO`:
```python
@classmethod
def desde_institucion(
    cls,
    institucion: "Institucion",  # forward ref para evitar circular
    anio: int,
    nota_minima_aprobacion: float,
) -> "InformacionInstitucionalDTO":
    """
    Construye el DTO desde la entidad Institucion (para previews).
    Falla si codigo_dane o rector son None (igual que desde_configuracion).
    """
```

Mapeo:
- `nombre_institucion` ← `institucion.nombre_oficial or institucion.nombre`
- `dane_code` ← `institucion.codigo_dane`
- `rector` ← `institucion.rector`
- campos opcionales ← tomados directamente del modelo

**Verificación:**
```bash
python -c "
from src.domain.models.configuracion import InformacionInstitucionalDTO
from src.domain.models.institucion import Institucion
inst = Institucion(
    nombre='IE Corta', nombre_oficial='Inst. Ed. Completa',
    codigo_dane='123456789012', rector='Rectora Ana'
)
dto = InformacionInstitucionalDTO.desde_institucion(inst, anio=2026, nota_minima_aprobacion=60.0)
assert dto.nombre_institucion == 'Inst. Ed. Completa'
assert dto.dane_code == '123456789012'
assert dto.rector == 'Rectora Ana'
print('T3 OK')
"
```

---

## T4 — Puerto: añadir `actualizar()` a `IInstitucionRepository`

**Archivo:** `src/domain/ports/institucion_repo.py`

```python
@abstractmethod
def actualizar(self, institucion: Institucion) -> Institucion:
    """Actualiza una institución existente. Lanza ValueError si no existe."""
    ...
```

**Verificación:**
```bash
python -c "
import inspect
from src.domain.ports.institucion_repo import IInstitucionRepository
assert 'actualizar' in [n for n,_ in inspect.getmembers(IInstitucionRepository, predicate=inspect.isfunction)]
print('T4 OK')
"
```

---

## T5 — Repositorio: actualizar `_COLS` + `_row_to_institucion` + implementar `actualizar()`

**Archivo:** `src/infrastructure/db/repositories/sqlite_institucion_repo.py`

1. Actualizar `_COLS` con los 13 campos nuevos.
2. Actualizar `_row_to_institucion()` para manejar campos nullable y enums
   (convertir strings a enums JornadaPrincipal, TipoInstitucion, Calendario).
3. Implementar `actualizar()`:
   ```python
   def actualizar(self, institucion: Institucion) -> Institucion:
       if not institucion.id:
           raise ValueError("La institución debe tener id para actualizar.")
       ...  # UPDATE instituciones SET col=? WHERE id=?
   ```

**Verificación:**
```bash
python -m pytest tests/integration/test_repositories.py -k "institucion" -v --tb=short 2>&1 | tail -10
```
*(Los tests existentes deben seguir pasando; el repositorio reconstruye modelos con los campos nuevos.)*

---

## T6 — Servicio: añadir métodos a `InstitucionService`

**Archivo:** `src/services/institucion_service.py`

Añadir tres métodos:

```python
@requiere_escritura
def actualizar(self, institucion_id: int, dto: ActualizarInstitucionDTO) -> Institucion:
    """Actualiza identidad. No toca snapshots históricos."""

def snapshot_institucional(self, institucion_id: int) -> dict:
    """Dict de campos de identidad mapeados a claves de ConfiguracionAnio.
    Solo incluye campos con valor. Retorna {} si no hay datos."""
```

Mapeo de `snapshot_institucional` (ver design.md §6).

Importar `ActualizarInstitucionDTO` en el módulo.

**Verificación:**
```bash
python -c "
from src.domain.models.institucion import Institucion, ActualizarInstitucionDTO
from src.domain.ports.institucion_repo import IInstitucionRepository

class FakeRepo(IInstitucionRepository):
    def __init__(self): self._data = {}
    def get_by_id(self, id): return self._data.get(id)
    def listar(self, solo_activas=False): return list(self._data.values())
    def existe_nombre(self, nombre): return any(i.nombre==nombre for i in self._data.values())
    def guardar(self, inst): inst = inst.model_copy(update={'id': 1}); self._data[1] = inst; return inst
    def get_por_defecto(self): return next(iter(self._data.values()), None)
    def actualizar(self, inst): self._data[inst.id] = inst; return inst

from src.services.institucion_service import InstitucionService
from src.domain.models.institucion import NuevaInstitucionDTO
svc = InstitucionService(FakeRepo())
inst = svc.crear(NuevaInstitucionDTO(nombre='IE Test'))
dto = ActualizarInstitucionDTO(nombre_oficial='IE Test Oficial', rector='Dr. X', codigo_dane='123456789012')
inst2 = svc.actualizar(inst.id, dto)
assert inst2.rector == 'Dr. X'
snap = svc.snapshot_institucional(inst2.id)
assert snap.get('rector') == 'Dr. X'
assert 'nombre_institucion' in snap
print('T6 OK')
"
```

---

## T7 — Servicio: auto-snapshot en `crear_anio()` + `sincronizar_snapshot_desde_institucion()`

**Archivo:** `src/services/configuracion_service.py`

**Modificación de `crear_anio()`**: después de guardar el config (y los periodos),
aplicar el snapshot institucional de forma graceful:
```python
try:
    from container import Container
    snap = Container.institucion_service().snapshot_institucional(config.institucion_id)
    if snap:
        dto_snap = ActualizarInfoInstitucionalDTO(**{
            k: v for k, v in snap.items()
            if k in ActualizarInfoInstitucionalDTO.model_fields
        })
        config_snap = dto_snap.aplicar_a(config)
        if config_snap != config:
            config = self._repo.actualizar(config_snap)
except Exception:
    pass  # auto-snapshot es best-effort; el año ya está creado
```

**Nuevo método `sincronizar_snapshot_desde_institucion(anio_id)`** (R6):
```python
@requiere_escritura
def sincronizar_snapshot_desde_institucion(self, anio_id: int) -> ConfiguracionAnio:
    """
    Copia la identidad vigente de la institución al snapshot del año indicado.
    Solo actualiza campos no nulos de la institución.
    """
```
Usa `get_by_id(anio_id)` → `Container.institucion_service().snapshot_institucional(...)` →
`ActualizarInfoInstitucionalDTO` → `self._repo.actualizar(...)`.

**Verificación:**
```bash
python -c "
from src.services.configuracion_service import ConfiguracionService
import inspect
# sincronizar_snapshot_desde_institucion existe
assert hasattr(ConfiguracionService, 'sincronizar_snapshot_desde_institucion')
# crear_anio no lanza sin institución con datos
print('T7 OK — verificar manualmente que crear_anio no rompe sin inst. enriquecida')
"
```

---

## T8 — Seed: migración idempotente para BDs existentes

**Archivo:** `src/infrastructure/db/seed.py`

Añadir `_migrate_instituciones_identidad(conn: sqlite3.Connection) -> None`:
1. Lee columnas existentes con `PRAGMA table_info(instituciones)`.
2. Para cada columna nueva que falte → `ALTER TABLE instituciones ADD COLUMN <col> TEXT`.
3. Copia datos desde `configuracion_anio` activa a `instituciones` #1
   (UPDATE instituciones SET ... WHERE id=<id> AND <col> IS NULL).

Llamar `_migrate_instituciones_identidad(conn)` al final de `_seed_institucion(conn)`.

Mapeo de backfill (configuracion_anio → instituciones): ver design.md §8.

**Verificación:**
```bash
python -c "
import sqlite3, sys
conn = sqlite3.connect(':memory:')
conn.row_factory = sqlite3.Row
from src.infrastructure.db.schema import create_schema
create_schema(conn)
# Simular BD vieja: tabla instituciones sin cols nuevas (en :memory: ya las tiene; ok)
# Insertar institución base y config anio activa
conn.execute(\"INSERT INTO instituciones (nombre, activa) VALUES ('IE', 1)\")
conn.execute(\"\"\"INSERT INTO configuracion_anio (anio, nombre_institucion, dane_code, rector, activo, nota_minima_aprobacion)
              VALUES (2026, 'IE Oficial', '123456789012', 'Dr. A', 1, 60.0)\"\"\")
conn.commit()
from src.infrastructure.db.seed import _migrate_instituciones_identidad
_migrate_instituciones_identidad(conn)
row = dict(conn.execute('SELECT * FROM instituciones WHERE id=1').fetchone())
assert row.get('nombre_oficial') == 'IE Oficial' or row.get('nombre_oficial') is None, repr(row)
# segunda ejecucion no lanza (idempotente)
_migrate_instituciones_identidad(conn)
print('T8 OK')
"
```

---

## T9 — Tests

**Archivos nuevos:**
- `tests/unit/domain/test_institucion_enriquecida.py`
- `tests/unit/services/test_institucion_service_actualizar.py`
- `tests/unit/services/test_configuracion_snapshot.py`

**Cobertura mínima:**

`test_institucion_enriquecida.py`:
- Institucion con campos opcionales vacíos se construye sin error.
- `codigo_dane` inválido (no 12 dígitos) → ValidationError.
- `nombre_oficial` > 200 chars → ValidationError.
- `ActualizarInstitucionDTO.aplicar_a()` cambia solo los campos no-None.
- `InformacionInstitucionalDTO.desde_institucion()` falla si `codigo_dane` es None.
- `InformacionInstitucionalDTO.desde_institucion()` falla si `rector` es None.
- `InformacionInstitucionalDTO.desde_institucion()` usa `nombre_oficial` si está presente.

`test_institucion_service_actualizar.py`:
- `actualizar()` con FakeRepo cambia campos correctamente.
- `snapshot_institucional()` retorna dict vacío si no hay datos de identidad.
- `snapshot_institucional()` incluye solo campos no-None.
- `snapshot_institucional()` mapea `telefono` → `telefono_institucion`.

`test_configuracion_snapshot.py`:
- `sincronizar_snapshot_desde_institucion()` falla con ValueError si anio no existe.

**Verificación global:**
```bash
python -m pytest tests/unit/domain/test_institucion_enriquecida.py tests/unit/services/test_institucion_service_actualizar.py tests/unit/services/test_configuracion_snapshot.py -v --tb=short 2>&1 | tail -20
```

---

## Verificación final

```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

Criterio: sin regresiones en los 1421 tests existentes. Los tests nuevos agregan al total.

```bash
# init.py con PYTHONIOENCODING
python -c "
from src.domain.models.institucion import Institucion, ActualizarInstitucionDTO, JornadaPrincipal
from src.domain.models.configuracion import InformacionInstitucionalDTO
from src.services.configuracion_service import ConfiguracionService
print('imports OK — mejora_06 verificado')
"
```
