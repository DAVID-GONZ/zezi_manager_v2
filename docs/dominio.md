# Puertos del Dominio (Repositorios e Interfaces)

> **Actualizado:** Junio 2026. Total: 19 puertos de repositorio + 3 interfaces de servicio externo.

## Modulo: `acudiente_repo.py`

### IAcudienteRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_by_id()`
- `get_by_documento()`
- `existe_documento()`
- `listar_por_estudiante()`
- `get_principal()`
- `listar_estudiantes_de_acudiente()`
- `guardar()`
- `actualizar()`
- `desactivar()`
- `vincular()`
- `desvincular()`
- `establecer_principal()`
- `get_vinculo()`

## Modulo: `alerta_repo.py`

### IAlertaRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_configuracion()`
- `listar_configuraciones()`
- `guardar_configuracion()`
- `desactivar_configuracion()`
- `get_alerta()`
- `listar_alertas()`
- `contar_pendientes()`
- `existe_pendiente()`
- `guardar_alerta()`
- `guardar_alertas_masivas()`
- `resolver_alerta()`
- `resolver_alertas_de_estudiante()`

## Modulo: `asignacion_repo.py`

### IAsignacionRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_by_id()`
- `listar()`
- `existe()`
- `get_info()`
- `listar_info()`
- `listar_por_grupo()`
- `listar_por_docente()`
- `guardar()`
- `desactivar()`
- `reactivar()`
- `reasignar_docente()`

## Modulo: `asistencia_repo.py`

### IAsistenciaRepository
**Herencia**: ABC

**Métodos definidos:**
- `registrar()`
- `registrar_masivo()`
- `get_por_fecha_estudiante()`
- `listar_por_grupo_y_fecha()`
- `listar_por_estudiante_y_periodo()`
- `listar_por_asignacion_y_rango()`
- `resumen_por_estudiante()`
- `resumen_por_grupo()`
- `contar_faltas_injustificadas()`
- `fechas_con_registro()`
- `porcentaje_asistencia_grupo()`
- `estudiantes_en_riesgo()`

## Modulo: `auditoria_repo.py`

### IAuditoriaRepository
**Herencia**: ABC

**Métodos definidos:**
- `registrar_evento()`
- `listar_eventos()`
- `get_ultimo_login()`
- `contar_fallos_recientes()`
- `registrar_cambio()`
- `registrar_cambios_masivos()`
- `listar_cambios()`
- `listar_cambios_por_registro()`
- `get_cambio()`

## Modulo: `cierre_repo.py`

### ICierreRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_cierre_periodo()`
- `listar_cierres_periodo_por_estudiante()`
- `guardar_cierre_periodo()`
- `get_cierre_anio()`
- `listar_cierres_anio_por_estudiante()`
- `guardar_cierre_anio()`
- `get_promocion()`
- `listar_promociones()`
- `guardar_promocion()`
- `actualizar_promocion()`

## Modulo: `configuracion_repo.py`

### IConfiguracionRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_activa()`
- `get_by_id()`
- `get_by_anio()`
- `listar()`
- `guardar()`
- `actualizar()`
- `activar()`
- `listar_niveles()`
- `get_nivel()`
- `guardar_nivel()`
- `actualizar_nivel()`
- `eliminar_nivel()`
- `reemplazar_niveles()`
- `clasificar_nota()`
- `get_criterios()`
- `guardar_criterios()`
- `get_numero_periodos()`
- `guardar_numero_periodos()`

## Modulo: `convivencia_repo.py`

### IConvivenciaRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_observacion()`
- `get_observacion_por_asignacion()`
- `listar_observaciones_por_estudiante()`
- `guardar_observacion()`
- `actualizar_observacion()`
- `eliminar_observacion()`
- `get_registro()`
- `listar_registros()`
- `contar_registros()`
- `guardar_registro()`
- `actualizar_registro()`
- `eliminar_registro()`
- `get_nota()`
- `listar_notas_por_estudiante()`
- `listar_notas_por_grupo()`
- `guardar_nota()`

## Modulo: `estadisticos_repo.py`

### IEstadisticosRepository
**Herencia**: ABC

**Métodos definidos:**
- `calcular_metricas_dashboard()`
- `promedio_general_grupo()`
- `porcentaje_asistencia_global()`
- `contar_alertas_pendientes()`
- `promedio_por_asignacion()`
- `distribucion_desempenos()`
- `comparativo_periodos()`
- `promedios_por_area()`
- `estudiantes_en_riesgo_academico()`
- `ranking_grupo()`
- `tendencia_asistencia()`
- `distribucion_estados_asistencia()`
- `consolidado_notas_grupo()`
- `consolidado_asistencia_grupo()`
- `consolidado_anual_grupo()`

## Modulo: `estudiante_repo.py`

### IEstudianteRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_by_id()`
- `get_by_documento()`
- `existe_documento()`
- `get_resumen()`
- `listar_filtrado()`
- `listar_resumenes()`
- `listar_por_grupo()`
- `contar_por_grupo()`
- `guardar()`
- `actualizar()`
- `actualizar_estado_matricula()`
- `asignar_grupo()`
- `get_piar()`
- `listar_piars()`
- `existe_piar()`
- `guardar_piar()`
- `actualizar_piar()`

## Modulo: `evaluacion_repo.py`

### IEvaluacionRepository
**Herencia**: ABC

**Métodos definidos:**
- `listar_categorias()`
- `get_categoria()`
- `guardar_categoria()`
- `actualizar_categoria()`
- `eliminar_categoria()`
- `suma_pesos_otras()`
- `listar_actividades()`
- `listar_actividades_por_categoria()`
- `listar_actividades_publicadas()`
- `get_actividad()`
- `guardar_actividad()`
- `actualizar_actividad()`
- `actualizar_estado_actividad()`
- `eliminar_actividad()`
- `listar_notas_por_estudiante()`
- `listar_notas_por_actividad()`
- `get_nota()`
- `guardar_nota()`
- `guardar_notas_masivas()`
- `eliminar_nota()`
- `get_puntos_extra()`
- `listar_puntos_extra()`
- `guardar_puntos_extra()`
- `listar_resultados_grupo()`

## Modulo: `habilitacion_repo.py`

### IHabilitacionRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_habilitacion()`
- `listar_habilitaciones()`
- `listar_por_estudiante()`
- `existe_habilitacion()`
- `guardar_habilitacion()`
- `actualizar_habilitacion()`
- `actualizar_estado_habilitacion()`
- `get_plan()`
- `listar_planes_por_estudiante()`
- `listar_planes_por_seguimiento()`
- `guardar_plan()`
- `actualizar_plan()`

## Modulo: `infraestructura_repo.py`

### IInfraestructuraRepository
**Herencia**: ABC

El puerto más extenso del sistema. Cubre toda la infraestructura académica y el subsistema completo de generación de horarios.

**Escenarios de horario:**
- `get_escenario()`, `listar_escenarios()`, `get_escenario_activo()`
- `crear_escenario()`, `actualizar_escenario()`, `activar_escenario()`, `eliminar_escenario()`
- `duplicar_escenario()`
- `listar_horario_grupo_escenario()`, `listar_horario_escenario()`

**Plantillas de franja y franjas:**
- `crear_plantilla_franja()`, `get_plantilla_franja()`, `listar_plantillas_franja()`, `get_plantilla_activa()`
- `actualizar_plantilla_franja()`, `activar_plantilla_franja()`, `eliminar_plantilla_franja()`
- `crear_franja()`, `listar_franjas()`, `actualizar_franja()`, `eliminar_franja()`, `reemplazar_franjas()`

**Áreas de conocimiento:**
- `get_area()`, `listar_areas()`, `guardar_area()`, `actualizar_area()`, `eliminar_area()`, `actualizar_color_area()`

**Asignaturas:**
- `get_asignatura()`, `listar_asignaturas()`, `guardar_asignatura()`, `actualizar_asignatura()`, `eliminar_asignatura()`

**Grupos:**
- `get_grupo()`, `get_grupo_por_codigo()`, `listar_grupos()`
- `guardar_grupo()`, `actualizar_grupo()`, `eliminar_grupo()`, `asignar_sala_a_grupo()`

**Horarios:**
- `get_horario()`, `get_info_horario()`, `listar_horario_grupo()`, `listar_horario_docente()`
- `existe_conflicto_horario()`, `existe_cruce()`, `get_estadisticas()`
- `guardar_horario()`, `actualizar_horario()`, `eliminar_horario()`, `eliminar_horarios_por_asignacion()`
- `contar_bloques_asignacion()`, `contar_bloques_docente()`, `crear_bloques_masivo()`

**Logros:**
- `get_logro()`, `listar_logros()`, `guardar_logro()`, `actualizar_logro()`, `eliminar_logro()`

**Disponibilidad docente:**
- `upsert_disponibilidad()`, `listar_disponibilidad_docente()`, `es_disponible()`
- `limpiar_disponibilidad_docente()`, `cargar_disponibilidad_lote()`, `reemplazar_disponibilidad_docente()`

**Configuración de generación:**
- `crear_config_generacion()`, `get_config_generacion()`, `listar_configs_generacion()`
- `actualizar_config_generacion()`, `eliminar_config_generacion()`, `cambiar_estado_config()`, `duplicar_config_generacion()`

**Salas:**
- `listar_salas()`, `get_sala()`, `crear_sala()`, `actualizar_sala()`, `eliminar_sala()`

**Restricciones de generación:**
- `listar_ventanas_grupo()`, `get_ventanas_por_grupo()`, `get_ventanas_por_grado()`, `crear_ventana_grupo()`, `eliminar_ventana_grupo()`
- `listar_bloques_anclados()`, `crear_bloque_anclado()`, `eliminar_bloque_anclado()`
- `listar_franjas_reunion()`, `get_franja_reunion()`, `crear_franja_reunion()`, `actualizar_franja_reunion()`, `eliminar_franja_reunion()`
- `get_limites_docente()`, `set_limites_docente()`, `listar_limites_docente()`

