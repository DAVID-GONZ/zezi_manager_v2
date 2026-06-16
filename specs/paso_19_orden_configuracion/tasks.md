# Tasks: Orden de configuración y panel de Preparación (paso_19_orden_configuracion)

> Los validadores son lógica pura de servicio; el panel se reubica en la página única
> de paso_18 cuando exista. No rompe flujos actuales (R8).

- [x] T1: Modelo `PlanEstudios` (por grado) + DTOs de preparación; tabla
          `plan_estudios` (DDL en `schema.py`, **sin migración**; recrear BD con seed)
          y repo; `PlanEstudiosService` con `horas_por_grado` / `horas_por_grupo`
          (fallback al `horas_semanales` global).
  Archivos: `infraestructura.py`, `infraestructura_repo.py`, `schema.py`, `seed.py`,
  `sqlite_infraestructura_repo.py`, `plan_estudios_service.py`, `container.py`.
  Verifica: `python init.py` ✅ 920 passed (2026-06-14)

- [x] T2: `PreparacionHorarioService.validar(...)` con las 7 puertas de R3 y
          `puede_generar(...)`; registrar en `container.py`.
  Archivo: `preparacion_horario_service.py` con `PuertaDTO`, `ReportePreparacionDTO`.
  Puertas: año_periodo_ok, asignaturas_con_horas, horas_grupo_vs_slots,
  capacidad_docente, cobertura_asignaciones, plantilla_suficiente, salas_suficientes.
  Verifica: `python init.py` ✅ 920 passed (2026-06-14)

- [x] T3: Validación al vuelo de carga docente en `AsignacionService.crear_asignacion`
          (R4), con mensaje accionable. Nuevos params `usuario_repo` e `infra_repo`.
  Verifica: `python init.py` ✅ 920 passed (2026-06-14)

- [x] T4: Panel "Preparación" (puertas verde/roja/ámbar + enlaces de corrección +
          Generar deshabilitado si hay duras en rojo). Integrado como sección Preparar
          en `horarios_hub.py` con `_render_preparar()` completo.
  Verifica: `python init.py` ✅ design system OK (2026-06-14)

- [x] T5: Verificación completa y no-regresión.
  Resultado: `python init.py` → ✅ ENTORNO OK — 920 passed, 1 skipped (2026-06-14)
  Verifica: `python init.py` ✅ · `python -m pytest -q` ✅

> Dependencia: la puerta de salas (R3.7) requiere el modelo de salas de paso_17; hasta
> entonces se reporta como advertencia neutra.
