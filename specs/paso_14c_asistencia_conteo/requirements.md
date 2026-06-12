# paso_14c_asistencia_conteo — requirements

Agregación que cuenta las clases efectivamente dictadas por un docente en un mes,
a partir de los registros de asistencia. Alimenta la tarjeta del rol docente
(paso_14d).

Notación EARS. Fuente de verdad: `src/services/asistencia_service.py`,
`src/domain/ports/asistencia_repo.py`.

## Definición de "clase dada"

- **R1** — El sistema DEBERÁ contar una clase dada por cada par distinto
  (`asignacion_id`, `fecha`) con al menos un registro de asistencia, asociado a
  una asignación cuyo docente sea el solicitado.
- **R2** — El conteo DEBERÁ delimitarse a un mes calendario (`anio`, `mes`).

## Consulta

- **R3** — El sistema DEBERÁ exponer una consulta que reciba `usuario_id`,
  `anio` y `mes` y retorne el número entero de clases dadas en ese mes.
- **R4** — Cuando el docente no tenga registros en el mes, el sistema DEBERÁ
  retornar 0 sin error.
- **R5** — El sistema NO DEBERÁ contar dos veces la misma asignación-fecha aunque
  tenga múltiples estudiantes registrados ese día.

## Desglose opcional

- **R6** — El sistema DEBERÁ exponer, además del total, un desglose por
  asignación (clases dadas por cada asignación del docente en el mes) para
  permitir a la interfaz mostrar detalle si lo requiere.

## Verificación

- **R7** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ presentar
  regresiones; R1–R5 DEBERÁN estar cubiertas por tests con repositorio falso o de
  integración con seed determinista.

## Fuera de alcance

- Presentación en la página del docente (paso_14d).
