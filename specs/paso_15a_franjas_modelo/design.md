# paso_15a_franjas_modelo — design

## Esquema (schema.py, módulo 2 — Infraestructura académica)

Insertar **después** de `escenarios_horario` (línea ~125) y **antes** de
`areas_conocimiento`, manteniendo orden FK. Dos tablas nuevas:

```sql
CREATE TABLE IF NOT EXISTS plantillas_franja (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT    NOT NULL UNIQUE,
    jornada      TEXT    NOT NULL DEFAULT 'UNICA'
                 CHECK(jornada IN ('AM', 'PM', 'UNICA')),
    dias_activos TEXT    NOT NULL DEFAULT 'Lunes,Martes,Miércoles,Jueves,Viernes',
    activa       INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
)

CREATE TABLE IF NOT EXISTS franjas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    plantilla_id INTEGER NOT NULL,
    orden        INTEGER NOT NULL CHECK(orden >= 1),
    hora_inicio  TIME    NOT NULL,
    hora_fin     TIME    NOT NULL,
    tipo         TEXT    NOT NULL DEFAULT 'lectiva'
                 CHECK(tipo IN ('lectiva', 'descanso', 'almuerzo')),
    etiqueta     TEXT,
    UNIQUE(plantilla_id, orden),
    CHECK(hora_inicio < hora_fin),
    FOREIGN KEY(plantilla_id) REFERENCES plantillas_franja(id) ON DELETE CASCADE
)
```

Índices (bloque de índices, junto a `idx_escenario_activo_unico`, ~línea 1005):

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_plantilla_activa_jornada
    ON plantillas_franja(jornada) WHERE activa = 1;
CREATE INDEX IF NOT EXISTS idx_franjas_plantilla ON franjas(plantilla_id);
```

> El índice parcial `WHERE activa = 1` replica el patrón de exclusividad de
> escenario activo: garantiza R2 a nivel BD sin triggers. No hace falta
> micro-migración (`ALTER TABLE`) porque son tablas nuevas creadas por `SCHEMA`.

## Dominio (infraestructura.py)

`DIAS_VALIDOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]`
(constante de módulo; reutilizar el enum `DiaSemana` si ya existe — verificar).

```python
class Franja(BaseModel):
    id: int | None = None
    plantilla_id: int
    orden: int                      # ge=1
    hora_inicio: str                # "HH:MM"
    hora_fin: str
    tipo: str = "lectiva"           # lectiva|descanso|almuerzo
    etiqueta: str | None = None
    # validators: orden>=1; tipo in {...}; hora_inicio < hora_fin (comparar "HH:MM")
    @property
    def es_lectiva(self) -> bool:
        return self.tipo == "lectiva"

class PlantillaFranja(BaseModel):
    id: int | None = None
    nombre: str                     # strip + no vacío
    jornada: str = "UNICA"          # AM|PM|UNICA
    dias_activos: list[str]         # subset de DIAS_VALIDOS
    activa: bool = False
    created_at: str | None = None
    # validator dias_activos: cada día en DIAS_VALIDOS, lista no vacía
    # En repo: persistir dias_activos como CSV join(','); al leer, split(',')

class NuevaPlantillaFranjaDTO(BaseModel):
    nombre: str
    jornada: str = "UNICA"
    dias_activos: list[str]
    def to_plantilla(self) -> PlantillaFranja: ...

class NuevaFranjaDTO(BaseModel):
    plantilla_id: int
    orden: int
    hora_inicio: str
    hora_fin: str
    tipo: str = "lectiva"
    etiqueta: str | None = None
    def to_franja(self) -> Franja: ...