**Grados y plan de estudios:**
- `listar_grados()`, `upsert_grado()`, `eliminar_grado()`
- `listar_plan_estudios()`, `get_plan_estudios_por_grado()`, `set_horas_plan()`, `eliminar_plan_estudios()`

## Modulo: `periodo_repo.py`

### IPeriodoRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_by_id()`
- `get_por_numero()`
- `get_activo()`
- `listar_por_anio()`
- `suma_pesos_otros()`
- `guardar()`
- `actualizar()`
- `cerrar()`
- `activar()`
- `desactivar()`
- `get_hito()`
- `listar_hitos()`
- `listar_hitos_proximos()`
- `guardar_hito()`
- `actualizar_hito()`
- `eliminar_hito()`

## Modulo: `service_ports.py`

### IAuthenticationService
**Herencia**: ABC

Gestión de credenciales de usuarios.

Responsabilidades:
  - Hashear contraseñas al crear/cambiar.
  - Verificar contraseñas en el login.
  - Cambiar contraseñas con validación de la contraseña actual.

Nunca:
  - Gestiona sesiones (eso es responsabilidad de la capa de interfaz).
  - Accede directamente a la BD (usa IUsuarioRepository para leer users).

**Métodos definidos:**
- `hashear_password()`
- `verificar_password()`
- `cambiar_password()`
- `resetear_password()`

### INotificationService
**Herencia**: ABC

Envío de notificaciones a usuarios, docentes y acudientes.

El servicio de dominio decide CUÁNDO y A QUIÉN notificar;
este port define CÓMO se envía la notificación.
La implementación concreta decide el canal (email, SMS, push).

**Métodos definidos:**
- `notificar_acudiente()`
- `notificar_docente()`
- `notificar_directivos()`

### IExporterService
**Herencia**: ABC

Exportación de datos a formatos externos para descarga.

El servicio de dominio prepara los datos en estructuras del dominio
(DTOs, listas); este port los convierte al formato de salida.
La implementación concreta gestiona las dependencias de librerías
(openpyxl, reportlab, weasyprint, etc.).

**Métodos definidos:**
- `exportar_excel()`
- `exportar_pdf()`
- `exportar_csv()`

## Modulo: `usuario_repo.py`

### IUsuarioRepository
**Herencia**: ABC

**Métodos definidos:**
- `get_by_id()`
- `get_by_username()`
- `get_by_email()`
- `existe_usuario()`
- `listar_filtrado()`
- `listar_resumenes()`
- `listar_docentes_info()`
- `get_docente_info()`
- `listar_asignaciones_docente()`
- `guardar()`
- `actualizar()`
- `cambiar_rol()`
- `desactivar()`
- `reactivar()`

---

## Modulo: `nivelacion_repo.py` *(Nuevo — Junio 2026)*

### INivelacionRepository
**Herencia**: ABC

Contrato de acceso a datos para el módulo de nivelación post-cierre (Decreto 1290).

**Actividades de nivelación:**
- `guardar_actividad()`
- `listar_actividades()`
- `get_actividad()`
- `suma_pesos_actividades()`

**Notas de nivelación:**
- `guardar_nota()`
- `actualizar_nota()`
- `listar_notas_por_actividad()`
- `listar_notas_por_asignacion()`
- `get_nota()`

**Cierre de nivelación:**
- `guardar_cierre()`
- `get_cierre()`

---

## Modulo: `plan_mejoramiento_repo.py` *(Nuevo — Junio 2026)*

### IPlanMejoramientoRepository
**Herencia**: ABC

Contrato de acceso a datos para el plan de mejoramiento cuantitativo con cortes y notas por actividad.

**Corte de plan:**
- `guardar_corte()`
- `get_corte()`
- `get_corte_by_id()`

**Notas de corte:**
- `guardar_nota_corte()`
- `get_nota_corte()`
- `listar_notas_corte()`
- `actualizar_nota_corte()`

**Actividades del plan:**
- `guardar_actividad()`
- `get_actividad()`
- `listar_actividades()`
- `suma_pesos_actividades()`

**Notas de actividades:**
- `guardar_nota_actividad()`
- `get_nota_actividad()`
- `listar_notas_actividad()`
- `listar_notas_por_corte_estudiante()`

---

## Modulo: `siee_repo.py` *(Nuevo — Junio 2026)*

### ISIEERepository
**Herencia**: ABC

Contrato para la configuración del Sistema Institucional de Evaluación y categorías institucionales.

**Configuración SIEE:**
- `get_configuracion()`
- `guardar_configuracion()`

**Categorías institucionales:**
- `listar_categorias_institucionales()`
- `get_categoria_institucional()`
- `guardar_categoria_institucional()`
- `actualizar_categoria_institucional()`
- `eliminar_categoria_institucional()`
- `suma_pesos_institucionales()`

