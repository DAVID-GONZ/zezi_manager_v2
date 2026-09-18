# Tasks: Huella en config, catálogos y planes (obs_04c)

- [ ] T1: Añadir `auditoria_repo: IAuditoriaRepository | None = None` al
      `__init__` de los siete servicios:
      `CatalogoAcademicoService`, `ConfiguracionService`,
      `PlanEstudiosService`, `InstitucionService`,
      `PlanMejoramientoService`, `NivelacionService`,
      `AprovisionamientoInstitucionService`.
      Ningún caller existente se rompe (parámetro opcional con default None).
  Verifica: `python scripts/init.py` (no nuevos errores de import ni firma)
  Produce: los siete servicios modificados

- [ ] T2: Cablear `auditoria_repo=Container.auditoria_repo()` en los siete
      constructores de `container.py`.
  Verifica: `python scripts/init.py`
  Produce: `container.py` modificado

- [ ] T3: Añadir `auditar_cambio` en los 11 métodos mutadores de
      `CatalogoAcademicoService` según la tabla §3 del diseño:
      - CREATE: `guardar_area`, `guardar_asignatura`, `guardar_grupo`.
      - UPDATE: `actualizar_area`, `set_color_area`, `actualizar_asignatura`,
        `actualizar_grupo`, `asignar_director_grupo`.
      - DELETE: `eliminar_area`, `eliminar_asignatura`, `eliminar_grupo`.
  Verifica: `python -m pytest tests/unit/ -q -k catalogo`
  Produce: `src/services/catalogo_academico_service.py` modificado

- [ ] T4: Añadir `auditar_cambio` en los 8 métodos mutadores propios de
      `ConfiguracionService` según la tabla §4 del diseño.
      Cuidar que `actualizar_info_institucional` y
      `sincronizar_snapshot_desde_institucion` se excluyen (R5).
      - CREATE: `crear_anio`, `agregar_nivel`.
      - UPDATE: `activar_anio`, `configurar_niveles` (batch resumen),
        `actualizar_nivel`, `guardar_criterios`, `actualizar_configuracion_academica`.
      - DELETE: `eliminar_nivel`.
  Verifica: `python -m pytest tests/unit/ -q -k configuracion`
  Produce: `src/services/configuracion_service.py` modificado

- [ ] T5: Añadir `auditar_cambio` en los 4 métodos mutadores propios de
      `PlanEstudiosService` según la tabla §5 del diseño.
      Cuidar que `set_horas` se excluye (delega en `actualizar`).
      - CREATE: `guardar_grado`, `actualizar`.
      - DELETE: `eliminar_grado`, `eliminar`.
  Verifica: `python -m pytest tests/unit/ -q -k plan_estudios`
  Produce: `src/services/plan_estudios_service.py` modificado

- [ ] T6: Añadir `auditar_cambio` en los 3 métodos mutadores de
      `InstitucionService` según la tabla §6 del diseño:
      - CREATE: `crear`.
      - UPDATE: `actualizar` (anterior ya cargado en el método),
        `marcar_configuracion_inicial_completa`.
  Verifica: `python -m pytest tests/unit/ -q -k institucion`
  Produce: `src/services/institucion_service.py` modificado

- [ ] T7: Añadir `auditar_cambio` en los 4 métodos mutadores de
      `PlanMejoramientoService` según la tabla §7 del diseño:
      - CREATE: `ejecutar_corte` (resumen: `nuevo={"asignacion_id": ...,
        "periodo_id": ..., "n_estudiantes": len(estudiantes)}`),
        `agregar_actividad`.
      - CREATE: `calificar_nota` (UPSERT, usar CREATE).
      - UPDATE: `cerrar_plan_estudiante`.
  Verifica: `python -m pytest tests/unit/ -q -k plan_mejoramiento`
  Produce: `src/services/plan_mejoramiento_service.py` modificado

- [ ] T8: Añadir `auditar_cambio` en los 3 métodos mutadores de
      `NivelacionService` según la tabla §8 del diseño:
      - CREATE: `agregar_actividad` (resumen: `nuevo={"asignacion_id": ...,
        "n_estudiantes": len(estudiante_ids)}`), `calificar_nota` (UPSERT,
        usar CREATE).
      - UPDATE: `cerrar_nivelacion`.
  Verifica: `python -m pytest tests/unit/ -q -k nivelacion`
  Produce: `src/services/nivelacion_service.py` modificado

- [ ] T9: Añadir `auditar_cambio` en el único método mutador propio de
      `AprovisionamientoInstitucionService`:
      - CREATE: `crear_institucion_con_director` — tabla `instituciones`,
        `registro_id=inst.id`, `nuevo=inst.model_dump()`.
      Cuidar que `finalizar_configuracion_inicial` se excluye (delega).
  Verifica: `python -m pytest tests/unit/ -q -k aprovisionamiento`
  Produce: `src/services/aprovisionamiento_institucion_service.py` modificado

- [ ] T10: Verificar qué entradas de los siete servicios siguen apareciendo
       en `SERVICIOS_SIN_HUELLA_DEUDA` ejecutando
       `python scripts/check_auditoria.py`.
       Vaciar el dict completamente retirando todas las entradas restantes.
  Verifica: `python scripts/check_auditoria.py` → exit code 0
  Produce: `scripts/check_auditoria.py` modificado con `SERVICIOS_SIN_HUELLA_DEUDA = {}`

- [ ] T11: Añadir tests de integración representativos (uno por servicio) en
       `tests/integration/test_huella_cobertura.py`:
       - CatalogoAcademicoService: `guardar_area` → `audit_log` crece.
       - ConfiguracionService: `crear_anio` → `audit_log` crece.
       - PlanEstudiosService: `guardar_grado` → `audit_log` crece.
       - InstitucionService: `crear` → `audit_log` crece.
       - PlanMejoramientoService: `agregar_actividad` → `audit_log` crece.
       - NivelacionService: `agregar_actividad` → `audit_log` crece.
       - AprovisionamientoInstitucionService: `crear_institucion_con_director`
         → `audit_log` crece con `tabla="instituciones"`.
  Verifica: `python -m pytest tests/integration/test_huella_cobertura.py -q`
  Produce: `test_huella_cobertura.py` modificado, verde

- [ ] T12: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Crear un área desde la UI → confirmar fila en `audit_log` con
  `tabla="areas"`, `accion="CREATE"`, `usuario_id` e `institucion_id`
  no nulos.
- Crear un año lectivo → confirmar fila en `audit_log` con
  `tabla="configuracion_anio"`, `accion="CREATE"`.
- Ejecutar un corte de plan de mejoramiento → confirmar fila resumen en
  `audit_log` con `tabla="cortes_plan"` y el campo `n_estudiantes` en
  `datos_nuevo`.
- `python scripts/check_auditoria.py` termina sin listar ningún servicio y
  con `SERVICIOS_SIN_HUELLA_DEUDA = {}`.
