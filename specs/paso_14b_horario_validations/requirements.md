# paso_14b_horario_validations — requirements

Centraliza las reglas de control del horario que hoy existen a medias o están
desconectadas. Depende de `paso_14a` (escenario, carga horaria del docente).

Notación EARS. Fuente de verdad: `src/services/`, `src/domain/models/`.

## Servicio de horario

- **R1** — El sistema DEBERÁ exponer un servicio de horario que concentre la
  creación, edición, movimiento y eliminación de bloques sobre un escenario.

## Asignación requerida y coherencia

- **R2** — Cuando se cree o edite un bloque, el sistema DEBERÁ exigir una
  asignación existente y activa; si no se provee o no existe, DEBERÁ rechazar la
  operación con un mensaje claro.
- **R3** — El sistema DEBERÁ derivar `grupo_id`, `asignatura_id` y `usuario_id`
  del bloque desde la asignación, de modo que un bloque solo pueda crearse para
  el grupo, la materia y el docente que la asignación define.

## Sin cruces de horario

- **R4** — Cuando se cree o edite un bloque, el sistema DEBERÁ rechazarlo si el
  **docente** ya tiene, en el mismo escenario y día, otro bloque cuyo rango
  horario se solape.
- **R5** — El sistema DEBERÁ rechazarlo si el **grupo** ya tiene, en el mismo
  escenario y día, otro bloque cuyo rango horario se solape.
- **R6** — El sistema DEBERÁ rechazarlo si la **sala** (cuando no sea el valor
  genérico "Aula") ya está ocupada, en el mismo escenario y día, por otro bloque
  cuyo rango horario se solape.
- **R7** — Al editar o mover un bloque, el sistema DEBERÁ excluir el propio
  bloque de la detección de cruces.

## Topes de carga

- **R8** — El sistema DEBERÁ rechazar el bloque si, al sumarlo, el número de
  bloques de esa asignación en el escenario supera las `horas_semanales` de la
  asignatura.
- **R9** — El sistema DEBERÁ rechazar el bloque si, al sumarlo, la suma de
  bloques del docente en el escenario supera su `carga_horaria_max` (cuando el
  docente tenga un tope definido).
- **R10** — Cuando el docente no tenga `carga_horaria_max` definido, el sistema
  NO DEBERÁ aplicar el tope global de R9.

## Mensajería y consulta de cupos

- **R11** — Cuando una validación falle, el sistema DEBERÁ comunicar el motivo
  específico (asignación, cruce de docente/grupo/sala, tope de materia, tope de
  docente) sin exponer detalles internos.
- **R12** — El sistema DEBERÁ exponer una consulta de disponibilidad por
  asignación y por docente (horas usadas / horas máximas) para que la interfaz
  muestre el cupo restante antes de intentar guardar.

## Verificación

- **R13** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ
  presentar regresiones; las reglas R2–R10 DEBERÁN estar cubiertas por tests
  unitarios con repositorio falso.

## Fuera de alcance

- Interfaz de edición y de carga masiva (pasos 14e, 14f).
