# Tasks: Reparar la ejecución del generador (paso_16a_fix_generador_timer)

- [ ] T1: Eliminar el temporizador pre-creado (`_generar_config_timer`) en
          `src/interface/pages/academico/horario_generar.py` y reescribir el
          cuerpo de `_generar_config()` para crear `ui.timer(0.1, _trabajo, once=True)`
          dentro del clic, con guarda `if _s["generando"]: return` y `finally`
          que limpie `_s["generando"]`.
  Verifica: `python scripts/check_imports.py --layer interface`
  Produce: `src/interface/pages/academico/horario_generar.py`

- [ ] T2: Verificar que no quedan referencias colgantes al temporizador
          eliminado (`_generar_config_timer`) en el archivo.
  Verifica: `python scripts/check_design.py --file src/interface/pages/academico/horario_generar.py`
  Produce: exit code 0 y 0 ocurrencias de `_generar_config_timer`

- [ ] T3: Verificar entorno completo.
  Verifica: `python init.py`
  Produce: todos los checks verdes, sin regresiones de tests
