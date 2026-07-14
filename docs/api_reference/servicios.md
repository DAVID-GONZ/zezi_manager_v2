# API Reference — Servicios

> Generado automáticamente desde `src/services/` por `tools/gen_api_reference.py` (firmas del fuente + primera línea del docstring). Los métodos sin docstring se marcan `⚠️ sin docstring`. **No editar a mano** — re-generar con el script.

**Cobertura de docstrings:** 420/420 métodos (100%).

| Archivo | Con docstring | Total | % |
|---|---:|---:|---:|
| `src/services/acudiente_service.py` | 3 | 3 | 100% |
| `src/services/alerta_service.py` | 10 | 10 | 100% |
| `src/services/asignacion_service.py` | 18 | 18 | 100% |
| `src/services/asistencia_service.py` | 11 | 11 | 100% |
| `src/services/auditoria_service.py` | 6 | 6 | 100% |
| `src/services/catalogo_academico_service.py` | 15 | 15 | 100% |
| `src/services/cierre_service.py` | 10 | 10 | 100% |
| `src/services/configuracion_service.py` | 16 | 16 | 100% |
| `src/services/contexto_tenant.py` | 4 | 4 | 100% |
| `src/services/convivencia_service.py` | 12 | 12 | 100% |
| `src/services/escenario_horario_service.py` | 13 | 13 | 100% |
| `src/services/estadisticos_service.py` | 20 | 20 | 100% |
| `src/services/estudiante_service.py` | 17 | 17 | 100% |
| `src/services/evaluacion_service.py` | 24 | 24 | 100% |
| `src/services/franja_service.py` | 8 | 8 | 100% |
| `src/services/generador_horario_service.py` | 5 | 5 | 100% |
| `src/services/habilitacion_service.py` | 9 | 9 | 100% |
| `src/services/horario_service.py` | 15 | 15 | 100% |
| `src/services/informe_service.py` | 15 | 15 | 100% |
| `src/services/infraestructura_service.py` | 70 | 70 | 100% |
| `src/services/institucion_service.py` | 6 | 6 | 100% |
| `src/services/login_throttle.py` | 4 | 4 | 100% |
| `src/services/nivelacion_service.py` | 10 | 10 | 100% |
| `src/services/periodo_service.py` | 9 | 9 | 100% |
| `src/services/plan_estudios_service.py` | 13 | 13 | 100% |
| `src/services/plan_mejoramiento_service.py` | 12 | 12 | 100% |
| `src/services/preparacion_horario_service.py` | 3 | 3 | 100% |
| `src/services/restriccion_generacion_service.py` | 31 | 31 | 100% |
| `src/services/sala_service.py` | 7 | 7 | 100% |
| `src/services/solo_lectura.py` | 5 | 5 | 100% |
| `src/services/usuario_service.py` | 19 | 19 | 100% |

## `acudiente_service.py`

### AcudienteService
> Orquesta los casos de uso del módulo de Acudientes.

- `def __init__(self, repo: IAcudienteRepository) -> None` — Inyecta el repositorio de acudientes.
- `def get_principal(self, estudiante_id: int)` — Retorna el acudiente principal de un estudiante, o None si no existe.
- `def listar_por_estudiante(self, estudiante_id: int)` — Retorna todos los acudientes vinculados a un estudiante.

## `alerta_service.py`

### AlertaService
> Orquesta los casos de uso del módulo de Alertas.

- `def __init__( self, repo: IAlertaRepository, estadisticos_repo: IEstadisticosRepository | None = None, ) -> None` — Inyecta el repositorio de alertas y el de estadísticos (opcional).
- `def configurar_alerta( self, config: ConfiguracionAlerta, ) -> ConfiguracionAlerta` `@requiere_escritura` — Guarda o actualiza la configuración de un tipo de alerta para un año.
- `def desactivar_configuracion( self, anio_id: int, tipo_alerta: TipoAlerta, ) -> bool` `@requiere_escritura` — Desactiva una configuración de alerta. Retorna True si fue desactivada.
- `def listar_configuraciones( self, anio_id: int, solo_activas: bool = True, ) -> list[ConfiguracionAlerta]` — Retorna las configuraciones de alerta de un año.
- `def get_configuracion( self, anio_id: int, tipo_alerta: TipoAlerta, ) -> ConfiguracionAlerta | None` — Retorna la configuración de un tipo de alerta para un año.
- `def listar_alertas( self, filtro: FiltroAlertasDTO, ) -> list[Alerta]` — Retorna alertas según los filtros indicados.
- `def contar_pendientes( self, estudiante_id: int | None = None, nivel: NivelAlerta | None = None, ) -> int` — Cuenta las alertas pendientes del sistema o de un estudiante.
- `def resolver_alerta( self, alerta_id: int, usuario_id: int, observacion: str | None = None, ) -> bool` — Resuelve una alerta existente.
- `def resolver_alertas_de_estudiante( self, estudiante_id: int, tipo_alerta: TipoAlerta, usuario_id: int, observacion: str | None = None, ) -> int` — Resuelve todas las alertas pendientes de un tipo para un estudiante.
- `def detectar_riesgo_academico( self, grupo_id: int, periodo_id: int, anio_id: int, nota_minima: float = 60.0, min_asignaturas: int = 1, ) -> int` — Detecta estudiantes en riesgo académico y genera alertas masivas.

## `asignacion_service.py`

### CupoDocenteDTO
> Cupo de un docente para una (asignatura, grupo) con sus horas.

_(sin métodos públicos)_

### CompletitudGrupoDTO
> Cobertura del plan de estudios de un grupo en un periodo.

- `def completo(self) -> bool` `@property` — True si las horas asignadas cubren el total del plan del grupo.
- `def faltantes(self) -> int` `@property` — Horas del plan aún sin asignar (nunca negativo).

### AsignacionService
> Orquesta los casos de uso del módulo de Asignaciones.

