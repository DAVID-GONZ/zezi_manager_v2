# Tasks: Huella en infraestructura, horarios, salas y franjas (obs_04b)

- [ ] T1: Modificar `InfraestructuraService.__init__` para aceptar
      `auditoria_repo: IAuditoriaRepository | None = None` y almacenarlo en
      `self._auditoria_repo`. Actualizar los 4 métodos de factoría lazy
      (`_sala_service`, `_franja_service`, `_escenario_horario_service`,
      `_restriccion_generacion_service`) para pasar `auditoria_repo=self._auditoria_repo`
      al construir el sub-servicio.
  Verifica: `python scripts/init.py` (no nuevos errores de import)
  Produce: `src/services/infraestructura_service.py` modificado

- [ ] T2: Cablear `auditoria_repo=Container.auditoria_repo()` en las dos
      construcciones directas de `container.py`: `InfraestructuraService(...)` y
      `HorarioService(...)`.
  Verifica: `python scripts/init.py`
  Produce: `container.py` modificado

- [ ] T3: Modificar `EscenarioHorarioService.__init__` para aceptar `auditoria_repo`.
      Añadir `auditar_cambio` en los 7 métodos mutadores según la tabla §4 del
      diseño (crear_escenario, crear_escenario_simple, actualizar_escenario,
      renombrar_escenario, activar_escenario, eliminar_escenario, duplicar_escenario).
  Verifica: `python -m pytest tests/unit/ -q -k escenario`
  Produce: `src/services/escenario_horario_service.py` modificado

- [ ] T4: Modificar `SalaService.__init__` para aceptar `auditoria_repo`. Añadir
      `auditar_cambio` en 4 métodos: `crear_sala` (CREATE), `actualizar_sala`
      (UPDATE — anterior ya disponible), `eliminar_sala` (DELETE — anterior vía
      `_verificar_pertenencia_obj`), `asignar_sala_a_grupo` (UPDATE).
  Verifica: `python -m pytest tests/unit/ -q -k sala`
  Produce: `src/services/sala_service.py` modificado

- [ ] T5: Modificar `FranjaService.__init__` para aceptar `auditoria_repo`. Añadir
      `auditar_cambio` en 4 métodos: `crear_plantilla_simple` (CREATE),
      `guardar_franjas` (UPDATE resumen con n_franjas), `activar_plantilla`
      (UPDATE), `eliminar_plantilla` (DELETE — anterior vía
      `_verificar_pertenencia_obj`).
  Verifica: `python -m pytest tests/unit/ -q -k franja`
  Produce: `src/services/franja_service.py` modificado

- [ ] T6: Modificar `RestriccionGeneracionService.__init__` para aceptar
      `auditoria_repo`. Añadir `auditar_cambio` en los 17 métodos mutadores
      según la tabla §7 del diseño:
      - Sin `@requiere_escritura`: `bloquear_franjas_docente` (CREATE resumen),
        `limpiar_disponibilidad_docente` (DELETE resumen).
      - Con `@requiere_escritura`: `guardar_disponibilidad_docente`,
        `crear_config_generacion`, `actualizar_config_generacion`,
        `eliminar_config_generacion`, `cambiar_estado_config`,
        `duplicar_config_generacion`, `crear_ventana_grupo`,
        `eliminar_ventana_grupo`, `crear_bloque_anclado`, `eliminar_bloque_anclado`,
        `crear_franja_reunion`, `actualizar_franja_reunion`, `eliminar_franja_reunion`,
        `set_limites_docente`, `set_limites_docente_simple`.
  Verifica: `python -m pytest tests/unit/ -q -k restriccion`
  Produce: `src/services/restriccion_generacion_service.py` modificado

- [ ] T7: Modificar `HorarioService.__init__` para aceptar `auditoria_repo`.
      Añadir `auditar_cambio` en 4 métodos: `crear_bloque` (CREATE),
      `mover_bloque` (UPDATE — anterior cargado en línea 161), `actualizar_bloque`
      (UPDATE — anterior cargado en línea 196), `eliminar_bloque` (DELETE — cargar
      bloque antes de eliminar si se quiere el anterior).
  Verifica: `python -m pytest tests/unit/ -q -k horario`
  Produce: `src/services/horario_service.py` modificado

- [ ] T8: Verificar qué entradas de los 6 servicios aparecen actualmente en
      `SERVICIOS_SIN_HUELLA_DEUDA` ejecutando `python scripts/check_auditoria.py`.
      Retirar las entradas que check_auditoria marque como ya cubiertas (las 5 sub-
      servicios activos + infraestructura_service si check_auditoria la incluye).
  Verifica: `python scripts/check_auditoria.py` → exit code 0
  Produce: `scripts/check_auditoria.py` modificado

- [ ] T9: Añadir tests de integración representativos (uno por sub-servicio) en
      `tests/integration/test_huella_cobertura.py`:
      - EscenarioHorarioService: `crear_escenario` → `audit_log` crece.
      - SalaService: `crear_sala` → `audit_log` crece.
      - FranjaService: `crear_plantilla_simple` → `audit_log` crece.
      - RestriccionGeneracionService: `crear_config_generacion` → `audit_log` crece.
      - HorarioService: `crear_bloque` → `audit_log` crece.
  Verifica: `python -m pytest tests/integration/test_huella_cobertura.py -q`
  Produce: `test_huella_cobertura.py` modificado, verde

- [ ] T10: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Crear un escenario de horario desde la UI → confirmar fila en `audit_log` con
  `tabla="escenarios_horario"`, `accion="CREATE"`, `usuario_id` e `institucion_id`
  no nulos.
- Guardar una disponibilidad de docente → confirmar fila resumen en `audit_log`
  con `tabla="disponibilidad_docente"`.
- Crear un bloque en el editor de horario → confirmar `tabla="horarios"` en
  `audit_log`.
- `python scripts/check_auditoria.py` no lista ninguno de los seis servicios.
