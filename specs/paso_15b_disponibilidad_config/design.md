# paso_15b_disponibilidad_config — design

## Esquema (schema.py, módulo 4 — Periodos y asignaciones)

Insertar las dos tablas **después** de `asignaciones` y **antes** de `logros`
(o bien en un bloque nuevo "12. Generador de horarios" al final del SCHEMA para
mayor claridad). Se elige añadirlas al final del SCHEMA —justo antes de los
índices— para no alterar el orden existente. Solo requieren FKs a tablas ya
declaradas.

### `disponibilidad_docente`

```sql
CREATE TABLE IF NOT EXISTS disponibilidad_docente (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL,
    dia_semana   TEXT    NOT NULL
                 CHECK(dia_semana IN ('Lunes','Martes','Miércoles',
                                      'Jueves','Viernes','Sábado')),
    franja_orden INTEGER NOT NULL CHECK(franja_orden >= 1),
    disponible   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(usuario_id, dia_semana, franja_orden),
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
)
```

### `config_generacion`

```sql
CREATE TABLE IF NOT EXISTS config_generacion (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre               TEXT    NOT NULL UNIQUE,
    periodo_id           INTEGER NOT NULL,
    anio_id              INTEGER NOT NULL,
    plantilla_id         INTEGER NOT NULL,
    estado               TEXT    NOT NULL DEFAULT 'borrador'
                         CHECK(estado IN ('borrador','generado','aplicado')),
    grupos_json          TEXT    NOT NULL DEFAULT '[]',
    pesos_json           TEXT    NOT NULL DEFAULT
                         '{"huecos":1.0,"distribucion":1.0,"compactacion":0.5}',
    escenario_destino_id INTEGER,
    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(periodo_id)           REFERENCES periodos(id)            ON DELETE CASCADE,
    FOREIGN KEY(anio_id)              REFERENCES configuracion_anio(id)  ON DELETE CASCADE,
    FOREIGN KEY(plantilla_id)         REFERENCES plantillas_franja(id)   ON DELETE CASCADE,
    FOREIGN KEY(escenario_destino_id) REFERENCES escenarios_horario(id)  ON DELETE SET NULL
)
```

### Índices

```sql
CREATE INDEX IF NOT EXISTS idx_disponibilidad_docente
    ON disponibilidad_docente(usuario_id, dia_semana);
CREATE INDEX IF NOT EXISTS idx_config_generacion_periodo
    ON config_generacion(periodo_id, estado);
```

> `INSERT OR REPLACE` en disponibilidad es seguro porque el UNIQUE está sobre
> `(usuario_id, dia_semana, franja_orden)` — un REPLACE borrará e insertará solo
> esa fila específica.

---

## Dominio (infraestructura.py)

### `PesosGeneracion`

```python
class PesosGeneracion(BaseModel):
    huecos:       float = Field(default=1.0, ge=0.0, le=2.0)
    distribucion: float = Field(default=1.0, ge=0.0, le=2.0)
    compactacion: float = Field(default=0.5, ge=0.0, le=2.0)
```

Constante de módulo para defaults:
```python
PESOS_DEFAULT = PesosGeneracion()
```

### `DisponibilidadDocente`

```python
class DisponibilidadDocente(BaseModel):
    id:           int | None = None
    usuario_id:   int                   # > 0
    dia_semana:   str                   # en DiaSemana / DIAS_VALIDOS
    franja_orden: int                   # ge=1
    disponible:   bool = True
    # validator dia_semana: str en DIAS_VALIDOS
```

### `ConfigGeneracion`

