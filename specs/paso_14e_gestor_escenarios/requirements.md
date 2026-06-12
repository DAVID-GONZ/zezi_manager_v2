# paso_14e_gestor_escenarios — requirements

Convierte `/horarios`, para admin/director/coordinador, en el lugar donde se
cargan y gestionan los horarios del año: administración de escenarios y edición
manual de bloques con todas las validaciones. Depende de `paso_14a` (escenarios)
y `paso_14b` (validaciones).

Notación EARS. Fuente de verdad: `src/interface/pages/academico/horarios.py`,
`src/services/horario_service.py`, `src/services/infraestructura_service.py`.

## Gestión de escenarios

- **R1** — El sistema DEBERÁ listar los escenarios del año, indicando cuál está
  activo.
- **R2** — El sistema DEBERÁ permitir crear un escenario nuevo (nombre y
  descripción), que nace inactivo.
- **R3** — El sistema DEBERÁ permitir activar un escenario; al hacerlo, el
  escenario antes vigente DEBERÁ quedar inactivo.
- **R4** — El sistema DEBERÁ permitir renombrar y eliminar un escenario; la
  eliminación DEBERÁ pedir confirmación y advertir que arrastra sus bloques.
- **R5** — El sistema DEBERÁ permitir duplicar un escenario para partir de una
  copia editable sin afectar al vigente.

## Edición de bloques sobre el escenario seleccionado

- **R6** — El sistema DEBERÁ permitir editar los bloques del escenario
  seleccionado (no necesariamente el activo), para preparar planes alternativos.
- **R7** — El sistema DEBERÁ permitir crear un bloque eligiendo una asignación
  del periodo, día, hora inicio, hora fin y sala.
- **R8** — El sistema DEBERÁ permitir editar y eliminar un bloque existente.
- **R9** — Cuando una operación viole una regla de control (asignación
  requerida, cruce de docente/grupo/sala, tope de materia, tope de docente), el
  sistema DEBERÁ impedirla y mostrar el motivo específico.
- **R10** — El sistema DEBERÁ mostrar, al elegir una asignación o un docente, el
  cupo restante (horas usadas frente al máximo) para guiar la carga.

## Filtrado por asignaciones

- **R11** — El selector de asignaciones DEBERÁ ofrecer únicamente asignaciones
  existentes y activas del periodo, de modo que un bloque solo pueda crearse para
  grupos y docentes efectivamente asignados.

## Permisos

- **R12** — Coordinador DEBERÁ poder consultar y, si la institución lo permite,
  editar; admin y director DEBERÁN tener edición completa. (El conjunto exacto de
  permisos de coordinador se conserva igual al comportamiento vigente salvo
  indicación contraria de David.)

## Estados y design system

- **R13** — Cuando el escenario no tenga bloques, el sistema DEBERÁ mostrar un
  estado vacío con acción de "Agregar bloque".
- **R14** — La página DEBERÁ usar componentes del design system (`form_dialog`,
  `confirm_dialog`, `empty_state`, `status_badge`, `btn_*`, `toast_*`) sin
  estilos inline estáticos ni `ui.button().props()`.

## Verificación

- **R15** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ presentar
  regresiones; el flujo crear escenario → editar bloques → activar DEBERÁ ser
  operativo y respetar las validaciones de `paso_14b`.

## Fuera de alcance

- Carga masiva (paso_14f), cubierta por su propio paso.
