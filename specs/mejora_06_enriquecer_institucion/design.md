# Design: mejora_06 — Enriquecimiento de la entidad Institucion

## Resumen de cambios

Mueve la identidad institucional de `configuracion_anio` (fuente de verdad actual) a la entidad `Institucion` (fuente de verdad permanente). `configuracion_anio` retiene esos campos como **snapshot histórico de solo lectura** para boletines.

---

## Archivos y responsabilidades

### 1. `src/infrastructure/db/schema.py`
Amplía `CREATE TABLE IF NOT EXISTS instituciones` con 13 columnas nuevas. Cubre instalaciones nuevas. Para BDs existentes, la migración la hace seed.py.

Columnas añadidas:
```sql
nombre_oficial         TEXT,           -- nombre completo para boletines
codigo_dane            TEXT,           -- 12 dígitos numéricos (validado en modelo)
rector                 TEXT,
direccion              TEXT,
municipio              TEXT,
telefono               TEXT,
logo_path              TEXT,
logo_url               TEXT,
resolucion_aprobacion  TEXT,
lema                   TEXT,
email_institucional    TEXT,
jornada_principal      TEXT,           -- 'AM' | 'PM' | 'UNICA'
tipo_institucion       TEXT,           -- 'publica' | 'privada'
calendario             TEXT            -- 'A' | 'B'
```

> Nota: `logo_url` ya existe en el modelo `ConfiguracionAnio` pero no en la
> tabla `configuracion_anio`; ese drift es pre-existente y está fuera de
> alcance de este paso.

---

### 2. `src/domain/models/institucion.py`
Tres enums nuevos + campos en `Institucion` + `ActualizarInstitucionDTO`.

**Enums:**
```python
class JornadaPrincipal(str, Enum):
    AM    = "AM"
    PM    = "PM"
    UNICA = "UNICA"

class TipoInstitucion(str, Enum):
    PUBLICA  = "publica"
    PRIVADA  = "privada"

class Calendario(str, Enum):
    A = "A"
    B = "B"
```

**Nuevos campos en `Institucion`** (todos opcionales para no romper creación existente):
`nombre_oficial`, `codigo_dane`, `rector`, `direccion`, `municipio`, `telefono`,
`logo_path`, `logo_url`, `resolucion_aprobacion`, `lema`, `email_institucional`,
`jornada_principal: JornadaPrincipal | None`, `tipo_institucion: TipoInstitucion | None`,
`calendario: Calendario | None`.

**Validadores:**
- `codigo_dane`: si presente, debe ser exactamente 12 dígitos numéricos.
- `nombre_oficial`: si presente, no vacío, ≤200 caracteres.

**`ActualizarInstitucionDTO`**: refleja todos los campos nuevos + los existentes
editables (`nombre`, `nit`). Método `aplicar_a(inst: Institucion) -> Institucion`.

---

### 3. `src/domain/models/configuracion.py` *(adición al scope)*
Agregar factory `InformacionInstitucionalDTO.desde_institucion()`:
```python
@classmethod
def desde_institucion(
    cls, institucion: Institucion, anio: int, nota_minima_aprobacion: float
) -> InformacionInstitucionalDTO:
```
Falla si `codigo_dane` o `rector` son None/vacíos (misma guarda que `desde_configuracion`).
Mapeo: `nombre_oficial or nombre` → `nombre_institucion`, `codigo_dane` → `dane_code`.

> Justificación de adición al scope: `InformacionInstitucionalDTO` solo puede
> definirse en `configuracion.py` porque allí ya están los imports y el
> resto de la clase. Crearlo en otro módulo generaría una importación circular
> (configuracion → institucion → configuracion).

---

### 4. `src/domain/ports/institucion_repo.py`
Añadir método abstracto:
```python
@abstractmethod
def actualizar(self, institucion: Institucion) -> Institucion:
    """Actualiza los campos de una institución existente. Lanza si no existe."""
    ...
```

---

