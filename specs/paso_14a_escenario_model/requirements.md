# paso_14a_escenario_model — requirements

Cimiento del épico de horarios. Introduce el concepto de **escenario de horario**
(varios guardados por año, uno solo vigente) y el **tope de carga horaria** por
docente. No hay script de transformación de datos: el esquema declara las nuevas
estructuras y el `seed` provee los datos de desarrollo y de test.

Notación EARS. Fuente de verdad: `src/domain/models/infraestructura.py`,
`src/domain/models/usuario.py`, `src/infrastructure/db/schema.py`,
`src/infrastructure/db/seed.py`.

## Entidad EscenarioHorario

- **R1** — El sistema DEBERÁ permitir representar un escenario de horario con:
  `id`, `anio_id`, `nombre`, `descripcion` (opcional), `activo` (booleano) y
  `created_at`.
- **R2** — Cuando se solicite el nombre de un escenario, el sistema DEBERÁ
  normalizarlo (strip) y rechazar el valor vacío.
- **R3** — El sistema DEBERÁ garantizar que, para un mismo `anio_id`, no exista
  más de un escenario con `activo = verdadero`.
- **R4** — Mientras un escenario esté activo, el sistema DEBERÁ tratar sus bloques
  como el horario vigente del año, aplicable a todos los periodos de ese año.

## Vínculo de Horario al escenario

- **R5** — El sistema DEBERÁ asociar cada bloque de horario a exactamente un
  escenario mediante `escenario_id`.
- **R6** — El sistema DEBERÁ garantizar la unicidad de un bloque por
  (`escenario_id`, `grupo_id`, `dia_semana`, `hora_inicio`).
- **R7** — Cuando se elimine un escenario, el sistema DEBERÁ eliminar en cascada
  sus bloques de horario asociados.
- **R8** — El sistema DEBERÁ exponer la consulta del horario de un grupo y de un
  docente resolviendo el escenario activo del año al que pertenece el periodo
  recibido, de modo que las firmas existentes
  (`listar_horario_grupo(grupo_id, periodo_id)`,
  `listar_horario_docente(usuario_id, periodo_id)`) sigan operativas.
- **R9** — El sistema DEBERÁ exponer además la consulta de bloques por escenario
  explícito (`listar_horario_grupo_escenario`, `listar_horario_escenario`) para
  alimentar al editor de escenarios.

## Tope de carga horaria del docente

- **R10** — El sistema DEBERÁ permitir registrar en el docente un valor de
  `carga_horaria_max` (entero de horas/semana) opcional; el valor ausente
  significa "sin tope".
- **R11** — El sistema DEBERÁ exponer una lectura del `carga_horaria_max` de un
  docente para que la capa de validación la consulte.

## Operaciones de escenario

- **R12** — El sistema DEBERÁ permitir crear, listar (por año), activar,
  renombrar y eliminar escenarios.
- **R13** — Cuando se active un escenario, el sistema DEBERÁ desactivar
  automáticamente cualquier otro escenario activo del mismo año.
- **R14** — El sistema DEBERÁ permitir duplicar un escenario, copiando todos sus
  bloques a un escenario nuevo e inactivo con nombre distinto.

## Datos de desarrollo y test (seed)

- **R15** — El `seed` de desarrollo DEBERÁ crear al menos un escenario activo
  ("Horario base") con los bloques de ejemplo y un segundo escenario inactivo
  ("Plan alterno") para ejercitar la habilitación/deshabilitación.
- **R16** — El `seed` de desarrollo DEBERÁ fijar un `carga_horaria_max` a los
  docentes de ejemplo.
- **R17** — El `seed` de test DEBERÁ crear un escenario activo determinista con
  al menos un bloque, de modo que los tests de integración de horario dispongan
  de un escenario sin depender de randomización.
- **R18** — Tras correr el `seed`, `python init.py` DEBERÁ quedar verde y la
  suite de tests no DEBERÁ presentar regresiones.

## Fuera de alcance

- Validaciones de cruces y topes (paso_14b).
- Conteo de clases dictadas (paso_14c).
- Cambios de interfaz (pasos 14d–14f).
