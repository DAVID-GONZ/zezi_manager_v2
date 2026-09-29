# Estructura del proyecto — zeci_manager_v2

> Generado automáticamente por `scripts/generar_estructura.py`
> Fecha: 2026-09-28 23:54
> Raíz: `C:\Users\579j\Documents\DOCUMENTOS_B\Proyecto_Control_Asitencia\app_v2\zeci_manager_v2`

**Excluidas (caché/entornos):** *.egg-info, .claude, .git, .mypy_cache, .nicegui, .pytest_cache, .ruff_cache, .tox, .venv, .vscode, __pycache__, build, dist, node_modules
**Excluidas (ruido de proceso):** progress, roadmaps, specs, tests ← ver `estructura_tests.md`

---

```
zeci_manager_v2/
├── 📁 **data/**
│   └── app.db
├── 📁 **deploy/**
│   ├── 📁 **caddy/**
│   │   └── Caddyfile
│   └── 📁 **nginx/**
│       └── zeci.conf
├── 📁 **docs/**
│   ├── 📁 **api_reference/**
│   │   ├── dominio_modelos.md
│   │   ├── dominio_politicas.md
│   │   ├── dominio_puertos.md
│   │   ├── infraestructura.md
│   │   └── servicios.md
│   ├── 📁 **design_system/**
│   │   ├── components.md
│   │   ├── portability_audit.md
│   │   └── portability_test.html
│   ├── api_reference.md
│   ├── architecture.md
│   ├── conventions.md
│   ├── decisions.md
│   ├── deploy.md
│   ├── dominio.md
│   ├── estructura_proyecto.md
│   ├── estructura_tests.md
│   ├── infraestructura.md
│   ├── modelos.md
│   ├── page_patterns.md
│   ├── repositorio.md
│   ├── schema.md
│   ├── seguridad.md
│   ├── services.md
│   ├── verificacion_bitacora.md
│   └── verification.md
├── 📁 **logs/**
│   └── security.log
├── 📁 **openapi/**
│   └── avedra-openapi.json
├── 📁 **scripts/**
│   ├── audit_css_portability.py
│   ├── check_auditoria.py
│   ├── check_enums.py
│   ├── export_openapi.py
│   ├── extract_component_info.py
│   ├── generar_estructura.py
│   ├── init.py
│   ├── run_tests.py
│   └── sync_tokens.py
├── 📁 **src/**
│   ├── 📁 **api/**
│   │   ├── 📁 **routes/**
│   │   │   ├── __init__.py
│   │   │   ├── asistencia.py
│   │   │   ├── auditoria.py
│   │   │   ├── configuracion.py
│   │   │   ├── contexto.py
│   │   │   ├── convivencia.py
│   │   │   ├── estudiantes.py
│   │   │   ├── evaluacion.py
│   │   │   ├── informes.py
│   │   │   └── usuarios.py
│   │   ├── 📁 **schemas/**
│   │   │   ├── __init__.py
│   │   │   ├── asistencia.py
│   │   │   ├── auditoria.py
│   │   │   ├── auth.py
│   │   │   ├── common.py
│   │   │   ├── configuracion.py
│   │   │   ├── contexto.py
│   │   │   ├── convivencia.py
│   │   │   ├── estudiantes.py
│   │   │   ├── evaluacion.py
│   │   │   ├── informes.py
│   │   │   └── usuarios.py
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── deps.py
│   │   ├── errors.py
│   │   ├── router.py
│   │   └── security.py
│   ├── 📁 **domain/**
│   │   ├── 📁 **models/**
│   │   │   ├── __init__.py
│   │   │   ├── acudiente.py
│   │   │   ├── alerta.py
│   │   │   ├── asignacion.py
│   │   │   ├── asistencia.py
│   │   │   ├── auditoria.py
│   │   │   ├── base.py
│   │   │   ├── busqueda.py
│   │   │   ├── catalogos_estandar.py
│   │   │   ├── cierre.py
│   │   │   ├── clock.py
│   │   │   ├── configuracion.py
│   │   │   ├── convivencia.py
│   │   │   ├── decimal_types.py
│   │   │   ├── dtos.py
│   │   │   ├── estudiante.py
│   │   │   ├── evaluacion.py
│   │   │   ├── habilitacion.py
│   │   │   ├── infraestructura.py
│   │   │   ├── institucion.py
│   │   │   ├── nivelacion.py
│   │   │   ├── observabilidad.py
│   │   │   ├── periodo.py
│   │   │   ├── piar.py
│   │   │   ├── plan_mejoramiento.py
│   │   │   ├── preferencia_institucion.py
│   │   │   ├── scheduling.py
│   │   │   ├── tenant.py
│   │   │   └── usuario.py
│   │   ├── 📁 **policies/**
│   │   │   ├── __init__.py
│   │   │   ├── alerta_ip.py
│   │   │   ├── audit_chain.py
│   │   │   ├── login_throttle.py
│   │   │   ├── password_policy.py
│   │   │   ├── rbac_auditoria.py
│   │   │   ├── rbac_convivencia.py
│   │   │   ├── rbac_usuarios.py
│   │   │   └── severidad_evento.py
│   │   ├── 📁 **ports/**
│   │   │   ├── __init__.py
│   │   │   ├── acudiente_repo.py
│   │   │   ├── alerta_repo.py
│   │   │   ├── asignacion_repo.py
│   │   │   ├── asistencia_repo.py
│   │   │   ├── auditoria_repo.py
│   │   │   ├── cierre_repo.py
│   │   │   ├── configuracion_repo.py
│   │   │   ├── convivencia_repo.py
│   │   │   ├── estadisticos_repo.py
│   │   │   ├── estudiante_repo.py
│   │   │   ├── evaluacion_repo.py
│   │   │   ├── habilitacion_repo.py
│   │   │   ├── infraestructura_repo.py
│   │   │   ├── institucion_repo.py
│   │   │   ├── log_reader.py
│   │   │   ├── nivelacion_repo.py
│   │   │   ├── periodo_repo.py
│   │   │   ├── plan_mejoramiento_repo.py
│   │   │   ├── portal_provider.py
│   │   │   ├── preferencias_repo.py
│   │   │   ├── security_logger.py
│   │   │   ├── service_ports.py
│   │   │   ├── siee_repo.py
│   │   │   └── usuario_repo.py
│   │   ├── exceptions.py
│   │   ├── modulos.py
│   │   └── tablas_auditables.py
│   ├── 📁 **infrastructure/**
│   │   ├── 📁 **auth/**
│   │   │   ├── __init__.py
│   │   │   ├── bcrypt_auth_service.py
│   │   │   └── jwt_handler.py
│   │   ├── 📁 **context/**
│   │   │   ├── __init__.py
│   │   │   ├── context_initializer.py
│   │   │   ├── contexto_actor.py
│   │   │   ├── contexto_tenant.py
│   │   │   └── solo_lectura.py
│   │   ├── 📁 **db/**
│   │   │   ├── 📁 **repositories/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── sqla_acudiente_repo.py
│   │   │   │   ├── sqla_alerta_repo.py
│   │   │   │   ├── sqla_asignacion_repo.py
│   │   │   │   ├── sqla_asistencia_repo.py
│   │   │   │   ├── sqla_auditoria_repo.py
│   │   │   │   ├── sqla_cierre_repo.py
│   │   │   │   ├── sqla_configuracion_repo.py
│   │   │   │   ├── sqla_convivencia_repo.py
│   │   │   │   ├── sqla_estadisticos_repo.py
│   │   │   │   ├── sqla_estudiante_repo.py
│   │   │   │   ├── sqla_evaluacion_repo.py
│   │   │   │   ├── sqla_habilitacion_repo.py
│   │   │   │   ├── sqla_infraestructura_repo.py
│   │   │   │   ├── sqla_institucion_repo.py
│   │   │   │   ├── sqla_nivelacion_repo.py
│   │   │   │   ├── sqla_periodo_repo.py
│   │   │   │   ├── sqla_plan_mejoramiento_repo.py
│   │   │   │   ├── sqla_preferencias_repo.py
│   │   │   │   ├── sqla_siee_repo.py
│   │   │   │   └── sqla_usuario_repo.py
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   ├── queries.py
│   │   │   ├── schema.py
│   │   │   └── seed.py
│   │   ├── 📁 **exporters/**
│   │   │   ├── __init__.py
│   │   │   ├── boletin_pdf.py
│   │   │   ├── exporter_factory.py
│   │   │   ├── null_exporter.py
│   │   │   ├── observador_excel.py
│   │   │   ├── observador_pdf.py
│   │   │   ├── openpyxl_exporter.py
│   │   │   └── pdf_exporter.py
│   │   ├── 📁 **logging/**
│   │   │   ├── __init__.py
│   │   │   ├── jsonl_log_reader.py
│   │   │   └── security_logger.py
│   │   └── 📁 **notifications/**
│   │       ├── __init__.py
│   │       ├── log_notification_service.py
│   │       └── null_notification_service.py
│   ├── 📁 **interface/**
│   │   ├── 📁 **auth/**
│   │   │   ├── __init__.py
│   │   │   └── route_guard.py
│   │   ├── 📁 **context/**
│   │   │   ├── __init__.py
│   │   │   ├── event_context.py
│   │   │   ├── eventos_sesion.py
│   │   │   ├── request_ip.py
│   │   │   └── session_context.py
│   │   ├── 📁 **design/**
│   │   │   ├── 📁 **components/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── activity_feed.py
│   │   │   │   ├── alerts_panel.py
│   │   │   │   ├── base_form.py
│   │   │   │   ├── buttons.py
│   │   │   │   ├── confirm_dialog.py
│   │   │   │   ├── confirmation_card.py
│   │   │   │   ├── counter_card.py
│   │   │   │   ├── custom_dialog.py
│   │   │   │   ├── data_table.py
│   │   │   │   ├── date_input.py
│   │   │   │   ├── empty_state.py
│   │   │   │   ├── followup_panel.py
│   │   │   │   ├── form_dialog.py
│   │   │   │   ├── form_fields.py
│   │   │   │   ├── greeting_hero.py
│   │   │   │   ├── groups_attention.py
│   │   │   │   ├── historial_cambios.py
│   │   │   │   ├── inline_selectors.py
│   │   │   │   ├── milestones_panel.py
│   │   │   │   ├── mini_chart.py
│   │   │   │   ├── page_header.py
│   │   │   │   ├── pending_items.py
│   │   │   │   ├── performance_indicator.py
│   │   │   │   ├── period_status.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── section_panel.py
│   │   │   │   ├── skeleton_loader.py
│   │   │   │   ├── stat_card.py
│   │   │   │   ├── stats_grid.py
│   │   │   │   ├── status_badge.py
│   │   │   │   └── toast.py
│   │   │   ├── 📁 **styles/**
│   │   │   │   ├── 📁 **adapter/**
│   │   │   │   │   ├── aggrid.css
│   │   │   │   │   └── quasar.css
│   │   │   │   ├── 📁 **components/**
│   │   │   │   │   ├── badges.css
│   │   │   │   │   ├── buttons.css
│   │   │   │   │   ├── cards.css
│   │   │   │   │   ├── counter-card.css
│   │   │   │   │   ├── date_input.css
│   │   │   │   │   ├── dialogs.css
│   │   │   │   │   ├── empty_state.css
│   │   │   │   │   ├── flujo.css
│   │   │   │   │   ├── forms.css
│   │   │   │   │   ├── historial.css
│   │   │   │   │   ├── impersonation.css
│   │   │   │   │   ├── inline_selectors.css
│   │   │   │   │   ├── marketing.css
│   │   │   │   │   ├── password_change.css
│   │   │   │   │   ├── skeleton_loader.css
│   │   │   │   │   ├── tables.css
│   │   │   │   │   ├── theme-toggle.css
│   │   │   │   │   └── toast.css
│   │   │   │   ├── 📁 **domain/**
│   │   │   │   │   ├── asistencia.css
│   │   │   │   │   ├── convivencia.css
│   │   │   │   │   ├── desempeno.css
│   │   │   │   │   ├── disponibilidad.css
│   │   │   │   │   ├── horario_generar.css
│   │   │   │   │   └── horario_parrilla.css
│   │   │   │   ├── 📁 **layout/**
│   │   │   │   │   ├── content.css
│   │   │   │   │   ├── sidebar.css
│   │   │   │   │   ├── spacing.css
│   │   │   │   │   └── topbar.css
│   │   │   │   ├── 📁 **pages/**
│   │   │   │   │   ├── buscar.css
│   │   │   │   │   └── wizard_configuracion.css
│   │   │   │   ├── 📁 **themes/**
│   │   │   │   │   └── dark.css
│   │   │   │   ├── CLASS_CONTRACT.md
│   │   │   │   ├── PORTABILITY.md
│   │   │   │   ├── reset.css
│   │   │   │   ├── tokens.css
│   │   │   │   ├── tokens.json
│   │   │   │   ├── tokens.py
│   │   │   │   ├── tokens.ts
│   │   │   │   └── typography.css
│   │   │   ├── __init__.py
│   │   │   ├── layout.py
│   │   │   └── theme.py
│   │   ├── 📁 **pages/**
│   │   │   ├── 📁 **academico/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── estudiantes.py
│   │   │   │   ├── horarios_hub.py
│   │   │   │   ├── parrilla_widget.py
│   │   │   │   ├── plantilla_editor_widget.py
│   │   │   │   ├── registro_asistencia.py
│   │   │   │   └── tablero_estadisticos.py
│   │   │   ├── 📁 **admin/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── asignaciones.py
│   │   │   │   ├── asignaturas.py
│   │   │   │   ├── auditoria.py
│   │   │   │   ├── catalogo_instituciones.py
│   │   │   │   ├── configuracion_sie.py
│   │   │   │   ├── diagnostico.py
│   │   │   │   ├── disponibilidad_docente.py
│   │   │   │   ├── grupos.py
│   │   │   │   ├── observabilidad.py
│   │   │   │   ├── plan_estudios.py
│   │   │   │   ├── salas.py
│   │   │   │   └── usuarios.py
│   │   │   ├── 📁 **convivencia/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── _shared_observacion_form.py
│   │   │   │   ├── alertas.py
│   │   │   │   ├── categorias.py
│   │   │   │   ├── comportamiento.py
│   │   │   │   ├── configuracion_alertas.py
│   │   │   │   ├── configuracion_convivencia.py
│   │   │   │   ├── notas_convivencia.py
│   │   │   │   ├── observaciones.py
│   │   │   │   ├── plantillas.py
│   │   │   │   ├── reporte_periodo.py
│   │   │   │   └── seguimiento.py
│   │   │   ├── 📁 **director/**
│   │   │   │   ├── __init__.py
│   │   │   │   └── gestion_usuarios.py
│   │   │   ├── 📁 **evaluacion/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cierre_anio.py
│   │   │   │   ├── cierre_periodo.py
│   │   │   │   ├── configuracion_evaluacion.py
│   │   │   │   ├── habilitaciones.py
│   │   │   │   ├── planes_mejoramiento.py
│   │   │   │   └── planilla_notas.py
│   │   │   ├── 📁 **informes/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── boletin_anual.py
│   │   │   │   ├── boletin_periodo.py
│   │   │   │   ├── consolidado_asistencia.py
│   │   │   │   ├── consolidado_notas.py
│   │   │   │   └── estadisticos.py
│   │   │   ├── 📁 **institucion/**
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auditoria.py
│   │   │   │   └── hub_institucion.py
│   │   │   ├── __init__.py
│   │   │   ├── buscar.py
│   │   │   ├── cambiar_password.py
│   │   │   ├── configuracion_inicial.py
│   │   │   ├── espera_configuracion.py
│   │   │   ├── inicio.py
│   │   │   ├── landing.py
│   │   │   ├── login.py
│   │   │   └── mi_cuenta_password.py
│   │   └── 📁 **presenters/**
│   │       ├── 📁 **academico/**
│   │       │   ├── __init__.py
│   │       │   ├── estudiantes_presenter.py
│   │       │   ├── horarios_hub_presenter.py
│   │       │   ├── registro_asistencia_presenter.py
│   │       │   └── tablero_estadisticos_presenter.py
│   │       ├── 📁 **admin/**
│   │       │   ├── __init__.py
│   │       │   ├── asignaciones_presenter.py
│   │       │   ├── asignaturas_presenter.py
│   │       │   ├── auditoria_presenter.py
│   │       │   ├── catalogo_instituciones_presenter.py
│   │       │   ├── configuracion_sie_presenter.py
│   │       │   ├── disponibilidad_docente_presenter.py
│   │       │   ├── grupos_presenter.py
│   │       │   ├── historial_presenter.py
│   │       │   ├── observabilidad_presenter.py
│   │       │   ├── plan_estudios_presenter.py
│   │       │   ├── salas_presenter.py
│   │       │   └── usuarios_presenter.py
│   │       ├── 📁 **convivencia/**
│   │       │   ├── __init__.py
│   │       │   ├── alertas_presenter.py
│   │       │   ├── configuracion_alertas_presenter.py
│   │       │   ├── configuracion_convivencia_presenter.py
│   │       │   ├── notas_convivencia_presenter.py
│   │       │   ├── observaciones_presenter.py
│   │       │   ├── reporte_periodo_presenter.py
│   │       │   └── seguimiento_presenter.py
│   │       ├── 📁 **director/**
│   │       │   ├── __init__.py
│   │       │   └── gestion_usuarios_presenter.py
│   │       ├── 📁 **evaluacion/**
│   │       │   ├── __init__.py
│   │       │   ├── cierre_anio_presenter.py
│   │       │   ├── cierre_periodo_presenter.py
│   │       │   ├── habilitaciones_presenter.py
│   │       │   ├── planes_mejoramiento_presenter.py
│   │       │   └── planilla_notas_presenter.py
│   │       ├── 📁 **informes/**
│   │       │   ├── __init__.py
│   │       │   ├── boletin_presenter.py
│   │       │   ├── consolidado_presenter.py
│   │       │   └── estadisticos_presenter.py
│   │       ├── 📁 **institucion/**
│   │       │   ├── __init__.py
│   │       │   ├── auditoria_presenter.py
│   │       │   └── hub_institucion_presenter.py
│   │       ├── __init__.py
│   │       └── buscar_presenter.py
│   ├── 📁 **reference/**
│   │   ├── __init__.py
│   │   └── divipola.py
│   └── 📁 **services/**
│       ├── 📁 **portal/**
│       │   ├── __init__.py
│       │   ├── convivencia_provider.py
│       │   └── evaluacion_provider.py
│       ├── __init__.py
│       ├── acudiente_service.py
│       ├── alerta_service.py
│       ├── aprovisionamiento_institucion_service.py
│       ├── asignacion_service.py
│       ├── asistencia_service.py
│       ├── auditoria_export_service.py
│       ├── auditoria_helpers.py
│       ├── auditoria_retencion_service.py
│       ├── auditoria_service.py
│       ├── busqueda_service.py
│       ├── catalogo_academico_service.py
│       ├── cierre_service.py
│       ├── configuracion_service.py
│       ├── convivencia_service.py
│       ├── escenario_horario_service.py
│       ├── estadisticos_service.py
│       ├── estudiante_service.py
│       ├── evaluacion_service.py
│       ├── franja_service.py
│       ├── generador_horario_service.py
│       ├── habilitacion_service.py
│       ├── horario_service.py
│       ├── informe_service.py
│       ├── infraestructura_service.py
│       ├── institucion_service.py
│       ├── nivelacion_service.py
│       ├── observabilidad_service.py
│       ├── periodo_service.py
│       ├── plan_estudios_service.py
│       ├── plan_mejoramiento_service.py
│       ├── portal_resumen_service.py
│       ├── preferencias_institucion_service.py
│       ├── preparacion_horario_service.py
│       ├── restriccion_generacion_service.py
│       ├── sala_service.py
│       └── usuario_service.py
├── AGENTS.md
├── CHECKPOINTS.md
├── CLAUDE.md
├── config.py
├── container.py
├── Dockerfile
├── main.py
├── pyproject.toml
├── render.yaml
├── requirements.txt
├── step_list.json
└── tokens.json
```


---

## Estadísticas rápidas

- **Total archivos:** 421
- **Por extensión:**
  - `.py`: 342
  - `.css`: 36
  - `.md`: 29
  - `.json`: 4
  - `(sin extensión)`: 2
  - `.toml`: 1
  - `.yaml`: 1
  - `.txt`: 1
  - `.db`: 1
  - `.log`: 1
  - `.conf`: 1
  - `.html`: 1
  - `.ts`: 1
