# Estructura de tests — zeci_manager_v2

> Generado automáticamente por `scripts/generar_estructura.py`
> Fecha: 2026-09-28 23:54

---

```
tests/
├── 📁 **e2e/**
│   ├── __init__.py
│   ├── conftest.py
│   ├── e2e_app.py
│   ├── test_asistencia.py
│   ├── test_flujos_smoke.py
│   ├── test_login.py
│   ├── test_matriz_rbac.py
│   ├── test_multitenant.py
│   └── test_ver_como.py
├── 📁 **integration/**
│   ├── __init__.py
│   ├── test_alertas_seguimiento.py
│   ├── test_asignacion_asignatura_horario.py
│   ├── test_asistencia_conteo.py
│   ├── test_convivencia_14_promocion_comportamiento.py
│   ├── test_convivencia_34_tipos_situacion.py
│   ├── test_convivencia_35_entradas_seguimiento.py
│   ├── test_convivencia_categorias.py
│   ├── test_disponibilidad_config_repo.py
│   ├── test_franjas_repo.py
│   ├── test_generacion_estres.py
│   ├── test_grupo_director_grupo.py
│   ├── test_health_endpoint.py
│   ├── test_horarios_integracion.py
│   ├── test_huella_actor.py
│   ├── test_huella_cobertura.py
│   ├── test_institucion_repo.py
│   ├── test_paso34_seed_segunda_institucion.py
│   ├── test_plan_mejoramiento_repo.py
│   ├── test_repositories.py
│   ├── test_scratch.py
│   ├── test_tenant_b1_grupos_asignaturas.py
│   ├── test_tenant_b2_estudiantes.py
│   ├── test_tenant_b3_asignaciones_evaluacion.py
│   ├── test_tenant_b4_salas_plantillas_convivencia.py
│   └── test_tenant_d_usuarios_login.py
├── 📁 **unit/**
│   ├── 📁 **api/**
│   │   ├── __init__.py
│   │   ├── test_api_auth.py
│   │   └── test_api_backend_12.py
│   ├── 📁 **design/**
│   │   ├── __init__.py
│   │   ├── test_tokens_roundtrip.py
│   │   └── test_tokens_sync.py
│   ├── 📁 **domain/**
│   │   ├── __init__.py
│   │   ├── test_alerta_ip.py
│   │   ├── test_alerta_piar_convivencia.py
│   │   ├── test_audit_chain.py
│   │   ├── test_cierre_periodo_infraestructura.py
│   │   ├── test_computed_fields.py
│   │   ├── test_configuracion_usuario_auditoria.py
│   │   ├── test_convivencia_models.py
│   │   ├── test_decimal_notas.py
│   │   ├── test_disponibilidad_config_model.py
│   │   ├── test_enums_schema.py
│   │   ├── test_escenario_model.py
│   │   ├── test_estudiante.py
│   │   ├── test_evaluacion.py
│   │   ├── test_exceptions.py
│   │   ├── test_fecha_zona_horaria.py
│   │   ├── test_franja_model.py
│   │   ├── test_habilitacion.py
│   │   ├── test_institucion.py
│   │   ├── test_institucion_enriquecida.py
│   │   ├── test_model_config.py
│   │   ├── test_modulos.py
│   │   ├── test_nivelacion.py
│   │   ├── test_observabilidad_models.py
│   │   ├── test_password_policy.py
│   │   ├── test_plan_mejoramiento.py
│   │   ├── test_portal_provider.py
│   │   ├── test_rbac_auditoria.py
│   │   ├── test_rbac_convivencia.py
│   │   ├── test_rbac_usuarios.py
│   │   ├── test_restricciones_str.py
│   │   ├── test_severidad_evento.py
│   │   ├── test_tablas_auditables.py
│   │   └── test_tenant_scope.py
│   ├── 📁 **infrastructure/**
│   │   ├── 📁 **exporters/**
│   │   │   ├── __init__.py
│   │   │   └── test_observador_pdf.py
│   │   ├── __init__.py
│   │   ├── test_auditoria_repo.py
│   │   ├── test_auditoria_volumen.py
│   │   ├── test_auth_service.py
│   │   ├── test_bcrypt_auth_service.py
│   │   ├── test_boletin_pdf.py
│   │   ├── test_context_initializer.py
│   │   ├── test_exporters.py
│   │   ├── test_jsonl_log_reader.py
│   │   ├── test_notification_service.py
│   │   ├── test_notification_services.py
│   │   ├── test_pdf_exporter_v2.py
│   │   ├── test_schema_integrity.py
│   │   ├── test_security_logger.py
│   │   └── test_tenant_filter_conformance.py
│   ├── 📁 **interface/**
│   │   ├── 📁 **auth/**
│   │   │   ├── __init__.py
│   │   │   ├── test_alias_roles.py
│   │   │   ├── test_gate_configuracion.py
│   │   │   ├── test_matriz_rutas_completa.py
│   │   │   └── test_route_guard.py
│   │   ├── 📁 **context/**
│   │   │   ├── __init__.py
│   │   │   ├── test_event_context.py
│   │   │   ├── test_request_ip.py
│   │   │   └── test_session_context_actor.py
│   │   ├── 📁 **design/**
│   │   │   ├── __init__.py
│   │   │   ├── test_counter_card_mini_chart.py
│   │   │   ├── test_empty_state.py
│   │   │   ├── test_navitems.py
│   │   │   ├── test_skeleton_loader.py
│   │   │   └── test_toast.py
│   │   ├── 📁 **presenters/**
│   │   │   ├── __init__.py
│   │   │   ├── test_alertas_presenter.py
│   │   │   ├── test_asignaciones_presenter.py
│   │   │   ├── test_asignaturas_presenter.py
│   │   │   ├── test_auditoria_institucional_presenter.py
│   │   │   ├── test_auditoria_presenter.py
│   │   │   ├── test_boletin_presenter.py
│   │   │   ├── test_buscar_presenter.py
│   │   │   ├── test_catalogo_instituciones_presenter.py
│   │   │   ├── test_cierre_anio_presenter.py
│   │   │   ├── test_cierre_periodo_presenter.py
│   │   │   ├── test_configuracion_alertas_presenter.py
│   │   │   ├── test_configuracion_convivencia_presenter.py
│   │   │   ├── test_configuracion_sie_presenter.py
│   │   │   ├── test_consolidado_presenter.py
│   │   │   ├── test_disponibilidad_docente_presenter.py
│   │   │   ├── test_estadisticos_presenter.py
│   │   │   ├── test_estudiantes_presenter.py
│   │   │   ├── test_grupos_presenter.py
│   │   │   ├── test_habilitaciones_presenter.py
│   │   │   ├── test_historial_presenter.py
│   │   │   ├── test_horarios_hub_presenter.py
│   │   │   ├── test_hub_institucion_presenter.py
│   │   │   ├── test_notas_convivencia_presenter.py
│   │   │   ├── test_observabilidad_presenter.py
│   │   │   ├── test_observaciones_presenter.py
│   │   │   ├── test_plan_estudios_presenter.py
│   │   │   ├── test_planes_mejoramiento_presenter.py
│   │   │   ├── test_planilla_notas_presenter.py
│   │   │   ├── test_presenters_puros.py
│   │   │   ├── test_registro_asistencia_presenter.py
│   │   │   ├── test_reporte_periodo_presenter.py
│   │   │   ├── test_salas_presenter.py
│   │   │   ├── test_seguimiento_presenter.py
│   │   │   ├── test_tablero_estadisticos_presenter.py
│   │   │   └── test_usuarios_presenter.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_emision_eventos.py
│   │   ├── test_horario_pages.py
│   │   ├── test_hub_institucion_smoke.py
│   │   ├── test_inicio_seguimientos.py
│   │   ├── test_inline_selectors.py
│   │   ├── test_parrilla_widget_logica.py
│   │   ├── test_planilla_notas_grid.py
│   │   ├── test_rbac_comportamiento_gating.py
│   │   └── test_rutas_raiz.py
│   ├── 📁 **services/**
│   │   ├── 📁 **portal/**
│   │   │   ├── __init__.py
│   │   │   └── test_pilotos.py
│   │   ├── __init__.py
│   │   ├── test_aislamiento_objeto_paso36.py
│   │   ├── test_alerta_service.py
│   │   ├── test_aprovisionamiento_service.py
│   │   ├── test_asignacion_service.py
│   │   ├── test_asistencia_conteo.py
│   │   ├── test_asistencia_service.py
│   │   ├── test_auditoria_diff.py
│   │   ├── test_auditoria_export.py
│   │   ├── test_auditoria_helpers.py
│   │   ├── test_auditoria_historial.py
│   │   ├── test_auditoria_retencion.py
│   │   ├── test_auditoria_service.py
│   │   ├── test_auditoria_verificacion_tramo.py
│   │   ├── test_busqueda_service.py
│   │   ├── test_catalogo_academico_autz_convivencia.py
│   │   ├── test_catalogo_academico_director_grupo.py
│   │   ├── test_cierre_service.py
│   │   ├── test_configuracion_service.py
│   │   ├── test_configuracion_snapshot.py
│   │   ├── test_contexto_actor.py
│   │   ├── test_contexto_tenant.py
│   │   ├── test_convivencia_service.py
│   │   ├── test_estadisticos_resumen.py
│   │   ├── test_estadisticos_service.py
│   │   ├── test_estudiante_service.py
│   │   ├── test_evaluacion_service.py
│   │   ├── test_generador_horario.py
│   │   ├── test_generador_horario_catalogo.py
│   │   ├── test_habilitacion_service.py
│   │   ├── test_horario_export.py
│   │   ├── test_horario_lote.py
│   │   ├── test_horario_service.py
│   │   ├── test_identidad_institucional.py
│   │   ├── test_informe_service.py
│   │   ├── test_institucion_service_actualizar.py
│   │   ├── test_login_throttle.py
│   │   ├── test_marcar_config_inicial.py
│   │   ├── test_nivelacion_service.py
│   │   ├── test_observabilidad_service.py
│   │   ├── test_parrilla.py
│   │   ├── test_periodo_service.py
│   │   ├── test_plan_estudios_service.py
│   │   ├── test_plan_mejoramiento_service.py
│   │   ├── test_portal_resumen_service.py
│   │   ├── test_preferencias_service.py
│   │   ├── test_preparacion_horario.py
│   │   ├── test_registros_boletin.py
│   │   ├── test_solo_lectura.py
│   │   ├── test_solo_lectura_isolation.py
│   │   ├── test_tenant_isolation.py
│   │   └── test_usuario_service.py
│   ├── __init__.py
│   ├── test_check_auditoria.py
│   ├── test_config_prod.py
│   ├── test_config_secretos.py
│   └── test_config_secrets.py
├── __init__.py
├── compat_conn.py
├── conftest.py
├── db_engine.py
└── test_container.py
```


---

## Estadísticas rápidas

- **Total archivos:** 218
- **Por extensión:**
  - `.py`: 218
