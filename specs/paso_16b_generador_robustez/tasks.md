# Tasks: Robustez de contexto e integración del generador (paso_16b_generador_robustez)

> Requiere `paso_16a_fix_generador_timer` en estado done.

- [ ] T1: En `horario_generar.py`, reemplazar el guard rígido de año/periodo por
          derivación robusta (`configuracion_service().get_activa()` +
          `periodo_service().get_activo()` con fallback), añadir claves
          `_s["anio_id"|"periodo_id"|"error_contexto"]` y migrar los usos de
          `ctx.anio_id/ctx.periodo_id` a `_s[...]`.
  Verifica: `python scripts/check_imports.py --layer interface`
  Produce: `src/interface/pages/academico/horario_generar.py`

- [ ] T2: En `contenido_refreshable()` de `horario_generar.py`, cortocircuitar con
          `empty_state` cuando falte año/periodo (`error_contexto`) o no haya
          plantillas (CTA a `/admin/plantillas-franja`).
  Verifica: `python scripts/check_design.py --file src/interface/pages/academico/horario_generar.py`
  Produce: exit code 0

- [ ] T3: Añadir botón «Ver en horarios» tras una generación válida que navegue a
          `/horarios?escenario=<escenario_id>`.
  Verifica: `python scripts/check_design.py --file src/interface/pages/academico/horario_generar.py`
  Produce: exit code 0

- [ ] T4: En `horarios.py`, leer el query param `escenario` y preseleccionar ese
          escenario tras `_cargar_escenarios()` (con manejo de valor inválido).
  Verifica: `python scripts/check_imports.py --layer interface`
  Produce: `src/interface/pages/academico/horarios.py`

- [ ] T5: Verificar entorno completo.
  Verifica: `python init.py`
  Produce: todos los checks verdes, sin regresiones de tests
