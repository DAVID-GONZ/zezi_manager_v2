# paso_14f_carga_masiva — requirements

Añade la carga masiva de bloques de horario sobre un escenario, con validación de
todo el lote antes de persistir. Depende de `paso_14a` (escenarios) y `paso_14b`
(validaciones), y convive con la edición manual de `paso_14e`.

Notación EARS. Fuente de verdad: `src/services/horario_service.py`,
`src/interface/pages/academico/horarios.py`.

## Plantilla e ingesta

- **R1** — El sistema DEBERÁ ofrecer la descarga de una plantilla con las
  columnas esperadas (grupo, asignatura, docente o código de asignación, día,
  hora inicio, hora fin, sala) y un ejemplo.
- **R2** — El sistema DEBERÁ aceptar la carga de un archivo (CSV o Excel) con
  filas de bloques destinados a un escenario seleccionado.
- **R3** — El sistema DEBERÁ resolver cada fila a una asignación existente y
  activa del periodo; si la fila no corresponde a una asignación válida, DEBERÁ
  marcarla como error sin abortar el resto del análisis.

## Validación del lote completo

- **R4** — Antes de persistir, el sistema DEBERÁ validar cada fila contra las
  mismas reglas de la edición manual: asignación requerida, cruces de
  docente/grupo/sala, tope de materia y tope de docente.
- **R5** — El sistema DEBERÁ detectar además los cruces y duplicados **internos
  del propio lote** (filas que se solapan entre sí), no solo contra los bloques
  ya existentes.
- **R6** — Los topes de materia y de docente DEBERÁN evaluarse considerando los
  bloques ya existentes en el escenario más los del lote en conjunto.

## Resultado y persistencia

- **R7** — El sistema DEBERÁ presentar un reporte previo que liste, por fila, si
  es válida o el motivo del rechazo, antes de confirmar.
- **R8** — El sistema DEBERÁ permitir aplicar solo las filas válidas, o exigir
  que todo el lote sea válido, según la elección del usuario; por defecto, NO
  DEBERÁ persistir ninguna fila si hay errores (modo "todo o nada"), con opción
  explícita de "cargar solo válidas".
- **R9** — Tras aplicar, el sistema DEBERÁ informar cuántos bloques se crearon y
  cuántas filas se omitieron.
- **R10** — La operación de aplicar el lote DEBERÁ ser atómica respecto a las
  filas elegidas (todas las válidas seleccionadas se crean o ninguna, ante un
  fallo inesperado).

## Permisos y design system

- **R11** — La carga masiva DEBERÁ estar disponible solo para los roles con
  permiso de edición de horarios (admin, director; coordinador según la política
  vigente).
- **R12** — La interfaz DEBERÁ usar componentes del design system (`form_dialog`
  o panel con `ui.upload`, `status_badge`, `btn_*`, `toast_*`, `skeleton_*`
  durante el análisis) sin estilos inline estáticos ni `ui.button().props()`.

## Verificación

- **R13** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ presentar
  regresiones; el flujo descargar plantilla → cargar archivo → ver reporte →
  aplicar DEBERÁ ser operativo y respetar las validaciones de `paso_14b` y los
  cruces internos del lote (R5).

## Fuera de alcance

- Edición individual de bloques (paso_14e) y conteo de clases (paso_14c).
