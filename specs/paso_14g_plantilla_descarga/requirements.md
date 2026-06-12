# paso_14g_plantilla_descarga — requirements

Cierra el flujo de carga/descarga de horarios: una **plantilla tipo** prellenada
con las asignaciones del periodo (para que la carga masiva sea guiada) y la
**descarga del horario** de un escenario para los roles superiores. Añade además
cobertura de tests de carga, descarga e integración del encadenamiento
asignatura → asignación → horario.

Depende de `paso_14a` (escenarios), `paso_14b` (validaciones) y `paso_14f`
(carga masiva). Notación EARS. Fuente de verdad: `src/services/horario_service.py`,
`src/interface/pages/academico/horarios.py`, `src/domain/ports/service_ports.py`
(`IExporterService`).

## Plantilla tipo

- **R1** — El sistema DEBERÁ generar una plantilla de horario que incluya, además
  de las columnas de carga (`asignacion_id`, `dia_semana`, `hora_inicio`,
  `hora_fin`, `sala`), columnas de referencia legibles (`grupo`, `asignatura`,
  `docente`) que faciliten identificar cada asignación.
- **R2** — La plantilla DEBERÁ venir **prellenada con una fila por cada asignación
  activa del periodo**, con `asignacion_id` y columnas de referencia rellenas y
  las columnas de día/hora vacías y `sala` con el valor por defecto "Aula", de
  modo que el usuario solo complete día y horas.
- **R3** — Las columnas de referencia DEBERÁN ser ignoradas al volver a cargar el
  archivo (el parser de carga masiva solo consume `asignacion_id`, `dia_semana`,
  `hora_inicio`, `hora_fin`, `sala`), de modo que la plantilla descargada sea
  recargable sin edición de cabeceras.

## Descarga de horarios (roles superiores)

- **R4** — El sistema DEBERÁ permitir a los roles con permiso de edición
  (admin, director; coordinador según política vigente) descargar el horario del
  escenario seleccionado como archivo (CSV por defecto, vía el exportador del
  sistema).
- **R5** — La descarga DEBERÁ contener una fila por cada bloque del escenario, con
  las mismas columnas que la plantilla (`asignacion_id`, `grupo`, `asignatura`,
  `docente`, `dia_semana`, `hora_inicio`, `hora_fin`, `sala`), de modo que un
  horario descargado pueda re-cargarse mediante la carga masiva (ida y vuelta).
- **R6** — Cuando el escenario no tenga bloques, la descarga NO DEBERÁ fallar:
  DEBERÁ producir un archivo solo con cabeceras o el sistema DEBERÁ avisar de que
  no hay bloques, sin lanzar excepción.

## Capa de servicio

- **R7** — La preparación de los datos (plantilla y exportación) DEBERÁ vivir en
  `HorarioService`, devolviendo `list[dict]` con claves canónicas; la conversión
  a bytes la hace el `IExporterService` y la entrega al navegador la hace la
  interfaz. El servicio NO DEBERÁ importar librerías de exportación ni NiceGUI.

## Tests

- **R8** — DEBERÁ existir cobertura de **carga**: análisis y aplicación de un lote
  (incluyendo el caso ida-y-vuelta: exportar un horario y volver a analizarlo sin
  errores nuevos atribuibles al formato).
- **R9** — DEBERÁ existir cobertura de **descarga**: `plantilla_filas` produce una
  fila por asignación activa del periodo con las columnas esperadas;
  `filas_exportables` produce una fila por bloque con las columnas esperadas y
  caso de escenario vacío.
- **R10** — DEBERÁ existir un **test de integración** que ejercite el
  encadenamiento real sobre la BD de seed: una asignatura tiene asignaciones, una
  asignación se materializa en uno o más bloques de horario, y cada bloque
  referencia `grupo_id`, `asignatura_id` y `usuario_id` coherentes con su
  asignación. DEBERÁ usar las fixtures de integración existentes (`db_conn`,
  `seed_result`).

## Design system y verificación

- **R11** — La interfaz DEBERÁ usar componentes del design system (`btn_*`,
  `toast_*`) sin estilos inline estáticos ni `ui.button().props()`. El botón de
  plantilla existente DEBERÁ reemplazarse por la plantilla prellenada (R2).
- **R12** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ presentar
  regresiones; el flujo descargar plantilla prellenada → completar → cargar →
  aplicar, y descargar horario del escenario, DEBERÁN ser operativos.

## Fuera de alcance

- Exportación a PDF del horario (solo CSV/Excel vía exportador).
- Cambios en la lógica de validación de `paso_14b`/`paso_14f`.