```python
ESTADOS_CONFIG = {"borrador", "generado", "aplicado"}
TRANSICIONES_CONFIG = {
    "borrador":  {"generado"},
    "generado":  {"aplicado", "borrador"},
    "aplicado":  set(),      # terminal
}

class ConfigGeneracion(BaseModel):
    id:                   int | None = None
    nombre:               str        # strip, no vacío
    periodo_id:           int        # > 0
    anio_id:              int        # > 0
    plantilla_id:         int        # > 0
    estado:               str = "borrador"
    grupos:               list[int] = []   # [] = todos
    pesos:                PesosGeneracion = Field(default_factory=PesosGeneracion)
    escenario_destino_id: int | None = None
    created_at:           str | None = None
    updated_at:           str | None = None

    @field_validator("estado")
    def validar_estado(cls, v):
        if v not in ESTADOS_CONFIG:
            raise ValueError(f"estado inválido: {v!r}")
        return v

    def puede_transicionar_a(self, nuevo: str) -> bool:
        return nuevo in TRANSICIONES_CONFIG.get(self.estado, set())
```

En el repo: persistir `grupos` como `json.dumps(lista)`, `pesos` como
`json.dumps(pesos.model_dump())`; al leer, `json.loads(...)` y
`PesosGeneracion(**pesos_dict)`.

### DTOs

```python
class NuevaDisponibilidadDTO(BaseModel):
    usuario_id:   int
    dia_semana:   str
    franja_orden: int
    disponible:   bool = True
    def to_modelo(self) -> DisponibilidadDocente: ...

class NuevaConfigGeneracionDTO(BaseModel):
    nombre:       str
    periodo_id:   int
    anio_id:      int
    plantilla_id: int
    grupos:       list[int] = []
    pesos:        PesosGeneracion = Field(default_factory=PesosGeneracion)
    def to_config(self) -> ConfigGeneracion: ...
```

Actualizar `__all__` con: `PesosGeneracion`, `PESOS_DEFAULT`, `DisponibilidadDocente`,
`ConfigGeneracion`, `ESTADOS_CONFIG`, `TRANSICIONES_CONFIG`,
`NuevaDisponibilidadDTO`, `NuevaConfigGeneracionDTO`.

---

## Puerto (infraestructura_repo.py)

Añadir a `IInfraestructuraRepository`:

```python
# Disponibilidad
def upsert_disponibilidad(self, d: DisponibilidadDocente) -> DisponibilidadDocente: ...
def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]: ...
def es_disponible(self, usuario_id: int, dia: str, franja_orden: int) -> bool: ...
def limpiar_disponibilidad_docente(self, usuario_id: int) -> int: ...  # filas borradas
def cargar_disponibilidad_lote(self, usuario_id: int, slots: list[dict]) -> int: ...

# Config generacion
def crear_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion: ...
def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None: ...
def listar_configs_generacion(self, periodo_id: int | None = None) -> list[ConfigGeneracion]: ...
def actualizar_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion: ...
def eliminar_config_generacion(self, config_id: int) -> bool: ...
def cambiar_estado_config(self, config_id: int, nuevo_estado: str) -> ConfigGeneracion: ...
def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion: ...
```

> Al agregar métodos abstractos, los `FakeInfraRepo` de tests existentes necesitan
> stubs. Buscar con grep `class FakeInfraRepo` en `tests/unit/services/`.
> Patrón: devolver `None`/`[]`/`0`/`True` según el tipo de retorno.

---

## Repositorio (sqlite_infraestructura_repo.py)

### Disponibilidad
- `upsert_disponibilidad`: `INSERT OR REPLACE INTO disponibilidad_docente ...`
- `es_disponible`: `SELECT disponible FROM ... WHERE usuario_id=? AND dia_semana=? AND franja_orden=?`; si no hay fila → `True` (R2).
- `cargar_disponibilidad_lote`: loop de `INSERT OR REPLACE` con `disponible=0`; devuelve conteo.
- `limpiar_disponibilidad_docente`: `DELETE WHERE usuario_id=?`; devuelve `rowcount`.