### 5. `src/infrastructure/db/repositories/sqlite_institucion_repo.py`
- Actualizar `_COLS` para incluir los 13 campos nuevos.
- Actualizar `_row_to_institucion()` para manejar los nuevos campos y los enums.
- Implementar `actualizar()` con `UPDATE instituciones SET ... WHERE id = ?`.

---

### 6. `src/services/institucion_service.py`
Añadir:

```python
def actualizar(self, institucion_id: int, dto: ActualizarInstitucionDTO) -> Institucion:
    """Actualiza identidad y clasificación de la institución. No altera snapshots históricos."""

def snapshot_institucional(self, institucion_id: int) -> dict:
    """Dict con campos de identidad mapeados al esquema de configuracion_anio.
    Retorna dict vacío si la institución no tiene datos de identidad."""

def sincronizar_snapshot_anio_activo(self, anio_id: int) -> ConfiguracionAnio:
    """Copia identidad vigente de la institución al snapshot del año indicado (R6)."""
```

`snapshot_institucional()` mapea:
```python
{
    "nombre_institucion": inst.nombre_oficial or inst.nombre,
    "dane_code":          inst.codigo_dane,
    "rector":             inst.rector,
    "direccion":          inst.direccion,
    "municipio":          inst.municipio,
    "telefono_institucion": inst.telefono,
    "logo_path":          inst.logo_path,
    "resolucion_aprobacion": inst.resolucion_aprobacion,
}
```
Solo incluye en el dict los campos con valor no-None.

---

### 7. `src/services/configuracion_service.py`
Modificar `crear_anio()` para auto-snapshot:
```python
# Después de crear el config y guardar los periodos:
try:
    snapshot = Container.institucion_service().snapshot_institucional(
        config.institucion_id
    )
    if snapshot:
        from src.domain.models.configuracion import ActualizarInfoInstitucionalDTO
        dto_snap = ActualizarInfoInstitucionalDTO(**snapshot)
        config_actualizada = dto_snap.aplicar_a(config)
        # solo guardar si hubo cambios reales
        if config_actualizada != config:
            config = self._repo.guardar_info_institucional(config.id, config_actualizada)
except Exception:
    pass  # auto-snapshot falla gracefully; el año se creó correctamente
```

Alternativamente (más limpio): delegar al repo una actualización directa en SQL, si
`IConfiguracionRepository` tiene `guardar_info_institucional`. Verificar si existe.

---

### 8. `src/infrastructure/db/seed.py`
Nueva función `_migrate_instituciones_identidad(conn)`:
- Lee `PRAGMA table_info(instituciones)` para obtener columnas existentes.
- Agrega via `ALTER TABLE instituciones ADD COLUMN ...` solo las columnas faltantes.
- Copia datos desde `configuracion_anio` activa → `instituciones` #1 (solo si NULL destino).
- Llamada desde `_seed_institucion()`, idempotente.

Mapeo para el backfill (configuracion_anio → instituciones):
```
nombre_institucion  → nombre_oficial
dane_code           → codigo_dane
rector              → rector
direccion           → direccion
municipio           → municipio
telefono_institucion→ telefono
logo_path           → logo_path
resolucion_aprobacion→ resolucion_aprobacion
```

---

## Alternativa descartada

**Añadir una tabla separada `identidad_institucional` 1-a-1 con `instituciones`.**

Pros: no altera tabla existente.
Cons: requiere JOIN en cada lectura, aumenta complejidad sin beneficio real dado el
escenario de máximo ~100 instituciones. Dado que SQLite soporta `ALTER TABLE ADD COLUMN`
y el proyecto es pre-producción, enriquecer la tabla existente es más directo.

---

## Notas de compatibilidad

- `InformacionInstitucionalDTO.desde_configuracion()` no se modifica → R9 garantizado.
- Todos los campos nuevos tienen `default=None` → `Institucion(**datos_viejos)` no falla.
- `InstitucionResumenDTO` no cambia; solo añade `nombre_oficial` para display si se desea.
- Tests existentes de `Institucion` siguen pasando sin cambios.