- `def __init__( self, repo: IAsignacionRepository, periodo_repo: IPeriodoRepository | None = None, auditoria: IAuditoriaRepository | None = None, usuario_repo: IUsuarioRepository | None = None, infra_repo: IInfraestructuraRepository | None = None, plan_svc=None, ) -> None` — Inyecta el repo de asignaciones y las dependencias opcionales
- `def horas_de_asignacion(self, grupo_id: int, asignatura_id: int) -> int` — Horas semanales que aporta una (grupo, asignatura) según el plan del
- `def carga_docente(self, usuario_id: int, periodo_id: int) -> int` — Suma de horas semanales asignadas (activas) a un docente en un periodo.
- `def desactivar_por_grado_asignatura( self, grado: int, asignatura_id: int, usuario_id: int | None = None ) -> int` `@requiere_escritura` — Desactiva las asignaciones activas de una asignatura en todos los
- `def asignar_docente_a_materia( self, grupo_id: int, asignatura_id: int, periodo_id: int, nuevo_usuario_id: int | None, usuario_id: int | None = None, ) -> Asignacion | None` `@requiere_escritura` — Asigna (o quita) el docente de una materia en un grupo+periodo de forma
- `def docentes_con_cupo( self, asignatura_id: int, grupo_id: int, horas: int, periodo_id: int, docente_ids: list[int], usuario_actual_id: int | None = None, ) -> dict[int, CupoDocenteDTO]` — Por cada docente en `docente_ids`, calcula (carga_actual, cap_efectivo,
- `def completitud_grupo( self, grupo_id: int, grado: int | None, periodo_id: int ) -> CompletitudGrupoDTO` — (horas del plan ya asignadas, total del plan) para un grupo+periodo.
- `def materias_sin_docente( self, grupo_id: int, grado: int | None, periodo_id: int ) -> list[int]` — IDs de asignaturas del plan del grado sin docente activo en el grupo.
- `def crear_asignacion( self, dto: NuevaAsignacionDTO, usuario_id: int | None = None, ) -> Asignacion` `@requiere_escritura` — Crea una asignación docente-grupo-asignatura-periodo.
- `def desactivar( self, asignacion_id: int, usuario_id: int | None = None, ) -> Asignacion` `@requiere_escritura` — Desactiva una asignación (soft delete).
- `def reactivar( self, asignacion_id: int, usuario_id: int | None = None, ) -> Asignacion` `@requiere_escritura` — Reactiva una asignación previamente desactivada (idempotente).
- `def reasignar_docente( self, asignacion_id: int, nuevo_usuario_id: int, usuario_id: int | None = None, ) -> Asignacion` `@requiere_escritura` — Reasigna una asignación a un docente diferente.
- `def listar_con_info( self, filtro: FiltroAsignacionesDTO, ) -> list[AsignacionInfo]` — Retorna asignaciones con nombres resueltos por JOIN (scopeado).
- `def listar_por_docente( self, usuario_id: int, periodo_id: int | None = None, ) -> list[AsignacionInfo]` — Retorna las asignaciones de un docente con info completa (scopeado).
- `def get_by_id(self, asignacion_id: int) -> Asignacion` — Retorna una asignación por id. Lanza si no existe.
- `def listar_por_grupo( self, grupo_id: int, solo_activas: bool = True, ) -> list[AsignacionInfo]` — Retorna las asignaciones de un grupo con info completa (scopeado).

## `asistencia_service.py`

### AsistenciaService
> Orquesta los casos de uso del módulo de Asistencia.

- `def __init__( self, repo: IAsistenciaRepository, alerta_repo: IAlertaRepository | None = None, config_repo: IConfiguracionRepository | None = None, ) -> None` — Inyecta el repo de asistencia y los de alertas y configuración (opcionales).
- `def registrar( self, dto: RegistrarAsistenciaDTO, usuario_id: int | None = None, ) -> ControlDiario` `@requiere_escritura` — Registra un control de asistencia individual.
- `def registrar_masivo( self, dto: RegistrarAsistenciaMasivaDTO, usuario_id: int | None = None, anio_id: int | None = None, ) -> int` `@requiere_escritura` — Registra la asistencia de todos los estudiantes de un grupo.
- `def resumen_estudiante( self, estudiante_id: int, periodo_id: int, asignacion_id: int | None = None, ) -> ResumenAsistenciaDTO` — Retorna el resumen de asistencia de un estudiante en un periodo.
- `def resumen_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[ResumenAsistenciaDTO]` — Retorna el resumen de asistencia de todos los estudiantes del grupo.
- `def get_por_fecha( self, estudiante_id: int, grupo_id: int, asignacion_id: int, fecha: object, ) -> ControlDiario | None` — Retorna el registro de asistencia de un estudiante en una fecha.
- `def listar_por_grupo_y_fecha( self, grupo_id: int, asignacion_id: int, fecha: object, ) -> list[ControlDiario]` — Retorna todos los registros de asistencia de un grupo en una fecha.
- `def estados_por_grupo_y_fecha( self, grupo_id: int, asignacion_id: int, fecha: object, ) -> dict[int, dict[str, str]]` — Retorna {estudiante_id: {"estado": "P"|"FJ"|..., "observacion": str}}
- `def guardar_asistencia_masiva( self, grupo_id: int, asignacion_id: int, periodo_id: int, fecha: object, lista: list[dict], usuario_id: int | None = None, anio_id: int | None = None, ) -> int` `@requiere_escritura` — Persiste la asistencia de un grupo a partir de una lista de dicts
- `def contar_clases_mes(self, usuario_id: int, anio: int, mes: int) -> int` — Retorna el total de clases dictadas por el docente en el mes indicado.
- `def clases_mes_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]` — Retorna el desglose {asignacion_id: n_clases} para el docente en el mes.

## `auditoria_service.py`

### AuditoriaService
> Servicio de lectura de auditoría.

- `def __init__(self, repo: IAuditoriaRepository) -> None` — Inyecta el repositorio de auditoría.
- `def registrar_evento(self, evento: EventoSesion) -> EventoSesion` — Registra un evento de sesión (delegado al repositorio).
- `def listar_cambios( self, filtro: FiltroAuditoriaDTO, ) -> list[RegistroCambio]` — Retorna registros del audit_log ordenados por timestamp descendente.
- `def listar_eventos_sesion( self, filtro: FiltroAuditoriaDTO, ) -> list[EventoSesion]` — Retorna eventos de sesión (login, logout, fallos) paginados.
- `def verificar_integridad(self) -> dict` — Verifica el encadenamiento por hash de las dos tablas de auditoría
- `def resumen_uso(self, dias: int = 7) -> ResumenUsoDTO` — Agregación de SOLO LECTURA del uso de la plataforma para el dashboard

## `catalogo_academico_service.py`

### CatalogoAcademicoService

- `def __init__(self, repo: IInfraestructuraRepository) -> None` — Inyecta el repositorio de infraestructura.
- `def listar_areas(self) -> list[AreaConocimiento]` — Lista las áreas de conocimiento (delegado al repositorio).
- `def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento` `@requiere_escritura` — Crea un área de conocimiento (delegado al repositorio).
- `def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento` `@requiere_escritura` — Actualiza un área de conocimiento (delegado al repositorio).
- `def eliminar_area(self, area_id: int) -> bool` `@requiere_escritura` — Elimina un área de conocimiento (delegado al repositorio).
- `def set_color_area(self, area_id: int, color: str | None) -> bool` `@requiere_escritura` — Asigna (o limpia) el color hex de un área. Valida vía el modelo.
- `def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]` — Lista las asignaturas del scope actual, opcionalmente filtradas por área.
- `def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura` `@requiere_escritura` — Crea una asignatura, asignándole la institución del scope si falta.
- `def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura` `@requiere_escritura` — Actualiza una asignatura verificando su tenant y preservando su institución.
- `def eliminar_asignatura(self, asignatura_id: int) -> bool` `@requiere_escritura` — Elimina una asignatura tras verificar que pertenece al tenant activo.
- `def get_grupo(self, grupo_id: int) -> Grupo | None` — Lee un grupo por id (lectura; sin scope de escritura).
- `def listar_grupos(self, grado: int | None = None) -> list[Grupo]` — Lista los grupos del scope actual, opcionalmente filtrados por grado.
- `def guardar_grupo(self, grupo: Grupo) -> Grupo` `@requiere_escritura` — Crea un grupo, asignándole la institución del scope si falta.
- `def actualizar_grupo(self, grupo: Grupo) -> Grupo` `@requiere_escritura` — Actualiza un grupo verificando su tenant y preservando su institución.
- `def eliminar_grupo(self, grupo_id: int) -> bool` `@requiere_escritura` — Elimina un grupo tras verificar que pertenece al tenant activo.

## `cierre_service.py`

### CierreService
> Orquesta los procesos de cierre de periodo y cierre anual.

- `def __init__( self, cierre_repo: ICierreRepository, evaluacion_repo: IEvaluacionRepository, periodo_repo: IPeriodoRepository, config_repo: IConfiguracionRepository, estudiante_repo: IEstudianteRepository, alerta_repo: IAlertaRepository | None = None, auditoria: IAuditoriaRepository | None = None, asignacion_repo=None, ) -> None` — Inyecta los repos de cierre, evaluación, periodo, configuración y
- `def cerrar_periodo( self, asignacion_id: int, periodo_id: int, ctx: ContextoAcademicoDTO, usuario_id: int | None = None, ) -> list[CierrePeriodo]` `@requiere_escritura` — Calcula y registra la nota definitiva de cada estudiante del grupo
- `def cerrar_anio( self, grupo_id: int, anio_id: int, ctx: ContextoAcademicoDTO, usuario_id: int | None = None, ) -> list[CierreAnio]` `@requiere_escritura` — Calcula y registra la nota definitiva anual de cada estudiante.
- `def decidir_promocion( self, est_id: int, anio_id: int, dto: DecidirPromocionDTO, usuario_id: int | None = None, ) -> PromocionAnual` — Registra la decisión de promoción de un estudiante.
- `def get_promocion(self, est_id: int, anio_id: int) -> PromocionAnual | None` — Retorna el registro de promoción de un estudiante.
- `def get_cierre_periodo( self, est_id: int, asignacion_id: int, periodo_id: int, ) -> CierrePeriodo | None` — Retorna el cierre de periodo de un estudiante en una asignación.
- `def estado_cierres_por_asignaciones( self, asignacion_ids: list[int], periodo_id: int, ) -> dict[int, list[CierrePeriodo]]` — Retorna los cierres existentes agrupados por asignacion_id.
- `def resumen_cierres_institucional( self, periodo_id: int, ) -> dict` — Resumen institucional de cierres del periodo (SOLO LECTURA).
- `def reabrir_asignacion( self, asignacion_id: int, periodo_id: int, usuario_id: int | None = None, motivo: str | None = None, ) -> int` `@requiere_escritura` — Elimina los registros de CierrePeriodo de una asignación en un periodo,
- `def cerrar_grupo( self, asignacion_ids: list[int], grupo_id: int, periodo_id: int, ctx: ContextoAcademicoDTO, usuario_id: int | None = None, ) -> dict[int, list[CierrePeriodo] | str]` `@requiere_escritura` — Cierra (o recalcula) todas las asignaciones indicadas de un grupo.

## `configuracion_service.py`

### ConfiguracionService
> Orquesta los casos de uso del módulo de Configuración.

- `def __init__(self, repo: IConfiguracionRepository) -> None` — Inyecta el repositorio de configuración.
- `def crear_anio(self, dto: NuevaConfiguracionAnioDTO) -> ConfiguracionAnio` `@requiere_escritura` — Crea un año lectivo nuevo para una institución.
- `def activar_anio(self, anio_id: int) -> ConfiguracionAnio` `@requiere_escritura` — Activa un año lectivo (solo puede haber uno activo).
- `def actualizar_info_institucional( self, anio_id: int, dto: ActualizarInfoInstitucionalDTO, ) -> ConfiguracionAnio` `@requiere_escritura` — Actualiza los datos institucionales del año indicado.
- `def get_activa(self, institucion_id: int | None = None) -> ConfiguracionAnio` — Retorna la configuración del año activo de la institución.
- `def get_by_id(self, anio_id: int) -> ConfiguracionAnio` — Retorna una configuración por id. Lanza si no existe.
- `def get_info_institucional(self, anio_id: int) -> InformacionInstitucionalDTO` — Retorna el DTO de información institucional.
- `def configurar_niveles( self, anio_id: int, niveles: list[NuevoNivelDesempenoDTO], ) -> list[NivelDesempeno]` `@requiere_escritura` — Reemplaza los niveles de desempeño del año con los nuevos.
- `def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]` — Retorna los niveles de desempeño del año.
- `def agregar_nivel( self, anio_id: int, dto: NuevoNivelDesempenoDTO ) -> NivelDesempeno` `@requiere_escritura` — Agrega un nivel validando que su rango no se solape con los existentes.
- `def actualizar_nivel( self, anio_id: int, nivel_id: int, dto: NuevoNivelDesempenoDTO ) -> NivelDesempeno` `@requiere_escritura` — Actualiza un nivel concreto validando rangos contra el resto.
- `def eliminar_nivel(self, anio_id: int, nivel_id: int) -> bool` `@requiere_escritura` — Elimina un nivel y reindexa el `orden` de los restantes.
- `def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None` — Clasifica una nota en el nivel de desempeño correspondiente.
- `def get_criterios(self, anio_id: int) -> CriterioPromocion | None` — Retorna los criterios de promoción del año.
- `def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion` `@requiere_escritura` — Guarda o actualiza los criterios de promoción del año.
- `def actualizar_configuracion_academica( self, anio_id: int, dto: ActualizarConfiguracionAnioDTO, ) -> ConfiguracionAnio` `@requiere_escritura` — Actualiza campos académicos: nota_minima_aprobacion, nota_minima_escala, nota_maxima_escala, fechas.

## `contexto_tenant.py`

### OperacionFueraDeInstitucionError(PermissionError)
> Se intentó operar (leer/mutar por id) sobre un objeto que NO pertenece a

_(sin métodos públicos)_

### Funciones de módulo

- `def activar_institucion(institucion_id: int | None) -> None` — Fija la institución activa del contexto actual (None = sin scope).
- `def institucion_actual() -> int | None` — Retorna la institución activa del contexto actual.
- `def verificar_pertenencia(institucion_id_objeto: int | None) -> None` — Verifica que un objeto pertenezca a la institución activa de la sesión.
- `def usar_institucion(institucion_id: int | None) -> Iterator[None]` — Context manager que fija la institución activa y la restaura al salir.

## `convivencia_service.py`

### ConvivenciaService
> Orquesta los casos de uso del módulo de Convivencia.

- `def __init__( self, repo: IConvivenciaRepository, alerta_repo: IAlertaRepository | None = None, ) -> None` — Inyecta el repositorio de convivencia y el de alertas (opcional).
- `def registrar_observacion( self, dto: NuevaObservacionDTO, usuario_id: int | None = None, ) -> ObservacionPeriodo` `@requiere_escritura` — Registra una observación narrativa de un estudiante en un periodo.
- `def listar_observaciones( self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False, ) -> list[ObservacionPeriodo]` — Retorna las observaciones de un estudiante.
- `def eliminar_observacion(self, observacion_id: int) -> bool` `@requiere_escritura` — Elimina una observación. Retorna True si fue eliminada.
- `def registrar_comportamiento( self, dto: NuevoRegistroComportamientoDTO, usuario_id: int | None = None, anio_id: int | None = None, ) -> RegistroComportamiento` `@requiere_escritura` — Registra un evento puntual de comportamiento.
- `def notificar_acudiente(self, registro_id: int) -> RegistroComportamiento` — Marca un registro de comportamiento como notificado al acudiente.
- `def agregar_seguimiento( self, registro_id: int, texto: str, ) -> RegistroComportamiento` `@requiere_escritura` — Agrega o actualiza el texto de seguimiento de un registro.
- `def listar_registros( self, filtro: FiltroConvivenciaDTO, ) -> list[RegistroComportamiento]` — Retorna registros de comportamiento según los filtros indicados.
- `def eliminar_registro(self, registro_id: int) -> bool` `@requiere_escritura` — Elimina un registro de comportamiento. Retorna True si fue eliminado.
- `def registrar_nota_comportamiento( self, dto: NuevaNotaComportamientoDTO, usuario_id: int | None = None, ) -> NotaComportamiento` `@requiere_escritura` — Registra o actualiza la nota de comportamiento de un estudiante
- `def get_nota_comportamiento( self, estudiante_id: int, periodo_id: int, ) -> NotaComportamiento | None` — Retorna la nota de comportamiento de un estudiante en un periodo.
- `def listar_notas_grupo( self, grupo_id: int, periodo_id: int, ) -> list[NotaComportamiento]` — Retorna las notas de comportamiento de todos los estudiantes del grupo.

## `escenario_horario_service.py`

### EscenarioHorarioService

- `def __init__(self, repo: IInfraestructuraRepository) -> None` — Inyecta el repositorio de infraestructura.
- `def get_escenario(self, escenario_id: int) -> EscenarioHorario | None` — Retorna un escenario por id (delegado al repositorio).
- `def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]` — Lista los escenarios de un año lectivo (delegado al repositorio).
- `def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None` — Retorna el escenario activo de un año (delegado al repositorio).
- `def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` `@requiere_escritura` — Crea un escenario (delegado al repositorio).
- `def crear_escenario_simple( self, anio_id: int, nombre: str, descripcion: str | None = None ) -> EscenarioHorario` `@requiere_escritura` — Crea un escenario a partir de parámetros primitivos (sin importar el modelo en la UI).
- `def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` `@requiere_escritura` — Actualiza un escenario (delegado al repositorio).
- `def renombrar_escenario( self, esc_existente, nombre: str, descripcion: str | None = None ) -> EscenarioHorario` — Actualiza nombre/descripción de un escenario usando el objeto ya cargado.
- `def activar_escenario(self, escenario_id: int) -> None` `@requiere_escritura` — Marca un escenario como activo (delegado al repositorio).
- `def eliminar_escenario(self, escenario_id: int) -> bool` `@requiere_escritura` — Elimina un escenario (delegado al repositorio).
- `def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario` `@requiere_escritura` — Duplica un escenario con un nuevo nombre (delegado al repositorio).
- `def listar_horario_grupo_escenario( self, grupo_id: int, escenario_id: int ) -> list[HorarioInfo]` — Lista el horario de un grupo dentro de un escenario (delegado al repositorio).
- `def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]` — Lista todos los bloques de un escenario (delegado al repositorio).

## `estadisticos_service.py`

### MetricasInstitucionalesDTO
> Métricas institucionales agregadas sobre todos los grupos con datos.

_(sin métodos públicos)_

### PendientesDocenteDTO
> Resumen de pendientes accionables de un docente (solo lectura).

- `def hay_pendientes(self) -> bool` `@property` — True si el docente tiene actividades, asistencias o alertas pendientes.

### EstadisticosService
> Orquesta los casos de uso del módulo de Estadísticas.

- `def __init__( self, repo: IEstadisticosRepository, config_repo: IConfiguracionRepository | None = None, evaluacion_repo=None, asistencia_repo=None, estudiante_repo=None, infra_repo=None, asignacion_repo=None, alerta_repo=None, ) -> None` — Inyecta el repo de estadísticos y los repos opcionales de
- `def metricas_dashboard( self, grupo_id: int, periodo_id: int, anio_id: int | None = None, ) -> DashboardMetricsDTO` — Calcula las métricas del panel principal para un grupo y periodo.
- `def metricas_institucionales( self, periodo_id: int, anio_id: int | None = None, ) -> MetricasInstitucionalesDTO` — Agrega las métricas de TODOS los grupos con datos en un periodo,
- `def pendientes_docente( self, usuario_id: int, periodo_id: int, anio_id: int | None = None, ) -> PendientesDocenteDTO` — Resumen de pendientes accionables de un docente (SOLO LECTURA).
- `def promedio_general_grupo( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, ) -> float` — Promedio de notas definitivas de todos los estudiantes del grupo.
- `def porcentaje_asistencia_global( self, grupo_id: int, periodo_id: int, ) -> float` — Porcentaje de asistencia promedio del grupo en todas sus asignaturas.
- `def contar_alertas_pendientes(self, grupo_id: int) -> int` — Número de alertas no resueltas de los estudiantes del grupo.
- `def promedio_por_asignacion( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> float` — Promedio de la nota definitiva de todos los estudiantes en una asignación.
- `def distribucion_desempenos( self, grupo_id: int, asignacion_id: int, periodo_id: int, anio_id: int | None = None, ) -> dict[str, int]` — Cuenta cuántos estudiantes cayeron en cada nivel de desempeño.
- `def comparativo_periodos( self, grupo_id: int, asignacion_id: int, anio_id: int, ) -> list[dict[str, Any]]` — Promedio del grupo por periodo, para ver la evolución temporal.
- `def promedios_por_area( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — Promedio del grupo por área de conocimiento en el periodo.
- `def estudiantes_en_riesgo_academico( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, min_asignaturas: int = 1, ) -> list[int]` — IDs de estudiantes con al menos N asignaturas bajo nota mínima.
- `def ranking_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — Estudiantes del grupo ordenados por promedio descendente.
- `def tendencia_asistencia( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — Porcentaje de asistencia del grupo por semana/quincena.
- `def distribucion_estados_asistencia( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> dict[str, int]` — Conteo total de registros por estado de asistencia en el periodo.
- `def consolidado_notas_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — Tabla completa de notas definitivas por asignatura para el grupo.
- `def consolidado_asistencia_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — Tabla completa de asistencia por asignatura para el grupo.
- `def consolidado_anual_grupo( self, grupo_id: int, anio_id: int, ) -> list[dict[str, Any]]` — Consolidado anual: notas + estado de promoción por estudiante.
- `def datos_tablero( self, asignacion_id: int, periodo_id: int, grupo_id: int, anio_id: int | None = None, ) -> dict` — Calcula todos los datos del tablero estadístico para una asignación.

## `estudiante_service.py`

### EstudianteService
> Orquesta los casos de uso del módulo de Estudiantes.

- `def __init__( self, repo: IEstudianteRepository, acudiente_repo: IAcudienteRepository | None = None, auditoria: IAuditoriaRepository | None = None, grupo_reader=None, ) -> None` — Inyecta el repo de estudiantes, los repos opcionales de acudientes
- `def matricular( self, dto: NuevoEstudianteDTO, usuario_id: int | None = None, actor_rol: str | None = None, ) -> Estudiante` `@requiere_escritura` — Matricula un estudiante nuevo.
- `def actualizar( self, estudiante_id: int, dto: ActualizarEstudianteDTO, usuario_id: int | None = None, actor_rol: str | None = None, ) -> Estudiante` `@requiere_escritura` — Actualiza los datos de un estudiante existente.
- `def retirar( self, estudiante_id: int, motivo: str | None = None, usuario_id: int | None = None, ) -> Estudiante` — Retira un estudiante del establecimiento.
- `def asignar_grupo( self, estudiante_id: int, grupo_id: int, usuario_id: int | None = None, ) -> Estudiante` `@requiere_escritura` — Asigna o cambia el grupo de un estudiante.
- `def trasladar( self, estudiante_id: int, grupo_destino_id: int, motivo: str | None, usuario_id: int | None = None, actor_rol: str | None = None, permitir_cambio_grado: bool = False, ) -> Estudiante` `@requiere_escritura` — Traslada un estudiante a otro grupo, registrando el movimiento en el
- `def listar_historial( self, estudiante_id: int ) -> list[MovimientoEstudianteInfoDTO]` — Retorna el historial de movimientos del estudiante (más reciente
- `def listar_por_grupo( self, grupo_id: int, solo_activos: bool = True, ) -> list[Estudiante]` — Retorna todos los estudiantes de un grupo.
- `def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]` — Retorna estudiantes según los filtros indicados (scopeado por tenant).
- `def listar_resumenes( self, filtro: FiltroEstudiantesDTO, ) -> list[EstudianteResumenDTO]` — Retorna la vista resumida de estudiantes para selects (scopeado).
- `def listar_resumenes_plano( self, filtro: FiltroEstudiantesDTO, ) -> list[dict]` — Igual que listar_resumenes pero serializado a dicts planos.
- `def get_by_id(self, estudiante_id: int) -> Estudiante` — Retorna un estudiante por id. Lanza si no existe.
- `def get_para_edicion(self, estudiante_id: int) -> dict` — Retorna los campos editables de un estudiante como dict plano.
- `def registrar_piar( self, dto: NuevoPIARDTO, usuario_id: int | None = None, ) -> PIAR` `@requiere_escritura` — Registra un PIAR para un estudiante en un año lectivo.
- `def actualizar_piar( self, estudiante_id: int, anio_id: int, dto: ActualizarPIARDTO, usuario_id: int | None = None, actor_rol: str | None = None, ) -> PIAR` `@requiere_escritura` — Actualiza un PIAR existente.
- `def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None` — Retorna el PIAR del estudiante para el año indicado.
- `def matricular_masivo_csv( self, filas: list[dict], mapa_grupos: dict[str, int], usuario_id: int | None = None, actor_rol: str | None = None, ) -> MatriculaMasivaResultadoDTO` `@requiere_escritura` — Matricula una lista de estudiantes proveniente de un CSV.

## `evaluacion_service.py`

### PlanillaCompletaDTO
> Agregado de la planilla de notas para la vista (una sola llamada).

_(sin métodos públicos)_

### EvaluacionService
> Orquesta los casos de uso del módulo de Evaluación.

- `def __init__( self, repo: IEvaluacionRepository, asignacion_repo: IAsignacionRepository | None = None, periodo_repo: IPeriodoRepository | None = None, auditoria: IAuditoriaRepository | None = None, siee_repo: ISIEERepository | None = None, ) -> None` — Inyecta el repo de evaluación y los repos opcionales de asignación,
- `def peso_autonomia_disponible( self, asignacion_id: int, periodo_id: int, anio_id: int, ) -> float` — Retorna el peso (0-1) disponible para que el docente añada categorías.
- `def agregar_categoria( self, dto: NuevaCategoriaDTO, ctx: ContextoAcademicoDTO, usuario_id: int | None = None, ) -> Categoria` `@requiere_escritura` — Agrega una categoría de evaluación de docente.
- `def actualizar_categoria( self, cat_id: int, dto: ActualizarCategoriaDTO, usuario_id: int | None = None, ) -> Categoria` `@requiere_escritura` — Actualiza nombre y/o peso de una categoría.
- `def eliminar_categoria( self, cat_id: int, usuario_id: int | None = None, ) -> None` `@requiere_escritura` — Elimina una categoría y sus actividades y notas asociadas
- `def listar_categorias( self, asignacion_id: int, periodo_id: int, ) -> list[Categoria]` — Retorna las categorías de la asignación en el periodo.
- `def agregar_actividad( self, dto: NuevaActividadDTO, usuario_id: int | None = None, ) -> Actividad` `@requiere_escritura` — Crea una actividad evaluativa en estado borrador.
- `def publicar_actividad( self, act_id: int, usuario_id: int | None = None, ) -> Actividad` — Publica una actividad para que los estudiantes puedan verla.
- `def cerrar_actividad( self, act_id: int, usuario_id: int | None = None, ) -> Actividad` `@requiere_escritura` — Cierra una actividad para que no acepte más notas.
- `def reabrir_actividad( self, act_id: int, usuario_id: int | None = None, ) -> Actividad` `@requiere_escritura` — Reabre una actividad cerrada para volver a aceptar notas.
- `def eliminar_actividad( self, act_id: int, usuario_id: int | None = None, ) -> None` `@requiere_escritura` — Elimina una actividad y sus notas asociadas.
- `def listar_actividades( self, asignacion_id: int, periodo_id: int, ) -> list[Actividad]` — Retorna las actividades de la asignación en el periodo.
- `def registrar_nota( self, dto: RegistrarNotaDTO, ctx: ContextoAcademicoDTO, usuario_id: int | None = None, ) -> Nota` `@requiere_escritura` — Registra la nota de un estudiante en una actividad.
- `def registrar_notas_masivas( self, dto: RegistrarNotasMasivasDTO, ctx: ContextoAcademicoDTO, usuario_id: int | None = None, ) -> int` `@requiere_escritura` — Registra las notas de todos los estudiantes de un grupo para una actividad.
- `def obtener_planilla( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[ResultadoEstudianteDTO]` — Retorna la planilla de notas del grupo con definitivas calculadas.
- `def listar_puntos_extra( self, asignacion_id: int, periodo_id: int, ) -> list[PuntosExtra]` — Retorna todos los registros de puntos extra de la asignación en el periodo.
- `def planilla_completa( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> PlanillaCompletaDTO` — Agrega actividades, categorías, planilla (con definitivas) y puntos
- `def guardar_puntos_extra( self, puntos: PuntosExtra, usuario_id: int | None = None, ) -> PuntosExtra` `@requiere_escritura` — Guarda o actualiza los puntos extra de un estudiante.
- `def get_configuracion_siee(self, anio_id: int) -> ConfiguracionSIEE` — Retorna la configuración SIEE del año.
- `def guardar_configuracion_siee( self, dto: NuevaConfiguracionSIEEDTO, usuario_id: int | None = None, ) -> ConfiguracionSIEE` `@requiere_escritura` — Crea o actualiza la configuración SIEE del año.
- `def listar_categorias_institucionales(self, anio_id: int) -> list[Categoria]` — Retorna las categorías institucionales del año.
- `def agregar_categoria_institucional( self, dto: NuevaCategoriaInstitucionalDTO, usuario_id: int | None = None, ) -> Categoria` `@requiere_escritura` — Crea una categoría institucional.
- `def actualizar_categoria_institucional( self, cat_id: int, dto: ActualizarCategoriaDTO, anio_id: int, usuario_id: int | None = None, ) -> Categoria` `@requiere_escritura` — Actualiza una categoría institucional existente.
- `def eliminar_categoria_institucional( self, cat_id: int, usuario_id: int | None = None, ) -> None` `@requiere_escritura` — Elimina una categoría institucional.

## `franja_service.py`

### FranjaService

- `def __init__(self, repo: IInfraestructuraRepository) -> None` — Inyecta el repositorio de infraestructura.
- `def crear_plantilla_simple( self, nombre: str, jornada: str = "UNICA", dias: list[str] | None = None, ) -> PlantillaFranja` `@requiere_escritura` — Crea una plantilla a partir de parámetros primitivos (la UI no importa modelos).
- `def listar_plantillas(self) -> list[PlantillaFranja]` — Lista las plantillas de franja del scope actual (admin ve todas).
- `def plantilla_activa(self, jornada: str = "UNICA") -> PlantillaFranja | None` — Retorna la plantilla activa de una jornada para la institución del scope.
- `def guardar_franjas(self, plantilla_id: int, filas: list[dict]) -> int` `@requiere_escritura` — Reemplaza el set de franjas de una plantilla. `filas` son dicts con claves
- `def listar_franjas(self, plantilla_id: int) -> list[Franja]` — Lista las franjas de una plantilla (delegado al repositorio).
- `def activar_plantilla(self, plantilla_id: int) -> None` `@requiere_escritura` — Marca una plantilla de franja como activa (delegado al repositorio).
- `def eliminar_plantilla(self, plantilla_id: int) -> bool` `@requiere_escritura` — Elimina una plantilla tras verificar que pertenece al tenant activo.

## `generador_horario_service.py`

### _Leccion
> Una unidad de bloque a colocar de una asignación (una hora o macro-bloque).

- `def __init__( self, asignacion_id, grupo_id, usuario_id, etiqueta, tipo_sala_req=None, n_horas=1, )` — Inicializa la unidad de bloque con su asignación, grupo, docente,

### GeneradorHorarioService

- `def __init__( self, infra_repo, asignacion_repo, usuario_repo, horario_service, infraestructura_service, plan_svc=None, )` — Inyecta los repos de infraestructura, asignación y usuario, los
- `def catalogo_pesos() -> dict[str, list[tuple[str, str, str]]]` `@staticmethod` — Devuelve el catálogo de pesos del motor para construir la UI.
- `def plantilla_generable(self, plantilla_id: int | None) -> tuple[bool, str]` — ¿Se puede generar un horario con esta plantilla?
- `def generar( self, config_id: int, *, crear_escenario: bool = True, max_iteraciones: int = 200_000, optimizar: bool = True, ) -> ResultadoGeneracionDTO` — Genera un horario para una config: carga asignaciones y restricciones,

## `habilitacion_service.py`

### HabilitacionService
> Orquesta los casos de uso del módulo de Habilitaciones.

- `def __init__( self, repo: IHabilitacionRepository, cierre_repo: ICierreRepository | None = None, config_repo: IConfiguracionRepository | None = None, auditoria: IAuditoriaRepository | None = None, ) -> None` — Inyecta el repo de habilitación y los repos opcionales de cierre,
- `def programar_habilitacion( self, dto: NuevaHabilitacionDTO, usuario_id: int | None = None, ) -> Habilitacion` — Programa una habilitación para un estudiante.
- `def registrar_nota_habilitacion( self, hab_id: int, dto: RegistrarNotaHabilitacionDTO, anio_id: int | None = None, ) -> Habilitacion` `@requiere_escritura` — Registra la nota obtenida en la habilitación y determina si aprueba.
- `def listar_habilitaciones( self, filtro: FiltroHabilitacionesDTO, ) -> list[Habilitacion]` — Retorna habilitaciones según los filtros indicados.
- `def contar_habilitaciones_pendientes( self, periodo_id: int | None = None, ) -> int` — Cuenta las habilitaciones en estado PENDIENTE (SOLO LECTURA).
- `def get_by_id(self, hab_id: int) -> Habilitacion` — Retorna una habilitación por id. Lanza si no existe.
- `def crear_plan( self, dto: NuevoPlanMejoramientoDTO, usuario_id: int | None = None, ) -> PlanMejoramiento` `@requiere_escritura` — Crea un plan de mejoramiento para un estudiante.
- `def cerrar_plan( self, plan_id: int, dto: CerrarPlanMejoramientoDTO, usuario_id: int | None = None, ) -> PlanMejoramiento` `@requiere_escritura` — Cierra un plan de mejoramiento con el estado y observación indicados.
- `def listar_planes_por_estudiante( self, estudiante_id: int, asignacion_id: int | None = None, estado: EstadoPlanMejoramiento | None = None, ) -> list[PlanMejoramiento]` — Retorna los planes de mejoramiento de un estudiante.

## `horario_service.py`

### HorarioService

- `def __init__( self, infra_repo: IInfraestructuraRepository, asignacion_repo: IAsignacionRepository, usuario_repo, plan_svc=None, )` — Inyecta los repos de infraestructura, asignación y usuario, más el
- `def crear_bloque( self, escenario_id: int, asignacion_id: int, dia: str, hora_inicio: str, hora_fin: str, sala: str = "Aula", ) -> Horario` `@requiere_escritura` — Crea un bloque de horario tras validar cruces (docente, grupo, sala)
- `def mover_bloque( self, horario_id: int, dia: str, hora_inicio: str, hora_fin: str, ) -> Horario` — Mueve un bloque a otro día/hora (misma sala) validando cruces.
- `def actualizar_bloque( self, horario_id: int, *, dia: str, hora_inicio: str, hora_fin: str, sala: str, ) -> Horario` `@requiere_escritura` — Actualiza día, horas y sala de un bloque validando cruces.
- `def eliminar_bloque(self, horario_id: int) -> bool` `@requiere_escritura` — Elimina un bloque de horario (delegado al repositorio).
- `def listar_horario_grupo( self, grupo_id: int, periodo_id: int ) -> list[HorarioInfo]` — Lista el horario de un grupo en un periodo (delegado al repositorio).
- `def disponibilidad_asignacion( self, escenario_id: int, asignacion_id: int ) -> CupoDTO` — Cupo de bloques de una asignación: usados vs. horas de la asignatura.
- `def disponibilidad_docente( self, escenario_id: int, usuario_id: int ) -> CupoDTO` — Cupo de bloques de un docente: usados vs. su carga horaria máxima.
- `def plantilla_filas(self, periodo_id: int) -> list[dict]` — Genera filas prellenadas (sin horario) para cada asignación del periodo.
- `def filas_exportables(self, escenario_id: int, grupo_id: int | None = None) -> list[dict]` — Exporta los bloques de un escenario como filas de dict con COLUMNAS_HORARIO.
- `def datos_parrilla(self, escenario_id: int) -> dict` — Devuelve la estructura UI-agnóstica para pintar la parrilla visual
- `def metricas_parrilla(self, escenario_id: int) -> dict` — Agregados del escenario para el panel de métricas de la parrilla.
- `def areas_parrilla(self, escenario_id: int) -> list[dict]` — Áreas presentes en el escenario, deduplicadas y ordenadas por nombre.
- `def analizar_lote( self, escenario_id: int, periodo_id: int, filas: list[dict], ) -> "ReporteLoteDTO"` — Analiza un lote de filas como escenario virtual (sin persistir):
- `def aplicar_lote( self, escenario_id: int, periodo_id: int, filas: list[dict], solo_validas: bool = False, ) -> "ResultadoLoteDTO"` `@requiere_escritura` — Persiste un lote de bloques: lo analiza y, si es válido (o si

## `informe_service.py`

### BoletinesGrupoDTO
> Resultado de la generación masiva de boletines de un grupo.

_(sin métodos públicos)_

### InformeService
> Orquesta la generación de informes académicos en diferentes formatos.

- `def __init__( self, estadisticos_repo: IEstadisticosRepository, exporter: IExporterService | None = None, estudiante_repo=None, ) -> None` — Inyecta el repo de estadísticos y, opcionalmente, el exportador y
- `def datos_informe_notas( self, dto: InformeNotasDTO, ) -> list[dict]` — Obtiene los datos del informe de notas para un grupo y periodo.
- `def generar_notas( self, dto: InformeNotasDTO, ) -> bytes` — Genera el informe de notas en el formato especificado (Excel o PDF).
- `def datos_informe_asistencia( self, dto: InformeAsistenciaDTO, ) -> list[dict]` — Obtiene los datos del informe de asistencia para un grupo y periodo.
- `def generar_asistencia( self, dto: InformeAsistenciaDTO, ) -> bytes` — Genera el informe de asistencia en el formato especificado.
- `def datos_consolidado_anual( self, grupo_id: int, anio_id: int, ) -> list[dict]` — Obtiene el consolidado anual: notas + estado de promoción.
- `def generar_consolidado_anual( self, grupo_id: int, anio_id: int, formato: FormatoInforme = FormatoInforme.EXCEL, ) -> bytes` — Genera el consolidado anual en el formato especificado.
- `def exportar_csv( self, datos: list[dict], encoding: str = "utf-8-sig", ) -> bytes` — Exporta una lista de dicts como CSV.
- `def generar_boletin_periodo( self, estudiante_id: int, grupo_id: int, periodo_id: int, formato: str = "pdf", grupo_nombre: str = "", periodo_nombre: str = "", ) -> bytes` — Genera el boletín de un estudiante para un periodo específico.
- `def generar_boletin_anual( self, estudiante_id: int, grupo_id: int, anio_id: int, formato: str = "pdf", grupo_nombre: str = "", ) -> bytes` — Genera el boletín anual de un estudiante.
- `def generar_boletines_grupo( self, grupo_id: int, periodo_id: int | None = None, anio_id: int | None = None, formato: str = "pdf", grupo_nombre: str = "", periodo_nombre: str = "", ) -> BoletinesGrupoDTO` — Genera el boletín de cada estudiante del grupo y los fusiona en un
- `def exportar_estadistico( self, tipo: str, datos, formato: FormatoInforme | str, contexto: dict | None = None, ) -> bytes` — Exporta un estadístico a Excel o PDF encapsulando todo el pipeline

### Funciones de módulo

- `def sanitizar_datos_exportacion(datos: list[dict]) -> list[dict]` — Prepara datos brutos del repositorio para exportación (Excel / PDF):
- `def merge_pdfs(pdf_list: list[bytes]) -> bytes` — Une varios PDF (como bytes) en un único documento PDF.
- `def merge_excels(excel_list: list[tuple[str, bytes]]) -> bytes` — Combina varios Excel (bytes) en un único libro con una hoja por estudiante.

## `infraestructura_service.py`

### InfraestructuraService

- `def __init__(self, repo: IInfraestructuraRepository) -> None` — Inyecta el repositorio de infraestructura.
- `def get_escenario(self, escenario_id: int) -> EscenarioHorario | None` — Retorna un escenario por id (delega en EscenarioHorarioService).
- `def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]` — Lista los escenarios de un año lectivo (delega en EscenarioHorarioService).
- `def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None` — Retorna el escenario activo de un año (delega en EscenarioHorarioService).
- `def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` — Crea un escenario (delega en EscenarioHorarioService).
- `def crear_escenario_simple( self, anio_id: int, nombre: str, descripcion: str | None = None ) -> EscenarioHorario` — Crea un escenario desde primitivos (delega en EscenarioHorarioService).
- `def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` — Actualiza un escenario (delega en EscenarioHorarioService).
- `def renombrar_escenario( self, esc_existente, nombre: str, descripcion: str | None = None ) -> EscenarioHorario` — Renombra un escenario usando el objeto ya cargado (delega en EscenarioHorarioService).
- `def activar_escenario(self, escenario_id: int) -> None` — Marca un escenario como activo (delega en EscenarioHorarioService).
- `def eliminar_escenario(self, escenario_id: int) -> bool` — Elimina un escenario (delega en EscenarioHorarioService).
- `def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario` — Duplica un escenario con un nuevo nombre (delega en EscenarioHorarioService).
- `def listar_horario_grupo_escenario( self, grupo_id: int, escenario_id: int ) -> list[HorarioInfo]` — Lista el horario de un grupo dentro de un escenario (delega en EscenarioHorarioService).
- `def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]` — Lista todos los bloques de un escenario (delega en EscenarioHorarioService).
- `def crear_plantilla_simple( self, nombre: str, jornada: str = "UNICA", dias: list[str] | None = None, ) -> PlantillaFranja` — Crea una plantilla desde primitivos (delega en FranjaService).
- `def listar_plantillas(self) -> list[PlantillaFranja]` — Lista las plantillas de franja del scope actual (delega en FranjaService).
- `def plantilla_activa(self, jornada: str = "UNICA") -> PlantillaFranja | None` — Retorna la plantilla activa de una jornada (delega en FranjaService).
- `def guardar_franjas(self, plantilla_id: int, filas: list[dict]) -> int` — Reemplaza el set de franjas de una plantilla (delega en FranjaService).
- `def listar_franjas(self, plantilla_id: int) -> list[Franja]` — Lista las franjas de una plantilla (delega en FranjaService).
- `def activar_plantilla(self, plantilla_id: int) -> None` — Marca una plantilla de franja como activa (delega en FranjaService).
- `def eliminar_plantilla(self, plantilla_id: int) -> bool` — Elimina una plantilla (delega en FranjaService).
- `def listar_areas(self) -> list[AreaConocimiento]` — Lista las áreas de conocimiento (delega en CatalogoAcademicoService).
- `def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento` — Crea un área de conocimiento (delega en CatalogoAcademicoService).
- `def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento` — Actualiza un área de conocimiento (delega en CatalogoAcademicoService).
- `def eliminar_area(self, area_id: int) -> bool` — Elimina un área de conocimiento (delega en CatalogoAcademicoService).
- `def set_color_area(self, area_id: int, color: str | None) -> bool` — Asigna (o limpia) el color hex de un área (delega en CatalogoAcademicoService).
- `def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]` — Lista las asignaturas del scope actual (delega en CatalogoAcademicoService).
- `def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura` — Crea una asignatura (delega en CatalogoAcademicoService).
- `def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura` — Actualiza una asignatura (delega en CatalogoAcademicoService).
- `def eliminar_asignatura(self, asignatura_id: int) -> bool` — Elimina una asignatura (delega en CatalogoAcademicoService).
- `def get_grupo(self, grupo_id: int) -> Grupo | None` — Lee un grupo por id (delega en CatalogoAcademicoService).
- `def listar_grupos(self, grado: int | None = None) -> list[Grupo]` — Lista los grupos del scope actual (delega en CatalogoAcademicoService).
- `def guardar_grupo(self, grupo: Grupo) -> Grupo` — Crea un grupo (delega en CatalogoAcademicoService).
- `def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool` — Asigna (o quita, con None) el aula propia de un grupo (delega en SalaService).
- `def actualizar_grupo(self, grupo: Grupo) -> Grupo` — Actualiza un grupo (delega en CatalogoAcademicoService).
- `def eliminar_grupo(self, grupo_id: int) -> bool` — Elimina un grupo (delega en CatalogoAcademicoService).
- `def es_disponible_docente( self, usuario_id: int, dia: str, franja_orden: int ) -> bool` — Indica si un docente está disponible en una franja (delega en RestriccionGeneracionService).
- `def bloquear_franjas_docente( self, usuario_id: int, slots: list[dict] ) -> int` — Carga en lote las franjas no disponibles de un docente (delega en RestriccionGeneracionService).
- `def limpiar_disponibilidad_docente(self, usuario_id: int) -> int` — Borra toda la disponibilidad configurada de un docente (delega en RestriccionGeneracionService).
- `def guardar_disponibilidad_docente( self, usuario_id: int, slots: list[dict] ) -> int` — Reemplaza ATÓMICAMENTE la disponibilidad de un docente (delega en RestriccionGeneracionService).
- `def listar_disponibilidad_docente( self, usuario_id: int ) -> list[DisponibilidadDocente]` — Lista la disponibilidad configurada de un docente (delega en RestriccionGeneracionService).
- `def crear_config_generacion( self, nombre: str, periodo_id: int, anio_id: int, plantilla_id: int, grupos: list[int] | None = None, pesos: dict | None = None, restricciones: dict | None = None, ) -> ConfigGeneracion` — Crea una config de generación desde primitivos (delega en RestriccionGeneracionService).
- `def construir_restricciones( self, min_horas: int, max_horas: int, modo: str = "preferente" ) -> dict` — Ensambla el payload de restricciones de generación (delega en RestriccionGeneracionService).
- `def listar_configs_generacion( self, periodo_id: int | None = None ) -> list[ConfigGeneracion]` — Lista las configs de generación (delega en RestriccionGeneracionService).
- `def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None` — Retorna una config de generación por id (delega en RestriccionGeneracionService).
- `def actualizar_config_generacion( self, config_id: int, **campos ) -> ConfigGeneracion` — Actualiza los campos indicados de una config de generación (delega en RestriccionGeneracionService).
- `def eliminar_config_generacion(self, config_id: int) -> bool` — Elimina una config de generación (delega en RestriccionGeneracionService).
- `def cambiar_estado_config( self, config_id: int, nuevo_estado: str ) -> ConfigGeneracion` — Cambia el estado de una config de generación (delega en RestriccionGeneracionService).
- `def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion` — Duplica una config de generación (delega en RestriccionGeneracionService).
- `def listar_salas(self) -> list[Sala]` — Lista las salas del scope actual (delega en SalaService).
- `def get_sala(self, sala_id: int) -> Sala | None` — Retorna una sala por id (delega en SalaService).
- `def crear_sala(self, sala: Sala) -> Sala` — Crea una sala (delega en SalaService).
- `def actualizar_sala(self, sala: Sala) -> Sala` — Actualiza una sala (delega en SalaService).
- `def eliminar_sala(self, sala_id: int) -> bool` — Elimina una sala (delega en SalaService).
- `def listar_ventanas_grupo(self) -> list[VentanaGrupo]` — Lista todas las ventanas de grupo (delega en RestriccionGeneracionService).
- `def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]` — Lista las ventanas de un grupo (delega en RestriccionGeneracionService).
- `def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]` — Lista las ventanas de un grado (delega en RestriccionGeneracionService).
- `def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo` — Crea una ventana de grupo (delega en RestriccionGeneracionService).
- `def eliminar_ventana_grupo(self, ventana_id: int) -> bool` — Elimina una ventana de grupo (delega en RestriccionGeneracionService).
- `def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]` — Lista los bloques anclados de un escenario (delega en RestriccionGeneracionService).
- `def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado` — Crea un bloque anclado (delega en RestriccionGeneracionService).
- `def eliminar_bloque_anclado(self, bloque_id: int) -> bool` — Elimina un bloque anclado (delega en RestriccionGeneracionService).
- `def listar_franjas_reunion(self) -> list[FranjaReunion]` — Lista las franjas de reunión (delega en RestriccionGeneracionService).
- `def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None` — Retorna una franja de reunión por id (delega en RestriccionGeneracionService).
- `def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion` — Crea una franja de reunión (delega en RestriccionGeneracionService).
- `def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion` — Actualiza una franja de reunión (delega en RestriccionGeneracionService).
- `def eliminar_franja_reunion(self, franja_id: int) -> bool` — Elimina una franja de reunión (delega en RestriccionGeneracionService).
- `def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None` — Retorna los límites diarios de un docente (delega en RestriccionGeneracionService).
- `def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente` — Crea o actualiza los límites diarios de un docente (delega en RestriccionGeneracionService).
- `def set_limites_docente_simple( self, usuario_id: int, min_horas_dia: int = 0, max_horas_dia: int = 8 ) -> LimitesDocente` — Crea o actualiza los límites diarios de un docente desde primitivos (delega en RestriccionGeneracionService).
- `def listar_limites_docente(self) -> list[LimitesDocente]` — Lista los límites diarios de todos los docentes (delega en RestriccionGeneracionService).

## `institucion_service.py`

### InstitucionService
> Orquesta los casos de uso del módulo de Instituciones.

- `def __init__(self, repo: IInstitucionRepository) -> None` — Inyecta el repositorio de instituciones.
- `def listar(self, solo_activas: bool = False) -> list[InstitucionResumenDTO]` — Retorna el resumen de instituciones para selects y filtros.
- `def get(self, institucion_id: int) -> Institucion` — Retorna una institución por id. Lanza si no existe.
- `def get_por_defecto(self) -> Institucion | None` — Retorna la institución por defecto (#1), o None si aún no hay ninguna.
- `def id_por_defecto(self) -> int | None` — Atajo: el id de la institución por defecto, o None si no hay ninguna.
- `def crear(self, dto: NuevaInstitucionDTO) -> Institucion` `@requiere_escritura` — Crea una institución nueva.

## `login_throttle.py`

### _Estado
> Contador de fallos y momento de bloqueo de un username.

_(sin métodos públicos)_

### Funciones de módulo

- `def registrar_fallo(usuario: str) -> None` — Registra un intento fallido para ``usuario``.
- `def registrar_exito(usuario: str) -> None` — Limpia el contador de fallos y cualquier bloqueo de ``usuario``.
- `def estado_bloqueo(usuario: str) -> tuple[bool, int]` — Estado de bloqueo de ``usuario``.
- `def reset_throttle() -> None` — Vacía todo el estado de throttle (uso exclusivo de tests).

## `nivelacion_service.py`

### FilaNivelacionDTO
> Una fila de la planilla de nivelación con el promedio YA calculado.

_(sin métodos públicos)_

### PlanillaNivelacionDTO
> Planilla completa de nivelación lista para renderizar (sin cálculo en la vista).

_(sin métodos públicos)_

### NivelacionService
> Casos de uso para el módulo de nivelación.

- `def __init__( self, repo: INivelacionRepository, cierre_repo: ICierreRepository, config_repo: IConfiguracionRepository | None = None, ) -> None` — Inyecta el repo de nivelación, el de cierre y el de configuración (opcional).
- `def listar_bajo_desempeno( self, asignacion_ids: list[int], periodo_id: int, nota_maxima: float | None = None, ) -> list[CierrePeriodo]` — Retorna cierres de período con nota ≤ nota_maxima (bajo desempeño).
- `def listar_actividades( self, asignacion_id: int, periodo_id: int, ) -> list[ActividadNivelacion]` — Lista actividades de nivelación para una asignacion+periodo.
- `def agregar_actividad( self, dto: NuevaActividadNivelacionDTO, estudiante_ids: list[int], usuario_id: int | None = None, ) -> ActividadNivelacion` `@requiere_escritura` — Crea una actividad de nivelación y genera NotaNivelacion vacías
- `def listar_notas( self, asignacion_id: int, periodo_id: int, ) -> list[NotaNivelacion]` — Lista todas las notas de nivelación para una asignacion+periodo.
- `def calificar_nota( self, actividad_nivelacion_id: int, estudiante_id: int, dto: CalificarNotaNivelacionDTO, ) -> NotaNivelacion` — Registra o actualiza la nota de un estudiante en una actividad.
- `def get_cierre( self, asignacion_id: int, periodo_id: int, ) -> CierreNivelacion | None` — Retorna el cierre si existe (nivelación cerrada), None si está abierta.
- `def cerrar_nivelacion( self, asignacion_id: int, periodo_id: int, usuario_id: int | None = None, ) -> CierreNivelacion` `@requiere_escritura` — Cierra la nivelación para una asignacion+periodo.
- `def calcular_nota_estudiante( self, estudiante_id: int, asignacion_id: int, periodo_id: int, ) -> float | None` — Calcula la nota definitiva de nivelación de un estudiante.
- `def planilla_nivelacion( self, asignacion_id: int, periodo_id: int, nota_maxima: float | None = None, ) -> PlanillaNivelacionDTO` — Devuelve la planilla de nivelación completa con el promedio ponderado

## `periodo_service.py`

### PeriodoService
> Orquesta los casos de uso del módulo de Periodos académicos.

- `def __init__( self, repo: IPeriodoRepository, config_repo: IConfiguracionRepository | None = None, auditoria: IAuditoriaRepository | None = None, ) -> None` — Inyecta el repo de periodos y los repos opcionales de configuración y auditoría.
- `def crear_periodo(self, dto: NuevoPeriodoDTO) -> Periodo` `@requiere_escritura` — Crea un periodo académico nuevo.
- `def cerrar_periodo( self, periodo_id: int, usuario_id: int | None = None, ) -> Periodo` `@requiere_escritura` — Cierra un periodo para que no acepte más notas ni asistencia.
- `def activar_periodo(self, periodo_id: int) -> Periodo` `@requiere_escritura` — Activa un periodo para que sea el periodo de trabajo actual.
- `def listar_por_anio(self, anio_id: int) -> list[Periodo]` — Retorna todos los periodos del año, ordenados por número.
- `def get_activo(self, anio_id: int) -> Periodo` — Retorna el periodo activo del año. Lanza si no hay activo.
- `def get_by_id(self, periodo_id: int) -> Periodo` — Retorna un periodo por id. Lanza si no existe.
- `def listar_hitos_proximos( self, anio_id: int, dias: int = 7, ) -> list[HitoPeriodo]` — Retorna hitos cuya fecha_limite cae dentro de los próximos `dias`
- `def agregar_hito( self, dto: NuevoHitoPeriodoDTO, usuario_id: int | None = None, ) -> HitoPeriodo` `@requiere_escritura` — Agrega un hito (fecha límite) a un periodo.

## `plan_estudios_service.py`

### PlanEstudiosService

- `def __init__( self, repo: IInfraestructuraRepository, asignacion_svc_provider=None, ) -> None` — Inyecta el repo de infraestructura y un provider lazy del servicio de
- `def listar_grados(self) -> list[Grado]` — Lista los grados ofrecidos (delegado al repositorio).
- `def guardar_grado( self, numero: int, nombre: str | None, min_estudiantes: int, max_estudiantes: int, horas_semanales: int, ) -> Grado` `@requiere_escritura` — Crea o actualiza un grado (upsert por número).
- `def eliminar_grado(self, numero: int) -> bool` `@requiere_escritura` — Elimina un grado por su número (delegado al repositorio).
- `def horas_objetivo(self, grado: int) -> int` — Total de horas semanales objetivo declarado para el grado (0 si no existe).
- `def listar(self) -> list[PlanEstudios]` — Lista todo el plan de estudios (delegado al repositorio).
- `def por_grado(self, grado: int) -> list[PlanEstudios]` — Lista el plan de estudios de un grado (delegado al repositorio).
- `def horas_por_grado(self, grado: int) -> int` — Total horas semanales declaradas en el plan para ese grado.
- `def horas_de(self, grado: int, asignatura_id: int) -> int` — Horas semanales de una asignatura en un grado.
- `def horas_por_grupo(self, grupo) -> int` — Total horas semanales para un grupo según su grado.
- `def actualizar(self, dto: NuevoPlanEstudiosDTO) -> PlanEstudios` `@requiere_escritura` — Fija (upsert) las horas de una asignatura en el plan de un grado.
- `def set_horas(self, grado: int, asignatura_id: int, horas: int) -> PlanEstudios` `@requiere_escritura` — Upsert a partir de primitivas (la UI no importa DTOs de dominio).
- `def eliminar( self, grado: int, asignatura_id: int, cascade: bool = True, usuario_id: int | None = None, ) -> tuple[bool, int]` `@requiere_escritura` — Quita una asignatura del plan de un grado.

## `plan_mejoramiento_service.py`

### PlanMejoramientoService
> Orquesta la lógica de Plan de Mejoramiento.

- `def __init__( self, plan_repo: IPlanMejoramientoRepository, eval_repo: IEvaluacionRepository, est_repo: IEstudianteRepository, ) -> None` — Inyecta los repos de plan de mejoramiento, evaluación y estudiante.
- `def ejecutar_corte( self, dto: EjecutarCorteDTO, grupo_id: int ) -> tuple[CortePlan, list[NotaCortePlan]]` — Ejecuta el corte de plan de mejoramiento para una asignación.
- `def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None` — Obtiene el corte existente para asignacion+periodo, o None.
- `def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]` — Lista todas las notas de corte (todos los estudiantes).
- `def listar_en_plan(self, corte_id: int) -> list[NotaCortePlan]` — Lista solo los estudiantes que están EN_PLAN.
- `def agregar_actividad( self, dto: NuevaActividadPlanDTO, usuario_id: int | None = None ) -> ActividadPlan` `@requiere_escritura` — Añade una actividad al plan de mejoramiento.
- `def listar_actividades(self, corte_id: int) -> list[ActividadPlan]` — Lista actividades del plan para un corte.
- `def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]` — Lista todas las notas de una actividad del plan.
- `def notas_por_actividad_corte( self, corte_id: int ) -> dict[int, dict[int, NotaActividadPlan]]` — Devuelve las notas de TODAS las actividades de un corte en una sola
- `def calificar_nota( self, actividad_plan_id: int, estudiante_id: int, dto: CalificarNotaPlanDTO, ) -> NotaActividadPlan` — Califica la nota de un estudiante en una actividad del plan.
- `def calcular_nota_plan_estudiante( self, corte_id: int, estudiante_id: int ) -> float | None` — Calcula el promedio ponderado del plan para un estudiante.
- `def cerrar_plan_estudiante(self, dto: CerrarPlanEstudianteDTO) -> NotaCortePlan` `@requiere_escritura` — Cierra el plan de mejoramiento de un estudiante.

## `preparacion_horario_service.py`

### PuertaDTO

_(sin métodos públicos)_

### PreparacionHorarioService

- `def __init__( self, infra_repo: IInfraestructuraRepository, asignacion_repo: IAsignacionRepository, config_repo: IConfiguracionRepository, periodo_repo: IPeriodoRepository, usuario_repo: IUsuarioRepository, plan_svc: "PlanEstudiosService", ) -> None` — Inyecta los repos de infraestructura, asignación, configuración,
- `def validar( self, anio_id: int, periodo_id: int, plantilla_id: int, ) -> ReportePreparacionDTO` — Ejecuta las 7 puertas en orden y devuelve el reporte.
- `def puede_generar(reporte: ReportePreparacionDTO) -> bool` `@staticmethod` — True si todas las puertas 'dura' están en ok.

## `restriccion_generacion_service.py`

### RestriccionGeneracionService

- `def __init__(self, repo: IInfraestructuraRepository) -> None` — Inyecta el repositorio de infraestructura.
- `def es_disponible_docente( self, usuario_id: int, dia: str, franja_orden: int ) -> bool` — Indica si un docente está disponible en una franja (delegado al repositorio).
- `def bloquear_franjas_docente( self, usuario_id: int, slots: list[dict] ) -> int` — Carga en lote las franjas no disponibles de un docente (delegado al repositorio).
- `def limpiar_disponibilidad_docente(self, usuario_id: int) -> int` — Borra toda la disponibilidad configurada de un docente (delegado al repositorio).
- `def guardar_disponibilidad_docente( self, usuario_id: int, slots: list[dict] ) -> int` `@requiere_escritura` — Reemplaza ATÓMICAMENTE la disponibilidad de un docente (borra + carga
- `def listar_disponibilidad_docente( self, usuario_id: int ) -> list[DisponibilidadDocente]` — Lista la disponibilidad configurada de un docente (delegado al repositorio).
- `def crear_config_generacion( self, nombre: str, periodo_id: int, anio_id: int, plantilla_id: int, grupos: list[int] | None = None, pesos: dict | None = None, restricciones: dict | None = None, ) -> ConfigGeneracion` `@requiere_escritura` — Crea una config de generación a partir de primitivos (la UI no importa modelos).
- `def construir_restricciones( self, min_horas: int, max_horas: int, modo: str = "preferente" ) -> dict` — Ensambla el payload de restricciones de generación a partir de
- `def listar_configs_generacion( self, periodo_id: int | None = None ) -> list[ConfigGeneracion]` — Lista las configs de generación, opcionalmente de un periodo (delegado al repositorio).
- `def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None` — Retorna una config de generación por id (delegado al repositorio).
- `def actualizar_config_generacion( self, config_id: int, **campos ) -> ConfigGeneracion` `@requiere_escritura` — Actualiza los campos indicados de una config de generación (lanza si no existe).
- `def eliminar_config_generacion(self, config_id: int) -> bool` `@requiere_escritura` — Elimina una config de generación (delegado al repositorio).
- `def cambiar_estado_config( self, config_id: int, nuevo_estado: str ) -> ConfigGeneracion` `@requiere_escritura` — Cambia el estado de una config de generación (delegado al repositorio).
- `def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion` `@requiere_escritura` — Duplica una config de generación (delegado al repositorio).
- `def listar_ventanas_grupo(self) -> list[VentanaGrupo]` — Lista todas las ventanas de grupo (delegado al repositorio).
- `def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]` — Lista las ventanas de un grupo (delegado al repositorio).
- `def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]` — Lista las ventanas de un grado (delegado al repositorio).
- `def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo` `@requiere_escritura` — Crea una ventana de grupo (delegado al repositorio).
- `def eliminar_ventana_grupo(self, ventana_id: int) -> bool` `@requiere_escritura` — Elimina una ventana de grupo (delegado al repositorio).
- `def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]` — Lista los bloques anclados de un escenario (delegado al repositorio).
- `def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado` `@requiere_escritura` — Crea un bloque anclado (delegado al repositorio).
- `def eliminar_bloque_anclado(self, bloque_id: int) -> bool` `@requiere_escritura` — Elimina un bloque anclado (delegado al repositorio).
- `def listar_franjas_reunion(self) -> list[FranjaReunion]` — Lista las franjas de reunión (delegado al repositorio).
- `def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None` — Retorna una franja de reunión por id (delegado al repositorio).
- `def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion` `@requiere_escritura` — Crea una franja de reunión (delegado al repositorio).
- `def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion` `@requiere_escritura` — Actualiza una franja de reunión (lanza si no tiene id).
- `def eliminar_franja_reunion(self, franja_id: int) -> bool` `@requiere_escritura` — Elimina una franja de reunión (delegado al repositorio).
- `def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None` — Retorna los límites diarios de un docente (delegado al repositorio).
- `def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente` `@requiere_escritura` — Crea o actualiza los límites diarios de un docente (delegado al repositorio).
- `def set_limites_docente_simple( self, usuario_id: int, min_horas_dia: int = 0, max_horas_dia: int = 8 ) -> LimitesDocente` `@requiere_escritura` — Crea o actualiza los límites diarios de un docente a partir de primitivos.
- `def listar_limites_docente(self) -> list[LimitesDocente]` — Lista los límites diarios de todos los docentes (delegado al repositorio).

## `sala_service.py`

### SalaService

- `def __init__(self, repo: IInfraestructuraRepository) -> None` — Inyecta el repositorio de infraestructura.
- `def listar_salas(self) -> list[Sala]` — Lista las salas del scope actual (admin ve todas).
- `def get_sala(self, sala_id: int) -> Sala | None` — Retorna una sala por id (delegado al repositorio).
- `def crear_sala(self, sala: Sala) -> Sala` `@requiere_escritura` — Crea una sala, asignándole la institución del scope si falta.
- `def actualizar_sala(self, sala: Sala) -> Sala` `@requiere_escritura` — Actualiza una sala verificando su tenant y preservando su institución.
- `def eliminar_sala(self, sala_id: int) -> bool` `@requiere_escritura` — Elimina una sala tras verificar que pertenece al tenant activo.
- `def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool` `@requiere_escritura` — Asigna (o quita, con None) el aula propia de un grupo.

## `solo_lectura.py`

### OperacionSoloLecturaError(PermissionError)
> Se lanza cuando se intenta una operación de escritura mientras la sesión

- `def __init__(self, mensaje: str | None = None) -> None` — Construye el error con un mensaje por defecto de solo lectura.

### Funciones de módulo

- `def activar_solo_lectura(valor: bool) -> None` — Activa o desactiva el modo solo lectura para el contexto actual.
- `def es_solo_lectura() -> bool` — Indica si el contexto actual está en modo solo lectura.
- `def verificar_escritura() -> None` — Punto de control para métodos de mutación.
- `def requiere_escritura(func: F) -> F` — Decorador equivalente a llamar `verificar_escritura()` al inicio del método.

## `usuario_service.py`

### UsuarioService
> Orquesta los casos de uso del módulo de Usuarios.

- `def __init__( self, repo: IUsuarioRepository, auth_service: IAuthenticationService | None = None, auditoria: IAuditoriaRepository | None = None, ) -> None` — Inyecta el repo de usuarios y los servicios opcionales de
- `def roles_asignables(self, actor_rol: str | None) -> set[str]` — Roles (strings) que `actor_rol` puede asignar o crear.
- `def puede_gestionar(self, actor_rol: str | None, target_rol: str) -> bool` — True si `actor_rol` puede gestionar a un usuario con rol `target_rol`.
- `def requisitos_password() -> list[str]` `@staticmethod` — Textos legibles de las reglas de la política de contraseñas (M4).
- `def crear_usuario( self, dto: NuevoUsuarioDTO, creado_por_id: int | None = None, actor_rol: str | None = None, ) -> Usuario` `@requiere_escritura` — Crea un usuario nuevo.
- `def actualizar( self, usuario_id: int, dto: ActualizarUsuarioDTO, actualizado_por_id: int | None = None, ) -> Usuario` `@requiere_escritura` — Actualiza nombre completo, email y/o teléfono de un usuario.
- `def cambiar_rol( self, usuario_id: int, nuevo_rol: Rol, cambiado_por_id: int | None = None, actor_rol: str | None = None, ) -> Usuario` `@requiere_escritura` — Cambia el rol de un usuario.
- `def desactivar( self, usuario_id: int, desactivado_por_id: int | None = None, actor_rol: str | None = None, ) -> Usuario` `@requiere_escritura` — Desactiva un usuario (soft delete).
- `def reactivar( self, usuario_id: int, reactivado_por_id: int | None = None, actor_rol: str | None = None, ) -> Usuario` `@requiere_escritura` — Reactiva un usuario desactivado.
- `def resetear_password( self, usuario_id: int, nueva_password: str, actor_rol: str | None = None, reset_por_id: int | None = None, ) -> str | None` `@requiere_escritura` — Restablece la contraseña de un usuario SIN verificar la anterior.
- `def cambiar_password( self, usuario_id: int, password_actual: str, password_nuevo: str, ) -> None` `@requiere_escritura` — Cambia la contraseña verificando la actual.
- `def listar_docentes( self, periodo_id: int | None = None, ) -> list[DocenteInfoDTO]` — Retorna los docentes con su carga académica calculada.
- `def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]` — Retorna usuarios según los filtros indicados (auto-scope por tenant).
- `def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]` — Retorna la vista resumida de usuarios (auto-scope por tenant).
- `def listar_para_ver_como( self, institucion_id: int | None = None ) -> list[UsuarioResumenDTO]` — Listado de SOLO LECTURA de usuarios activos candidatos a 'Ver como',
- `def get_by_id(self, usuario_id: int) -> Usuario` — Retorna un usuario por id. Lanza si no existe.
- `def resumen_por_rol(self) -> ResumenUsuariosDTO` — Agregación de SOLO LECTURA para el dashboard de plataforma.
- `def carga_horaria_max(self, usuario_id: int) -> int | None` — Retorna la carga horaria máxima del usuario, o None si no está definida.
- `def configurar_carga( self, usuario_id: int, carga_horaria_max: int | None, horas_extra: int = 0, actualizado_por_id: int | None = None, ) -> Usuario` `@requiere_escritura` — Configura el tope semanal y las horas extra de un docente.

