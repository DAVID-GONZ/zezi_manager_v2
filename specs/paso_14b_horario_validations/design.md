# paso_14b_horario_validations — design

## Componente nuevo: `HorarioService`

`src/services/horario_service.py`. Orquesta la escritura de bloques con todas las
reglas. No contiene SQL ni NiceGUI. Depende (por inyección, vía `container.py`)
de:

- `IInfraestructuraRepository` — escenarios, bloques, conflictos, conteos.
- `IAsignacionRepository` — resolver y validar la asignación.
- `IUsuarioRepository` (o `UsuarioService`) — leer `carga_horaria_max`.

### Métodos públicos

```
crear_bloque(escenario_id, asignacion_id, dia, hora_inicio, hora_fin, sala) -> Horario
mover_bloque(horario_id, dia, hora_inicio, hora_fin) -> Horario
actualizar_bloque(horario_id, *, dia, hora_inicio, hora_fin, sala) -> Horario
eliminar_bloque(horario_id) -> bool
disponibilidad_asignacion(escenario_id, asignacion_id) -> CupoDTO   # usadas/max
disponibilidad_docente(escenario_id, usuario_id) -> CupoDTO
```

### Flujo de validación (crear/editar)

1. Resolver asignación (`get_by_id`); si None o `activo=False` → `ValueError`
   "La asignación no existe o está inactiva." (R2).
2. Derivar `grupo_id`, `asignatura_id`, `usuario_id` de la asignación (R3); la
   capa de interfaz no los envía.
3. Cruces (R4–R7), vía repo `existe_cruce(...)`:
   - docente: `usuario_id` del bloque.
   - grupo: `grupo_id` del bloque.
   - sala: solo si `sala != "Aula"`.
   - en edición/movimiento, pasar `excluir_horario_id`.
4. Tope materia (R8): contar bloques de la asignación en el escenario; si
   `usados + 1 > asignatura.horas_semanales` → `ValueError`.
5. Tope docente (R9–R10): leer `carga_horaria_max`; si está definido y
   `usados_docente + 1 > max` → `ValueError`.
6. Persistir vía `guardar_horario` / `actualizar_horario` (paso_14a).

Cada fallo lanza `ValueError` con texto orientado al usuario (R11); la interfaz
lo captura y lo muestra con `toast_warning`.

## DTO de cupo

`CupoDTO(BaseModel)` en `src/domain/models/infraestructura.py`:
`usadas: int`, `maximas: int | None`, propiedad `disponibles` y `excedido`.

## Puerto `IInfraestructuraRepository` — métodos nuevos

- `existe_cruce(escenario_id, dia_semana, hora_inicio, hora_fin, *, usuario_id=None, grupo_id=None, sala=None, excluir_horario_id=None) -> bool`
  Un solo método parametrizado por dimensión; el servicio lo invoca tres veces.
- `contar_bloques_asignacion(escenario_id, asignacion_id) -> int`
- `contar_bloques_docente(escenario_id, usuario_id) -> int`

> El método legado `existe_conflicto_horario(usuario, periodo, ...)` queda
> reemplazado por `existe_cruce` (basado en escenario y multidimensional). Se
> elimina del puerto y del repo, y se actualiza cualquier llamador.

## Repositorio SQLite

`existe_cruce`: `SELECT 1 FROM horarios WHERE escenario_id=? AND dia_semana=?
AND hora_inicio < :hora_fin AND hora_fin > :hora_inicio` + filtro dinámico por
`usuario_id` / `grupo_id` / `sala` + `AND id != :excluir`. Solape estándar
`inicio_a < fin_b AND fin_a > inicio_b`.

## `container.py`

Registrar `horario_service()` con sus tres dependencias (factoría perezosa,
igual patrón que los servicios existentes).

## Interfaz (mínima en este paso)

Ninguna página se reescribe aquí; el cableado UI es 14e/14f. Este paso entrega el
servicio y sus tests. Se permite, opcionalmente, conectar el `_guardar` actual de
`horarios.py` a `HorarioService.crear_bloque` para no dejar la validación
desconectada — pero el rediseño completo es 14e.

### Alternativa descartada

**Poner las validaciones dentro de `InfraestructuraService.guardar_horario`.**
Descartada: ese servicio es un CRUD fino sobre el repo y se usa desde varios
sitios; cargarlo con reglas de asignación/cupos acopla responsabilidades. Un
`HorarioService` dedicado deja el CRUD intacto y concentra la política.

## Verificación

- `python -m pytest tests/unit/ -q -k horario_service` cubre R2–R10.
- `python scripts/check_imports.py --layer services` (no importa `src.db`).
- `python init.py` exit 0.
