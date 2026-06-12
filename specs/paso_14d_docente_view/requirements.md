# paso_14d_docente_view — requirements

Rediseña la experiencia del rol docente en `/horarios`: vista por día y por
semana del horario vigente, más el conteo de clases dictadas en el mes. Depende
de `paso_14a` (escenario activo) y `paso_14c` (conteo).

Notación EARS. Fuente de verdad: `src/interface/pages/academico/horarios.py`,
`src/services/`.

## Vista por rol

- **R1** — Cuando el usuario tenga rol docente, el sistema DEBERÁ mostrar
  únicamente su propio horario, tomado del escenario activo del año, sin
  selectores de grupo ni de docente.
- **R2** — El sistema DEBERÁ ofrecer al docente una alternancia entre **vista
  semanal** (grilla día × hora) y **vista diaria** (los bloques de un único día).
- **R3** — En la vista diaria, el sistema DEBERÁ permitir elegir el día y, por
  defecto, mostrar el día actual (o lunes si el día actual no es hábil).

## Conteo de clases del mes

- **R4** — El sistema DEBERÁ mostrar una tarjeta con el número de clases dictadas
  por el docente en el mes en curso, calculado a partir de los registros de
  asistencia.
- **R5** — El sistema DEBERÁ permitir consultar el conteo de un mes distinto al
  actual mediante un selector de mes.
- **R6** — Cuando no existan registros en el mes, la tarjeta DEBERÁ mostrar 0 de
  forma legible, sin error.

## Estados vacíos

- **R7** — Cuando no haya escenario activo o el docente no tenga bloques, el
  sistema DEBERÁ mostrar un estado vacío explicativo (sin acción de creación,
  pues el docente no edita).

## Restricciones

- **R8** — El rol docente NO DEBERÁ disponer de acciones de creación, edición,
  movimiento o eliminación de bloques en esta vista.
- **R9** — La página DEBERÁ usar los componentes del design system
  (`empty_state`, `stat_card`/`status_badge`, botones `btn_*`) y no introducir
  estilos inline estáticos ni `ui.button().props()`.

## Verificación

- **R10** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ presentar
  regresiones; la página DEBERÁ cargar para el rol docente mostrando grilla,
  alternancia día/semana y tarjeta de clases del mes.

## Fuera de alcance

- Gestión de escenarios y edición (paso_14e); carga masiva (paso_14f).
