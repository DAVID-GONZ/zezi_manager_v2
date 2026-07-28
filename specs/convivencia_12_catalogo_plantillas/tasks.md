# convivencia_12_catalogo_plantillas — Tasks
> ⚠️ TOCA BD — puerta de aprobación de David antes del implementer.
> Prerequisito: convivencia_09 y convivencia_11 DONE.

## Objetivo
Crear la tabla `plantillas_observacion`, el modelo, el puerto, el repo y
el seed de plantillas predefinidas. Añadir la opción "usar plantilla" en
el formulario de observación.

## Scope
```
src/infrastructure/db/schema.py
src/domain/models/convivencia.py
src/domain/ports/convivencia_repo.py
src/infrastructure/db/repositories/sqlite_convivencia_repo.py
src/infrastructure/db/seed.py
src/services/convivencia_service.py
src/interface/pages/convivencia/observaciones.py
tests/
```

## Diseño

### Tabla nueva
```sql
CREATE TABLE IF NOT EXISTS plantillas_observacion (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    texto        TEXT    NOT NULL,
    categoria_id INTEGER REFERENCES categorias_observacion(id) ON DELETE SET NULL,
    uso_count    INTEGER NOT NULL DEFAULT 0,
    activa       BOOLEAN NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_plantillas_obs_categoria
    ON plantillas_observacion(categoria_id);
CREATE INDEX IF NOT EXISTS ix_plantillas_obs_activa
    ON plantillas_observacion(activa);
```

### Modelo de dominio
```python
class PlantillaObservacion(BaseModel):
    id:           int | None = None
    texto:        str
    categoria_id: int | None = None
    uso_count:    int        = 0
    activa:       bool       = True

class NuevaPlantillaDTO(BaseModel):
    texto:        str
    categoria_id: int | None = None
```

### Métodos nuevos en `IConvivenciaRepository`
```python
def listar_plantillas(self, categoria_id: int | None = None, solo_activas: bool = True) -> list[PlantillaObservacion]
def get_plantilla(self, plantilla_id: int) -> PlantillaObservacion | None
def guardar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion
def actualizar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion
def incrementar_uso_plantilla(self, plantilla_id: int) -> None
```

### Seed predefinido
Plantillas asociadas a las categorías del seed_09. Ejemplos (5-8 plantillas):

| texto                                               | categoria (nombre)       |
|-----------------------------------------------------|--------------------------|
| Demuestra buen desempeño y compromiso en clase.     | Comportamiento positivo  |
| Cumple con las normas de convivencia del aula.      | Convivencia y normas     |
| Entrega oportuna de trabajos y tareas.              | Responsabilidad          |
| Participa activamente en las actividades.           | Participación            |
| Presenta dificultades en el respeto a compañeros.  | Comportamiento negativo  |
| Incumplimiento reiterado de normas del aula.        | Convivencia y normas     |

Buscar `categoria_id` por nombre antes de insertar (join idempotente).

### UI: "Usar plantilla"
En el `form_dialog` de nueva observación añadir:
- Botón "Usar plantilla" que abre un segundo `ui.dialog` (selector de plantilla).
- El selector muestra `listar_plantillas(categoria_id=categoria_seleccionada)`.
- Al elegir una plantilla, pre-rellena el campo `texto` del formulario principal
  y llama `incrementar_uso_plantilla`.

Cuando la observación se crea desde plantilla, `origen="plantilla"` se establece
en el servicio automáticamente (la UI no lo maneja directamente).

### Método nuevo en `ConvivenciaService`
```python
def listar_plantillas(self, categoria_id: int | None = None) -> list[PlantillaObservacion]
def registrar_observacion_desde_plantilla(
    self,
    dto: NuevaObservacionDTO,
    plantilla_id: int,
    usuario_id: int | None = None,
    usuario_rol: str | None = None,
) -> ObservacionPeriodo
```
`registrar_observacion_desde_plantilla` llama `registrar_observacion` con `dto.origen="plantilla"`
y luego `incrementar_uso_plantilla(plantilla_id)`.

## Tareas

### T1 — `schema.py`: añadir tabla e índices
### T2 — `convivencia.py`: añadir `PlantillaObservacion` y `NuevaPlantillaDTO`
### T3 — `convivencia_repo.py`: añadir 5 métodos al puerto
### T4 — `sqlite_convivencia_repo.py`: implementar los 5 métodos
- `incrementar_uso_plantilla`: `UPDATE plantillas_observacion SET uso_count = uso_count + 1 WHERE id=?`.
### T5 — `seed.py`: añadir seed de plantillas
- Buscar `categoria_id` por nombre de categoría antes de insertar.
- Usar `_get_or_insert` buscando por `texto` (idempotente).
### T6 — `convivencia_service.py`: añadir `listar_plantillas` y `registrar_observacion_desde_plantilla`
### T7 — `observaciones.py`: botón "Usar plantilla" en `form_dialog`
**Verificación**: `check_design`, `check_imports --layer interface`
### T8 — Tests
- `test_listar_plantillas_por_categoria` — integración.
- `test_registrar_observacion_desde_plantilla_incrementa_uso` — integración.
- `test_listar_plantillas_servicio` — unitario.

## criterio_done
- [ ] Tabla `plantillas_observacion` existe en schema.
- [ ] `PlantillaObservacion` importable desde `src.domain.models.convivencia`.
- [ ] 5 métodos del puerto implementados en repo.
- [ ] 6+ plantillas en seed (idempotentes).
- [ ] Servicio expone `listar_plantillas` y `registrar_observacion_desde_plantilla`.
- [ ] UI muestra selector de plantillas al crear observación.
- [ ] Tests nuevos verdes.
- [ ] `init.py --quick` → ENTORNO OK.