### Config generación
- Mapeo JSON: `json.dumps`/`json.loads` para `grupos_json` y `pesos_json`.
- Helper privado `_row_to_config(row)`: construye `ConfigGeneracion` deserializando.
- `cambiar_estado_config`: leer la config, validar `puede_transicionar_a(nuevo)`,
  hacer UPDATE, también actualizar `updated_at = datetime('now')`. Lanzar
  `ValueError` si la transición es inválida.
- `duplicar_config_generacion`: leer la config origen, INSERT con
  `nombre = f"{original.nombre} (copia)"`, `estado = 'borrador'`,
  `escenario_destino_id = NULL`; devuelve la nueva config.

---

## Servicio fachada (infraestructura_service.py)

Añadir métodos que reciban tipos simples (str/int/list/dict, no modelos de dominio):

```python
# Disponibilidad
def es_disponible_docente(self, usuario_id, dia, franja_orden) -> bool
def bloquear_franjas_docente(self, usuario_id, slots: list[dict]) -> int
def limpiar_disponibilidad_docente(self, usuario_id) -> int
def listar_disponibilidad_docente(self, usuario_id) -> list[DisponibilidadDocente]

# Config generación
def crear_config_generacion(self, nombre, periodo_id, anio_id, plantilla_id,
                             grupos=None, pesos=None) -> ConfigGeneracion
def listar_configs_generacion(self, periodo_id=None) -> list[ConfigGeneracion]
def get_config_generacion(self, config_id) -> ConfigGeneracion | None
def actualizar_config_generacion(self, config_id, **campos) -> ConfigGeneracion
def eliminar_config_generacion(self, config_id) -> bool
def cambiar_estado_config(self, config_id, nuevo_estado) -> ConfigGeneracion
def duplicar_config_generacion(self, config_id) -> ConfigGeneracion
```

`crear_config_generacion`: construye `PesosGeneracion(**pesos)` si `pesos` es dict,
luego `NuevaConfigGeneracionDTO(...).to_config()` y llama al repo.

---

## Seed (seed.py)

`_seed_config_generacion(conn, periodo_id, anio_id, plantilla_id)`:
- INSERT una `config_generacion` de nombre `"Config inicial"`, `estado='borrador'`,
  `grupos_json='[]'`, `pesos_json` con defaults.
- Idempotente: verificar si ya existe por nombre antes de insertar.

Llamar desde `seed_test` (y desde la función de seed principal) pasando los IDs
correctos del contexto del seed.

---

## Tests

### Unit (`tests/unit/domain/test_disponibilidad_config_model.py`)
- `PesosGeneracion`: defaults correctos; valor fuera de [0.0, 2.0] → error.
- `DisponibilidadDocente`: `dia_semana` inválido → error; `franja_orden < 1` → error.
- `ConfigGeneracion`: estado inválido → error; `puede_transicionar_a` para todos los
  arcos válidos e inválidos (incluyendo desde `aplicado` → nada).
- `NuevaConfigGeneracionDTO.to_config`: produce `ConfigGeneracion` con estado `borrador`.
- `NuevaDisponibilidadDTO.to_modelo`: mapeo correcto.

### Integración (`tests/integration/test_disponibilidad_config_repo.py`)
Con `db_conn`:
- Upsert disponibilidad: insertar + actualizar misma fila (idempotencia).
- `es_disponible`: slot registrado como no disponible → `False`; slot no registrado
  → `True`; slot registrado como disponible → `True`.
- `cargar_disponibilidad_lote`: inserta N filas, `limpiar` borra todas.
- CRUD `config_generacion`: crear, leer, listar, eliminar.
- `cambiar_estado_config`: `borrador→generado` OK; `aplicado→borrador` lanza error.
- `duplicar_config_generacion`: copia con `" (copia)"` en estado `borrador`.
- Seed dejó al menos una config en `borrador`.

---

## Verificación

- `python -X utf8 -m pytest tests/unit/domain/test_disponibilidad_config_model.py tests/integration/test_disponibilidad_config_repo.py -v`
- `python -X utf8 init.py` exit 0; suite ≥832 + nuevos tests, sin regresiones.
