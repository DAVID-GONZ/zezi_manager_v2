# paso_14a_escenario_model — design

## Estrategia: sin transformación de datos

Estamos en desarrollo. En lugar de un script que altere datos existentes, se
declara la estructura final en `schema.py` (CREATE TABLE / columnas nuevas) y se
recrea la base con el `seed`. `init.py` reconstruye el esquema; `seed_dev` /
`seed_test` proveen los escenarios y las cargas horarias.

## Esquema (`src/infrastructure/db/schema.py`)

### Tabla nueva `escenarios_horario`

```sql
CREATE TABLE IF NOT EXISTS escenarios_horario (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anio_id     INTEGER NOT NULL,
    nombre      TEXT    NOT NULL,
    descripcion TEXT,
    activo      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(anio_id, nombre),
    FOREIGN KEY(anio_id) REFERENCES configuracion_anio(id) ON DELETE CASCADE
)
```

Índice parcial que garantiza R3 (un activo por año):

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_escenario_activo_unico
    ON escenarios_horario(anio_id) WHERE activo = 1
```

### Cambios en tabla `horarios`

- Añadir columna `escenario_id INTEGER NOT NULL`.
- FK `FOREIGN KEY(escenario_id) REFERENCES escenarios_horario(id) ON DELETE CASCADE`.
- Reemplazar la constraint `UNIQUE(grupo_id, dia_semana, hora_inicio, periodo_id)`
  por `UNIQUE(escenario_id, grupo_id, dia_semana, hora_inicio)` (R6).
- `periodo_id` pasa a aceptar NULL (deja de ser la clave de almacenamiento; se
  conserva la columna para compatibilidad de lectura/informes).
- Índice nuevo `idx_horarios_escenario ON horarios(escenario_id)`.

### Cambios en tabla `usuarios`

- Añadir columna `carga_horaria_max INTEGER` (NULL permitido).

## Dominio

### `src/domain/models/infraestructura.py`

- **`EscenarioHorario(BaseModel)`**: `id: int | None`, `anio_id: int`,
  `nombre: str` (validator strip + no vacío), `descripcion: str | None = None`,
  `activo: bool = False`, `created_at: str | None = None`. Validator id positivo
  para `anio_id`.
- **`NuevoEscenarioDTO(BaseModel)`**: `anio_id`, `nombre`, `descripcion`,
  método `to_escenario()`.
- **`Horario`**: añadir `escenario_id: int` (validator positivo); cambiar
  `periodo_id: int` → `periodo_id: int | None = None`.
- **`NuevoHorarioDTO`**: añadir `escenario_id: int`; `periodo_id` opcional.
- **`HorarioInfo`**: añadir `escenario_id: int`.
- Exports actualizados en `__all__`.

### `src/domain/models/usuario.py`

- Añadir `carga_horaria_max: int | None = None` a la entidad de usuario, con
  validator que rechace negativos.

## Puerto `IInfraestructuraRepository`

Métodos nuevos (abstractos):

- `get_escenario(escenario_id) -> EscenarioHorario | None`
- `listar_escenarios(anio_id) -> list[EscenarioHorario]`
- `get_escenario_activo(anio_id) -> EscenarioHorario | None`
- `crear_escenario(esc: EscenarioHorario) -> EscenarioHorario`
- `actualizar_escenario(esc) -> EscenarioHorario` (nombre/descripcion)
- `activar_escenario(escenario_id) -> None` (desactiva los demás del año)
- `eliminar_escenario(escenario_id) -> bool`
- `duplicar_escenario(escenario_id, nuevo_nombre) -> EscenarioHorario`
- `listar_horario_grupo_escenario(grupo_id, escenario_id) -> list[HorarioInfo]`
- `listar_horario_escenario(escenario_id) -> list[HorarioInfo]`

`listar_horario_grupo` / `listar_horario_docente` mantienen su firma pero su
implementación resuelve: `periodo_id → periodos.anio_id → escenario activo`, y si
no hay escenario activo retornan `[]`.

## Repositorio `sqlite_infraestructura_repo.py`

- CRUD de escenario sobre `escenarios_horario`.
- `activar_escenario`: transacción `UPDATE ... SET activo=0 WHERE anio_id=?` y
  luego `UPDATE ... SET activo=1 WHERE id=?` (el índice parcial protege la
  invariante).
- `duplicar_escenario`: inserta escenario inactivo y copia filas de `horarios`
  con el nuevo `escenario_id`.
- `guardar_horario` / `actualizar_horario`: incluir `escenario_id` en INSERT/UPDATE;
  `periodo_id` se persiste como NULL si no viene.
- Las consultas que hoy filtran por `periodo_id` pasan a resolver el escenario
  activo y filtran por `escenario_id`.

## Servicio `InfraestructuraService`

Métodos delegados nuevos: `listar_escenarios`, `get_escenario_activo`,
`crear_escenario`, `activar_escenario`, `renombrar_escenario`,
`eliminar_escenario`, `duplicar_escenario`,
`listar_horario_grupo_escenario`, `listar_horario_escenario`. El método
`carga_horaria_max(usuario_id)` se expone vía `UsuarioService` (lectura del
campo nuevo).

## `container.py`

No requiere wiring nuevo de repos (los métodos viven en repos ya registrados).
Verificar que `InfraestructuraService` y `UsuarioService` exponen los métodos.

## `seed.py`

- `_seed_escenarios(conn, anio_id) -> dict[str, int]`: crea "Horario base"
  (`activo=1`) y "Plan alterno" (`activo=0`); retorna `{nombre: id}`.
- `_seed_horarios`: recibe `escenario_id` activo; inserta bloques con
  `escenario_id`, `periodo_id=NULL`.
- `_seed_usuarios` (dev): tras crear docentes, `UPDATE usuarios SET
  carga_horaria_max=22 WHERE rol='profesor'` (o columna en la tupla de datos).
- `seed_test`: añadir `_seed_escenarios` + un bloque de horario en el escenario
  activo para fixtures de integración.

### Alternativa descartada

**Mantener `horarios` ligado a `periodo_id` y simular escenarios con una columna
`etiqueta` de texto.** Descartada: no garantiza "un solo activo por año" a nivel
de BD, obliga a duplicar bloques por cada periodo del año (rompe "una vez por
año, replica a periodos") y complica la activación atómica. El índice parcial
sobre una tabla dedicada modela la invariante directamente.

## Verificación

- `python init.py` exit 0.
- `python -m pytest tests/ -q` sin regresiones.
- `python -c "from src.domain.models.infraestructura import EscenarioHorario, NuevoEscenarioDTO"`.
- Tras `seed_dev`: existe exactamente 1 escenario activo por año y ≥1 inactivo.
