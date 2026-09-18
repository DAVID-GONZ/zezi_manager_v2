# Tasks: Huella en convivencia y asistencia (obs_04a)

- [ ] T1: Añadir `auditoria_repo: IAuditoriaRepository | None = None` al
      `__init__` de `ConvivenciaService`, `AsistenciaService` y `AlertaService`.
      Ningún caller existente se rompe (parámetro opcional con default None).
  Verifica: `python scripts/init.py` (no nuevos errores de import ni firma)
  Produce: los tres servicios modificados

- [ ] T2: Cablear `auditoria_repo=Container.auditoria_repo()` en los tres
      constructores de `container.py`.
  Verifica: `python scripts/init.py`
  Produce: `container.py` modificado

- [ ] T3: Añadir `auditar_cambio` en los 23 métodos mutadores de
      `ConvivenciaService` según la tabla de §3 del diseño:
      - CREATE: `registrar_observacion` (rama nueva), `registrar_comportamiento`,
        `registrar_nota_comportamiento` (rama nueva), `crear_tipo_situacion`,
        `crear_medida_pedagogica`, `crear_categoria`, `crear_plantilla`,
        `registrar_observacion_desde_plantilla` (rama nueva),
        `promover_observacion_a_plantilla`, `promover_a_comportamiento`,
        `crear_alerta_seguimiento_manual`, `agregar_entrada_seguimiento`.
      - UPDATE: `registrar_observacion` (rama actualiza), `notificar_acudiente`,
        `agregar_entrada_seguimiento` (actualización legacy del campo seguimiento),
        `registrar_nota_comportamiento` (rama actualiza),
        `actualizar_tipo_situacion`, `desactivar_tipo_situacion`,
        `actualizar_medida_pedagogica`, `desactivar_medida_pedagogica`,
        `actualizar_categoria`, `desactivar_categoria`,
        `actualizar_plantilla`, `desactivar_plantilla`,
        `registrar_observacion_desde_plantilla` (rama actualiza),
        `promover_a_comportamiento` (actualización de la observación enlazada).
      - DELETE: `eliminar_observacion`, `eliminar_registro`.
  Verifica: `python -m pytest tests/unit/services/ -q -k convivencia`
  Produce: `src/services/convivencia_service.py` modificado

- [ ] T4: Añadir `auditar_cambio` en los 2 métodos propios de `AsistenciaService`:
      - `registrar` → CREATE en `control_diario`.
      - `registrar_masivo` → CREATE resumen en `control_diario` con
        `nuevo={"grupo_id": ..., "asignacion_id": ..., "fecha": ..., "n_registros": n}`.
  Verifica: `python -m pytest tests/unit/services/ -q -k asistencia`
  Produce: `src/services/asistencia_service.py` modificado

- [ ] T5: Añadir `auditar_cambio` en los 5 métodos mutadores de `AlertaService`
      según la tabla de §5 del diseño.
  Verifica: `python -m pytest tests/unit/services/ -q -k alerta`
  Produce: `src/services/alerta_service.py` modificado

- [ ] T6: Retirar `convivencia_service`, `asistencia_service` y `alerta_service`
      de `SERVICIOS_SIN_HUELLA_DEUDA` en `scripts/check_auditoria.py`.
      Verificar que el doble filo de la puerta pase: la lista ya no debe contener
      entradas con huella, y los tres servicios ya no deben aparecer como deuda.
  Verifica: `python scripts/check_auditoria.py` → exit code 0
  Produce: `scripts/check_auditoria.py` modificado

- [ ] T7: Añadir tests de integración representativos (uno por servicio) en
      `tests/integration/test_huella_cobertura.py`:
      - ConvivenciaService: `registrar_comportamiento` → `audit_log` crece con
        `usuario_id` e `institucion_id` no nulos.
      - AsistenciaService: `registrar` → `audit_log` crece.
      - AlertaService: `configurar_alerta` → `audit_log` crece.
  Verifica: `python -m pytest tests/integration/test_huella_cobertura.py -q`
  Produce: `test_huella_cobertura.py` modificado, verde

- [ ] T8: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Crear un registro de comportamiento desde la UI → confirmar fila en `audit_log`
  con `tabla="registro_comportamiento"`, `accion="CREATE"`, `usuario_id` y
  `institucion_id` no nulos.
- Registrar asistencia masiva de un grupo → confirmar fila en `audit_log`
  con `tabla="control_diario"` y el conteo en `datos_nuevo`.
- `python scripts/check_auditoria.py` no lista ninguno de los tres servicios.
