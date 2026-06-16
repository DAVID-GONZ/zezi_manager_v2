# Tasks: Restricciones configurables del generador (paso_17_restricciones_configurables)

> Fases incrementales. Cada tarea deja `python init.py` verde y sin regresiones.
> El default sin configurar = comportamiento actual (R16). No se toca
> `parrilla_widget.py` (R17).

## Fase A — Modelo y persistencia ✅ (2026-06-14)
- [x] T1: Modelos nuevos (`Sala`, `VentanaGrupo`, `BloqueAnclado`, `FranjaReunion`,
          límites docente) + ampliaciones (`Asignatura.tipo_sala_requerido`,
          `bloque_doble`, `horas_consecutivas`; `PesosGeneracion` con balance_diario,
          franja_preferida, dia_libre, hueco_comun; `ConfigGeneracion.restricciones`).
  Verifica: `python -m pytest tests/domain -q` → **424 tests OK**
- [x] T2: DDL en `schema.py` (tablas `salas`, `ventanas_grupo`, `bloques_anclados`,
          `franjas_reunion`, `limites_docente`; columnas nuevas) + repos + métodos de
          servicio + datos de ejemplo en `seed`. **Dev: sin migración**, se recrea la BD
          con seed.
  Verifica: `python scripts/check_imports.py` → OK · init.py → **900 tests OK**

## Fase B — Captura en interfaz
- [x] T3: UI de disponibilidad docente (rejilla días×franjas) + límites docente
          (carga_max, min/max día) usando los servicios existentes/nuevos. ✅ (2026-06-14)
- [x] T4: CRUD de salas + selector "tipo de sala requerido" en asignatura + sección de
          restricciones en el diálogo de ConfigGeneracion (modo estricta/preferente + pesos). ✅ (2026-06-14)

## Fase C — Motor: restricciones duras ✅ (2026-06-14)
- [x] T5: Salas en el motor (ocupado_sala + elección de sala por tipo; coloreo solo sin
          restricción de sala) y bloques dobles/consecutivos (macro-lección contigua).
  Verifica: 29 tests OK
- [x] T6: Ventanas de grupo, bloques anclados (siembra previa) e híbridas estrictas
          (min/máx diario docente, máx/día materia).
  Verifica: 29 tests OK

## Fase D — Motor: coste blando ✅ (2026-06-14)
- [x] T7: Términos de coste balance_diario, hueco_comun, franja_preferida, dia_libre en
          `_costo`; hill-climbing los optimiza. Métrica sum_sq para balance_diario
          (funciona correctamente con 1 solo día de datos).
  Verifica: 29 tests OK

## Fase E — Infactibilidad ✅ (2026-06-14)
- [x] T8: Pre-vuelo O(n) (grupo/docente) con incidencias accionables; relajación
          ordenada (max_horas_dia_estricta → franjas_reunion_estricta) con registro
          en `relajadas`; diagnóstico de causa por no-colocado en `causas` dict.
  Verifica: 33 tests OK (4 nuevos T8)

## Cierre ✅ (2026-06-14)
- [x] T9: Verificación completa y no-regresión.
  Resultado: `python init.py` → ✅ · `python -m pytest -q` → **920 passed, 1 skipped**
  Comportamiento por defecto equivalente al original (sin configurar restricciones = sin cambios).

> Nota: T3/T4 (UI) pueden reubicarse dentro de la página única de paso_18; si paso_18
> va antes, crear las secciones directamente allí.