```

Actualizar `__all__` con: `PlantillaFranja`, `Franja`, `NuevaPlantillaFranjaDTO`,
`NuevaFranjaDTO`, `DIAS_VALIDOS`.

> **Comparación de horas como string "HH:MM"** funciona lexicográficamente
> (igual que ya hace `analizar_lote._solapan`). No introducir `datetime.time` en
> el dominio para mantener consistencia con el resto del modelo de horarios.

## Puerto (infraestructura_repo.py)

Añadir a `IInfraestructuraRepository` (métodos abstractos):

```python
# Plantillas
def crear_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja: ...
def get_plantilla_franja(self, plantilla_id: int) -> PlantillaFranja | None: ...
def listar_plantillas_franja(self) -> list[PlantillaFranja]: ...
def get_plantilla_activa(self, jornada: str) -> PlantillaFranja | None: ...
def actualizar_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja: ...
def activar_plantilla_franja(self, plantilla_id: int) -> None: ...
def eliminar_plantilla_franja(self, plantilla_id: int) -> bool: ...
# Franjas
def crear_franja(self, f: Franja) -> Franja: ...
def listar_franjas(self, plantilla_id: int) -> list[Franja]: ...
def actualizar_franja(self, f: Franja) -> Franja: ...
def eliminar_franja(self, franja_id: int) -> bool: ...
def reemplazar_franjas(self, plantilla_id: int, franjas: list[Franja]) -> int: ...
```

> Al agregar métodos abstractos, **todos los `FakeInfraRepo`** de los tests
> (`test_horario_service.py`, `test_horario_lote.py`) dejan de instanciarse.
> Añadir stubs que devuelvan `None`/`[]`/`0`/`True` — igual que se hizo con
> `crear_bloques_masivo` en paso_14f. Es la regresión más probable; revisar.

## Repositorio (sqlite_infraestructura_repo.py)

- Mapear `dias_activos` ↔ CSV: al insertar `",".join(p.dias_activos)`; al leer
  `row["dias_activos"].split(",")`.
- `get_plantilla_activa(jornada)`: `SELECT ... WHERE jornada=? AND activa=1`.
- `activar_plantilla_franja(id)` — transacción:
  ```sql
  UPDATE plantillas_franja SET activa=0
     WHERE jornada=(SELECT jornada FROM plantillas_franja WHERE id=:id);
  UPDATE plantillas_franja SET activa=1 WHERE id=:id;
  ```
  (mismo patrón que `activar_escenario`).
- `reemplazar_franjas(plantilla_id, franjas)` — transacción:
  `DELETE FROM franjas WHERE plantilla_id=:id` + `executemany` INSERT; devuelve nº
  insertadas. Reutilizable por la futura UI de edición de rejilla.
- `listar_franjas`: `ORDER BY orden`.

## Servicio (infraestructura_service.py)

Fachada con tipos simples (la interfaz nunca importa modelos de dominio — patrón
paso_14e). Construye los DTOs internamente:

```python
def crear_plantilla_simple(self, nombre, jornada="UNICA", dias=None) -> PlantillaFranja
def listar_plantillas(self) -> list[PlantillaFranja]
def plantilla_activa(self, jornada="UNICA") -> PlantillaFranja | None
def guardar_franjas(self, plantilla_id, filas: list[dict]) -> int   # -> reemplazar_franjas
def activar_plantilla(self, plantilla_id) -> None
def eliminar_plantilla(self, plantilla_id) -> bool
```

`guardar_franjas` recibe `filas` como `list[dict]` con claves `orden`,
`hora_inicio`, `hora_fin`, `tipo`, `etiqueta`, construye `Franja` y delega en
`reemplazar_franjas`. Devuelve el conteo.

## Seed (seed.py)

`_seed_plantilla_franjas(conn) -> int` (devuelve `plantilla_id`):

1. INSERT plantilla `("Jornada única", "UNICA", "Lunes,...,Viernes", activa=1)`.
2. INSERT 7 franjas (6 lectivas + 1 recreo). Ejemplo:

| orden | inicio | fin | tipo | etiqueta |
|---|---|---|---|---|
| 1 | 07:00 | 07:55 | lectiva | |
| 2 | 07:55 | 08:50 | lectiva | |
| 3 | 08:50 | 09:45 | lectiva | |
| 4 | 09:45 | 10:15 | descanso | Recreo |
| 5 | 10:15 | 11:10 | lectiva | |
| 6 | 11:10 | 12:05 | lectiva | |
| 7 | 12:05 | 13:00 | lectiva | |

Llamar `_seed_plantilla_franjas` desde la función principal de seed (junto a
`_seed_escenarios`). En `seed_test`: una plantilla mínima con ≥1 franja lectiva.

## Tests

### Unit (`tests/unit/domain/test_franja_model.py` — nuevo)
- `Franja`: orden ≥ 1; `tipo` inválido → ValidationError; `hora_inicio >= hora_fin`
  → error; `es_lectiva` True/False según tipo.
- `PlantillaFranja`: nombre vacío → error; día inválido en `dias_activos` → error;
  `dias_activos` vacío → error.
- DTOs: `to_plantilla()` / `to_franja()` producen el modelo correcto.

### Integración (`tests/integration/test_franjas_repo.py` — nuevo)
Con `db_conn`:
- Crear plantilla + `reemplazar_franjas` con 3 franjas → `listar_franjas` ordenadas.
- Exclusividad: crear 2 plantillas UNICA, activar la 2ª → la 1ª queda `activa=0`
  (`get_plantilla_activa("UNICA")` devuelve la 2ª).
- Plantillas de jornadas distintas (AM y PM) pueden estar ambas activas a la vez
  (el índice parcial es por jornada).
- `eliminar_plantilla_franja` cascada borra sus franjas.
- El seed dejó una plantilla activa con franjas (`get_plantilla_activa` no None).

## Alternativa descartada

**Modelar la hora como índice de franja en `horarios` ya en este paso.** Acoplaría
la tabla `horarios` (y la carga masiva de paso_14f/14g) a la rejilla antes de que
exista el generador. Se difiere a paso_15c, donde el solver decidirá si `horarios`
gana una columna `franja_id` o sigue derivando `hora_inicio/fin` desde la franja.
Mantener `horarios` intacto aquí evita regresiones en lo ya entregado.

## Verificación

- `python -X utf8 -m pytest tests/unit/domain/test_franja_model.py tests/integration/test_franjas_repo.py -v`
- `python -X utf8 init.py` exit 0; suite sin regresiones (≥804 passed).
