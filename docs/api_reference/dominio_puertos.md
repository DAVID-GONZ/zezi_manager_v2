# API Reference — Dominio · Puertos

> Generado automáticamente desde `src/domain/ports/` por `tools/gen_api_reference.py` (firmas del fuente + primera línea del docstring). Los métodos sin docstring se marcan `⚠️ sin docstring`. **No editar a mano** — re-generar con el script.

**Cobertura de docstrings:** 337/364 métodos (93%).

| Archivo | Con docstring | Total | % |
|---|---:|---:|---:|
| `src/domain/ports/acudiente_repo.py` | 13 | 13 | 100% |
| `src/domain/ports/alerta_repo.py` | 12 | 12 | 100% |
| `src/domain/ports/asignacion_repo.py` | 11 | 11 | 100% |
| `src/domain/ports/asistencia_repo.py` | 14 | 14 | 100% |
| `src/domain/ports/auditoria_repo.py` | 11 | 11 | 100% |
| `src/domain/ports/cierre_repo.py` | 12 | 12 | 100% |
| `src/domain/ports/configuracion_repo.py` | 18 | 18 | 100% |
| `src/domain/ports/convivencia_repo.py` | 16 | 16 | 100% |
| `src/domain/ports/estadisticos_repo.py` | 18 | 18 | 100% |
| `src/domain/ports/estudiante_repo.py` | 19 | 19 | 100% |
| `src/domain/ports/evaluacion_repo.py` | 24 | 24 | 100% |
| `src/domain/ports/habilitacion_repo.py` | 12 | 12 | 100% |
| `src/domain/ports/infraestructura_repo.py` | 73 | 100 | 73% ⚠️ |
| `src/domain/ports/institucion_repo.py` | 5 | 5 | 100% |
| `src/domain/ports/nivelacion_repo.py` | 11 | 11 | 100% |
| `src/domain/ports/periodo_repo.py` | 16 | 16 | 100% |
| `src/domain/ports/plan_mejoramiento_repo.py` | 15 | 15 | 100% |
| `src/domain/ports/service_ports.py` | 11 | 11 | 100% |
| `src/domain/ports/siee_repo.py` | 8 | 8 | 100% |
| `src/domain/ports/usuario_repo.py` | 18 | 18 | 100% |

## `acudiente_repo.py`

### IAcudienteRepository(ABC)

- `def get_by_id(self, acudiente_id: int) -> Acudiente | None` `@abstractmethod` — Retorna el acudiente con ese id, o None si no existe.
- `def get_by_documento(self, numero_documento: str) -> Acudiente | None` `@abstractmethod` — Busca un acudiente por número de documento.
- `def existe_documento(self, numero_documento: str) -> bool` `@abstractmethod` — True si ya existe un acudiente con ese número de documento.
- `def listar_por_estudiante( self, estudiante_id: int, solo_activos: bool = True, ) -> list[Acudiente]` `@abstractmethod` — Retorna todos los acudientes vinculados a un estudiante,
- `def get_principal(self, estudiante_id: int) -> Acudiente | None` `@abstractmethod` — Retorna el acudiente marcado como principal para un estudiante.
- `def listar_estudiantes_de_acudiente( self, acudiente_id: int, ) -> list[int]` `@abstractmethod` — Retorna los IDs de los estudiantes vinculados a un acudiente.
- `def guardar(self, acudiente: Acudiente) -> Acudiente` `@abstractmethod` — Inserta un acudiente nuevo.
- `def actualizar(self, acudiente: Acudiente) -> Acudiente` `@abstractmethod` — Actualiza los datos de un acudiente existente.
- `def desactivar(self, acudiente_id: int) -> bool` `@abstractmethod` — Marca el acudiente como inactivo (activo=False, soft delete).
- `def vincular(self, vinculo: EstudianteAcudiente) -> None` `@abstractmethod` — Crea el vínculo entre un estudiante y un acudiente.
- `def desvincular( self, estudiante_id: int, acudiente_id: int, ) -> bool` `@abstractmethod` — Elimina el vínculo entre un estudiante y un acudiente.
- `def establecer_principal( self, estudiante_id: int, acudiente_id: int, ) -> None` `@abstractmethod` — Marca un acudiente como principal para un estudiante.
- `def get_vinculo( self, estudiante_id: int, acudiente_id: int, ) -> EstudianteAcudiente | None` `@abstractmethod` — Retorna el vínculo entre un estudiante y un acudiente,

## `alerta_repo.py`

### IAlertaRepository(ABC)

- `def get_configuracion( self, anio_id: int, tipo_alerta: TipoAlerta, ) -> ConfiguracionAlerta | None` `@abstractmethod` — Retorna la configuración de un tipo de alerta para un año lectivo.
- `def listar_configuraciones( self, anio_id: int, solo_activas: bool = True, ) -> list[ConfiguracionAlerta]` `@abstractmethod` — Retorna todas las configuraciones de alerta de un año lectivo,
- `def guardar_configuracion( self, config: ConfiguracionAlerta, ) -> ConfiguracionAlerta` `@abstractmethod` — Inserta o actualiza la configuración de un tipo de alerta
- `def desactivar_configuracion( self, anio_id: int, tipo_alerta: TipoAlerta, ) -> bool` `@abstractmethod` — Marca la configuración como inactiva (activa=False).
- `def get_alerta(self, alerta_id: int) -> Alerta | None` `@abstractmethod` — Retorna la alerta con ese id, o None si no existe.
- `def listar_alertas(self, filtro: FiltroAlertasDTO) -> list[Alerta]` `@abstractmethod` — Retorna alertas según los filtros indicados.
- `def contar_pendientes( self, estudiante_id: int | None = None, nivel: NivelAlerta | None = None, ) -> int` `@abstractmethod` — Cuenta las alertas pendientes. Si estudiante_id es None,
- `def existe_pendiente( self, estudiante_id: int, tipo_alerta: TipoAlerta, ) -> bool` `@abstractmethod` — True si ya existe una alerta pendiente del tipo indicado para ese estudiante.
- `def guardar_alerta(self, alerta: Alerta) -> Alerta` `@abstractmethod` — Inserta una alerta nueva.
- `def guardar_alertas_masivas(self, alertas: list[Alerta]) -> int` `@abstractmethod` — Inserta múltiples alertas en una sola operación.
- `def resolver_alerta( self, alerta_id: int, usuario_id: int, observacion: str | None = None, fecha: datetime | None = None, ) -> bool` `@abstractmethod` — Marca una alerta como resuelta en la BD.
- `def resolver_alertas_de_estudiante( self, estudiante_id: int, tipo_alerta: TipoAlerta, usuario_id: int, observacion: str | None = None, ) -> int` `@abstractmethod` — Resuelve todas las alertas pendientes de un tipo para un estudiante.

## `asignacion_repo.py`

### IAsignacionRepository(ABC)

- `def get_by_id(self, asignacion_id: int) -> Asignacion | None` `@abstractmethod` — Retorna la asignación con ese id, o None si no existe.
- `def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]` `@abstractmethod` — Retorna asignaciones según los filtros indicados.
- `def existe( self, grupo_id: int, asignatura_id: int, usuario_id: int, periodo_id: int, ) -> bool` `@abstractmethod` — True si ya existe una asignación con esa combinación exacta.
- `def get_info(self, asignacion_id: int) -> AsignacionInfo | None` `@abstractmethod` — Retorna la vista enriquecida de una asignación (con nombres
- `def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]` `@abstractmethod` — Retorna vistas enriquecidas de asignaciones según los filtros.
- `def listar_por_grupo( self, grupo_id: int, periodo_id: int, solo_activas: bool = True, institucion_id: int | None = None, ) -> list[AsignacionInfo]` `@abstractmethod` — Retorna todas las asignaciones de un grupo en un periodo.
- `def listar_por_docente( self, usuario_id: int, periodo_id: int | None = None, solo_activas: bool = True, institucion_id: int | None = None, ) -> list[AsignacionInfo]` `@abstractmethod` — Retorna todas las asignaciones de un docente.
- `def guardar(self, asignacion: Asignacion) -> Asignacion` `@abstractmethod` — Inserta una asignación nueva.
- `def desactivar(self, asignacion_id: int) -> bool` `@abstractmethod` — Marca la asignación como inactiva (activo=False, soft-delete).
- `def reactivar(self, asignacion_id: int) -> bool` `@abstractmethod` — Marca la asignación como activa (activo=True).
- `def reasignar_docente( self, asignacion_id: int, nuevo_usuario_id: int, ) -> bool` `@abstractmethod` — Cambia el docente de una asignación existente.

## `asistencia_repo.py`

### IAsistenciaRepository(ABC)

- `def registrar(self, control: ControlDiario) -> ControlDiario` `@abstractmethod` — Inserta o actualiza el registro de asistencia de un estudiante
- `def registrar_masivo(self, controles: list[ControlDiario]) -> int` `@abstractmethod` — Inserta o actualiza múltiples registros en una sola operación.
- `def get_por_fecha_estudiante( self, estudiante_id: int, asignacion_id: int, fecha: date, ) -> ControlDiario | None` `@abstractmethod` — Retorna el registro de asistencia de un estudiante en una
- `def listar_por_grupo_y_fecha( self, grupo_id: int, asignacion_id: int, fecha: date, ) -> list[ControlDiario]` `@abstractmethod` — Retorna todos los registros de asistencia de un grupo en una
- `def listar_por_estudiante_y_periodo( self, estudiante_id: int, periodo_id: int, ) -> list[ControlDiario]` `@abstractmethod` — Retorna todos los registros de asistencia de un estudiante
- `def listar_por_asignacion_y_rango( self, asignacion_id: int, fecha_desde: date, fecha_hasta: date, ) -> list[ControlDiario]` `@abstractmethod` — Retorna los registros de una asignación en un rango de fechas.
- `def resumen_por_estudiante( self, estudiante_id: int, periodo_id: int, asignacion_id: int | None = None, ) -> ResumenAsistenciaDTO` `@abstractmethod` — Calcula el resumen de asistencia de un estudiante en un periodo,
- `def resumen_por_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[ResumenAsistenciaDTO]` `@abstractmethod` — Calcula el resumen de asistencia de todos los estudiantes de un grupo
- `def contar_faltas_injustificadas( self, estudiante_id: int, periodo_id: int, ) -> int` `@abstractmethod` — Cuenta las faltas injustificadas de un estudiante en el periodo.
- `def fechas_con_registro( self, asignacion_id: int, periodo_id: int, ) -> list[date]` `@abstractmethod` — Retorna las fechas que ya tienen registro de asistencia para
- `def porcentaje_asistencia_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> float` `@abstractmethod` — Porcentaje de asistencia promedio del grupo (0.0 a 100.0).
- `def estudiantes_en_riesgo( self, grupo_id: int, asignacion_id: int, periodo_id: int, umbral_pct: float = 80.0, ) -> list[int]` `@abstractmethod` — Retorna los IDs de los estudiantes cuyo porcentaje de asistencia
- `def contar_clases_dictadas_docente(self, usuario_id: int, anio: int, mes: int) -> int` `@abstractmethod` — Cuenta el total de clases dictadas por un docente en un mes/año.
- `def clases_dictadas_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]` `@abstractmethod` — Retorna el desglose de clases dictadas por asignación para un docente

## `auditoria_repo.py`

### IAuditoriaRepository(ABC)

- `def registrar_evento(self, evento: EventoSesion) -> EventoSesion` `@abstractmethod` — Inserta un evento de sesión en la tabla `auditoria`.
- `def listar_eventos(self, filtro: FiltroAuditoriaDTO) -> list[EventoSesion]` `@abstractmethod` — Retorna eventos de sesión según los filtros indicados.
- `def get_ultimo_login(self, usuario_id: int) -> EventoSesion | None` `@abstractmethod` — Retorna el último evento LOGIN_EXITOSO del usuario.
- `def contar_fallos_recientes( self, usuario: str, ventana_minutos: int = 30, ) -> int` `@abstractmethod` — Cuenta los eventos LOGIN_FALLIDO del usuario en los últimos
- `def registrar_cambio(self, registro: RegistroCambio) -> RegistroCambio` `@abstractmethod` — Inserta un registro de cambio en la tabla `audit_log`.
- `def registrar_cambios_masivos(self, registros: list[RegistroCambio]) -> int` `@abstractmethod` — Inserta múltiples registros de cambio en una sola operación.
- `def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]` `@abstractmethod` — Retorna registros de cambio según los filtros indicados.
- `def listar_cambios_por_registro( self, tabla: str, registro_id: int, ) -> list[RegistroCambio]` `@abstractmethod` — Retorna el historial de cambios de un registro específico.
- `def get_cambio(self, cambio_id: int) -> RegistroCambio | None` `@abstractmethod` — Retorna el registro de cambio con ese id, o None si no existe.
- `def verificar_cadena_eventos(self) -> int | None` — Verifica el encadenamiento por hash de la tabla `auditoria`.
- `def verificar_cadena_cambios(self) -> int | None` — Verifica el encadenamiento por hash de la tabla `audit_log`.

## `cierre_repo.py`

### ICierreRepository(ABC)

- `def get_cierre_periodo( self, estudiante_id: int, asignacion_id: int, periodo_id: int ) -> CierrePeriodo | None` `@abstractmethod` — Retorna el cierre de periodo para un estudiante en una asignación y
- `def listar_cierres_periodo_por_estudiante( self, estudiante_id: int, periodo_id: int | None = None ) -> list[CierrePeriodo]` `@abstractmethod` — Retorna los cierres de periodo de un estudiante.
- `def guardar_cierre_periodo(self, cierre: CierrePeriodo) -> CierrePeriodo` `@abstractmethod` — Guarda un cierre de periodo.
- `def get_cierre_anio( self, estudiante_id: int, asignacion_id: int, anio_id: int ) -> CierreAnio | None` `@abstractmethod` — Retorna el cierre anual para un estudiante en una asignación y año
- `def listar_cierres_anio_por_estudiante( self, estudiante_id: int, anio_id: int ) -> list[CierreAnio]` `@abstractmethod` — Retorna todos los cierres anuales de un estudiante en un año específico.
- `def guardar_cierre_anio(self, cierre: CierreAnio) -> CierreAnio` `@abstractmethod` — Guarda un cierre anual.
- `def get_promocion( self, estudiante_id: int, anio_id: int ) -> PromocionAnual | None` `@abstractmethod` — Retorna el registro de promoción de un estudiante para un año.
- `def listar_promociones( self, anio_id: int, estado: EstadoPromocion | None = None ) -> list[PromocionAnual]` `@abstractmethod` — Lista todas las decisiones de promoción de un año.
- `def guardar_promocion(self, promocion: PromocionAnual) -> PromocionAnual` `@abstractmethod` — Inserta un nuevo registro de promoción anual (usualmente inicializado
- `def actualizar_promocion(self, promocion: PromocionAnual) -> PromocionAnual` `@abstractmethod` — Actualiza el estado y detalles de una decisión de promoción existente.
- `def listar_cierres_periodo_por_asignaciones( self, asignacion_ids: list[int], periodo_id: int, nota_maxima: float | None = None, ) -> list[CierrePeriodo]` `@abstractmethod` — Lista cierres de período para varias asignaciones.
- `def borrar_cierres_periodo(self, asignacion_id: int, periodo_id: int) -> int` `@abstractmethod` — Elimina todos los CierrePeriodo de una asignación en un periodo.

## `configuracion_repo.py`

### IConfiguracionRepository(ABC)

- `def get_activa(self, institucion_id: int | None = None) -> ConfiguracionAnio | None` `@abstractmethod` — Retorna la configuración del año lectivo activo.
- `def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None` `@abstractmethod` — Retorna la configuración con ese id, o None si no existe.
- `def get_by_anio( self, institucion_id: int | None, anio: int ) -> ConfiguracionAnio | None` `@abstractmethod` — Busca la configuración por número de año (ej: 2025), scopeada por
- `def listar( self, institucion_id: int | None = None ) -> list[ConfiguracionAnio]` `@abstractmethod` — Retorna las configuraciones anuales ordenadas por año descendente
- `def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio` `@abstractmethod` — Inserta una configuración nueva.
- `def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio` `@abstractmethod` — Actualiza todos los campos de una configuración existente.
- `def activar(self, anio_id: int) -> bool` `@abstractmethod` — Marca el año indicado como activo y desactiva los demás años de la
- `def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]` `@abstractmethod` — Retorna los niveles de desempeño de un año, ordenados por `orden`.
- `def get_nivel(self, nivel_id: int) -> NivelDesempeno | None` `@abstractmethod` — Retorna el nivel con ese id, o None si no existe.
- `def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno` `@abstractmethod` — Inserta un nivel de desempeño nuevo.
- `def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno` `@abstractmethod` — Actualiza un nivel de desempeño existente.
- `def eliminar_nivel(self, nivel_id: int) -> bool` `@abstractmethod` — Elimina un nivel de desempeño.
- `def reemplazar_niveles( self, anio_id: int, niveles: list[NivelDesempeno], ) -> list[NivelDesempeno]` `@abstractmethod` — Reemplaza todos los niveles de un año por la lista provista.
- `def clasificar_nota( self, nota: float, anio_id: int, ) -> NivelDesempeno | None` `@abstractmethod` — Retorna el nivel de desempeño que corresponde a una nota.
- `def get_criterios(self, anio_id: int) -> CriterioPromocion | None` `@abstractmethod` — Retorna los criterios de promoción del año.
- `def guardar_criterios( self, criterios: CriterioPromocion, ) -> CriterioPromocion` `@abstractmethod` — Inserta o actualiza los criterios de promoción para el año
- `def get_numero_periodos(self, anio_id: int) -> int` `@abstractmethod` — Retorna el número de periodos configurados para el año.
- `def guardar_numero_periodos( self, anio_id: int, numero_periodos: int, pesos_iguales: bool = True, ) -> None` `@abstractmethod` — Persiste la configuración de número de periodos para el año.

## `convivencia_repo.py`

### IConvivenciaRepository(ABC)

- `def get_observacion(self, observacion_id: int) -> ObservacionPeriodo | None` `@abstractmethod` — Retorna una observación por su ID, o None si no existe.
- `def get_observacion_por_asignacion( self, estudiante_id: int, asignacion_id: int, periodo_id: int ) -> ObservacionPeriodo | None` `@abstractmethod` — Retorna la observación de una asignatura específica en un periodo.
- `def listar_observaciones_por_estudiante( self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False ) -> list[ObservacionPeriodo]` `@abstractmethod` — Retorna las observaciones de un estudiante.
- `def guardar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo` `@abstractmethod` — Guarda una nueva observación.
- `def actualizar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo` `@abstractmethod` — Actualiza una observación existente (texto o visibilidad).
- `def eliminar_observacion(self, observacion_id: int) -> bool` `@abstractmethod` — Elimina (o desactiva lógicamente) una observación.
- `def get_registro(self, registro_id: int) -> RegistroComportamiento | None` `@abstractmethod` — Retorna un registro de comportamiento por su ID, o None si no existe.
- `def listar_registros( self, filtro: FiltroConvivenciaDTO, institucion_id: int | None = None, ) -> list[RegistroComportamiento]` `@abstractmethod` — Retorna una lista paginada de registros que cumplen con los criterios
- `def contar_registros( self, filtro: FiltroConvivenciaDTO, institucion_id: int | None = None, ) -> int` `@abstractmethod` — Retorna la cantidad total de registros que cumplen con el filtro,
- `def guardar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento` `@abstractmethod` — Guarda un nuevo registro de comportamiento.
- `def actualizar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento` `@abstractmethod` — Actualiza un registro existente (ej. se agregó seguimiento o se
- `def eliminar_registro(self, registro_id: int) -> bool` `@abstractmethod` — Elimina un registro de comportamiento (físico o lógico).
- `def get_nota(self, estudiante_id: int, periodo_id: int) -> NotaComportamiento | None` `@abstractmethod` — Retorna la nota de comportamiento de un estudiante en un periodo,
- `def listar_notas_por_estudiante(self, estudiante_id: int) -> list[NotaComportamiento]` `@abstractmethod` — Retorna todas las notas de comportamiento de un estudiante en los
- `def listar_notas_por_grupo( self, grupo_id: int, periodo_id: int ) -> list[NotaComportamiento]` `@abstractmethod` — Retorna las notas de comportamiento de todos los estudiantes de un grupo
- `def guardar_nota(self, nota: NotaComportamiento) -> NotaComportamiento` `@abstractmethod` — Guarda o actualiza la nota de comportamiento (Upsert).

## `estadisticos_repo.py`

### IEstadisticosRepository(ABC)

- `def calcular_metricas_dashboard( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, ) -> DashboardMetricsDTO` `@abstractmethod` — Calcula todas las métricas del panel principal en una sola operación.
- `def promedio_general_grupo( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, ) -> float` `@abstractmethod` — Promedio de notas definitivas de todos los estudiantes del grupo
- `def porcentaje_asistencia_global( self, grupo_id: int, periodo_id: int, ) -> float` `@abstractmethod` — Porcentaje de asistencia promedio del grupo en todas sus asignaturas.
- `def contar_alertas_pendientes( self, grupo_id: int, ) -> int` `@abstractmethod` — Número de alertas no resueltas de los estudiantes del grupo.
- `def promedio_por_asignacion( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> float` `@abstractmethod` — Promedio de la nota definitiva de todos los estudiantes en una
- `def distribucion_desempenos( self, grupo_id: int, asignacion_id: int, periodo_id: int, niveles: list[NivelDesempeno], ) -> dict[str, int]` `@abstractmethod` — Cuenta cuántos estudiantes cayeron en cada nivel de desempeño.
- `def comparativo_periodos( self, grupo_id: int, asignacion_id: int, anio_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Promedio del grupo por periodo, para mostrar la evolución.
- `def promedios_por_area( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Promedio del grupo por área de conocimiento en el periodo.
- `def estudiantes_en_riesgo_academico( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, min_asignaturas: int = 1, ) -> list[int]` `@abstractmethod` — IDs de estudiantes que tienen al menos `min_asignaturas` asignaturas
- `def ranking_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Estudiantes del grupo ordenados por promedio descendente.
- `def tendencia_asistencia( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Porcentaje de asistencia del grupo por semana o quincena.
- `def distribucion_estados_asistencia( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> dict[str, int]` `@abstractmethod` — Conteo total de registros por estado de asistencia en el periodo.
- `def consolidado_notas_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Tabla completa de notas definitivas por asignatura para todos los
- `def consolidado_asistencia_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Tabla completa de asistencia por asignatura para todos los
- `def consolidado_anual_grupo( self, grupo_id: int, anio_id: int, ) -> list[dict[str, Any]]` `@abstractmethod` — Consolidado anual: nota definitiva por asignatura + estado de
- `def boletin_datos_periodo( self, estudiante_id: int, grupo_id: int, periodo_id: int, ) -> dict[str, Any]` `@abstractmethod` — Datos completos de un estudiante para el boletín de un periodo.
- `def boletin_datos_acumulado( self, estudiante_id: int, grupo_id: int, hasta_periodo_id: int, ) -> dict[str, Any]` `@abstractmethod` — Datos del estudiante para el boletín acumulado hasta un periodo dado.
- `def boletin_datos_anual( self, estudiante_id: int, grupo_id: int, anio_id: int, ) -> dict[str, Any]` `@abstractmethod` — Datos completos de un estudiante para el boletín anual.

## `estudiante_repo.py`

### IEstudianteRepository(ABC)

- `def get_by_id(self, estudiante_id: int) -> Estudiante | None` `@abstractmethod` — Retorna el estudiante con ese id, o None si no existe.
- `def get_by_documento( self, numero_documento: str, institucion_id: int | None = None ) -> Estudiante | None` `@abstractmethod` — Busca un estudiante por número de documento.
- `def existe_documento( self, numero_documento: str, institucion_id: int | None = None ) -> bool` `@abstractmethod` — True si ya existe un estudiante con ese número de documento.
- `def get_resumen(self, estudiante_id: int) -> EstudianteResumenDTO | None` `@abstractmethod` — Retorna la vista reducida del estudiante para selects y referencias.
- `def listar_filtrado( self, filtro: FiltroEstudiantesDTO, ) -> list[Estudiante]` `@abstractmethod` — Retorna estudiantes según los filtros indicados.
- `def listar_resumenes( self, filtro: FiltroEstudiantesDTO, ) -> list[EstudianteResumenDTO]` `@abstractmethod` — Versión optimizada de listar_filtrado que retorna solo los campos
- `def listar_por_grupo( self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None, ) -> list[Estudiante]` `@abstractmethod` — Retorna todos los estudiantes de un grupo, ordenados por apellido.
- `def contar_por_grupo( self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None, ) -> int` `@abstractmethod` — Cuenta los estudiantes de un grupo.
- `def guardar(self, estudiante: Estudiante) -> Estudiante` `@abstractmethod` — Inserta un estudiante nuevo.
- `def actualizar(self, estudiante: Estudiante) -> Estudiante` `@abstractmethod` — Actualiza los datos de un estudiante existente.
- `def actualizar_estado_matricula( self, estudiante_id: int, estado: str, ) -> bool` `@abstractmethod` — Actualiza solo el estado de matrícula de un estudiante.
- `def asignar_grupo(self, estudiante_id: int, grupo_id: int) -> bool` `@abstractmethod` — Asigna o cambia el grupo de un estudiante.
- `def registrar_movimiento( self, estudiante_id: int, grupo_origen_id: int | None, grupo_destino_id: int | None, tipo: TipoMovimiento, motivo: str | None = None, usuario_registro_id: int | None = None, ) -> MovimientoEstudiante` `@abstractmethod` — Inserta un registro en `historial_estudiantes`.
- `def listar_historial( self, estudiante_id: int ) -> list[MovimientoEstudianteInfoDTO]` `@abstractmethod` — Retorna el historial de movimientos de un estudiante, más reciente
- `def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None` `@abstractmethod` — Retorna el PIAR del estudiante para el año indicado.
- `def listar_piars(self, estudiante_id: int) -> list[PIAR]` `@abstractmethod` — Retorna todos los PIARs de un estudiante, ordenados por año descendente.
- `def existe_piar(self, estudiante_id: int, anio_id: int) -> bool` `@abstractmethod` — True si ya existe un PIAR para ese estudiante y año.
- `def guardar_piar(self, piar: PIAR) -> PIAR` `@abstractmethod` — Inserta un PIAR nuevo.
- `def actualizar_piar(self, piar: PIAR) -> PIAR` `@abstractmethod` — Actualiza un PIAR existente.

## `evaluacion_repo.py`

### IEvaluacionRepository(ABC)

- `def listar_categorias( self, asignacion_id: int, periodo_id: int, ) -> list[Categoria]` `@abstractmethod` — Retorna todas las categorías de una asignación en un periodo,
- `def get_categoria(self, cat_id: int) -> Categoria | None` `@abstractmethod` — Retorna la categoría con ese id, o None si no existe.
- `def guardar_categoria(self, categoria: Categoria) -> Categoria` `@abstractmethod` — Inserta una categoría nueva. Retorna la entidad con id asignado.
- `def actualizar_categoria(self, categoria: Categoria) -> Categoria` `@abstractmethod` — Actualiza nombre y/o peso de una categoría existente.
- `def eliminar_categoria(self, cat_id: int) -> None` `@abstractmethod` — Elimina una categoría y todas sus actividades y notas en cascada
- `def suma_pesos_otras( self, asignacion_id: int, periodo_id: int, excluir_cat_id: int | None = None, ) -> float` `@abstractmethod` — Suma de pesos de las categorías existentes para una asignación+periodo,
- `def listar_actividades( self, asignacion_id: int, periodo_id: int, ) -> list[Actividad]` `@abstractmethod` — Retorna todas las actividades de una asignación+periodo,
- `def listar_actividades_por_categoria( self, cat_id: int, ) -> list[Actividad]` `@abstractmethod` — Retorna las actividades de una categoría específica.
- `def listar_actividades_publicadas( self, asignacion_id: int, periodo_id: int, hasta_fecha: date | None = None, ) -> list[Actividad]` `@abstractmethod` — Retorna actividades en estado PUBLICADA o CERRADA.
- `def get_actividad(self, act_id: int) -> Actividad | None` `@abstractmethod` — Retorna la actividad con ese id, o None si no existe.
- `def guardar_actividad(self, actividad: Actividad) -> Actividad` `@abstractmethod` — Inserta una actividad nueva. Retorna la entidad con id asignado.
- `def actualizar_actividad(self, actividad: Actividad) -> Actividad` `@abstractmethod` — Actualiza los campos de una actividad existente.
- `def actualizar_estado_actividad( self, act_id: int, estado: EstadoActividad, ) -> bool` `@abstractmethod` — Actualiza solo el estado de una actividad.
- `def eliminar_actividad(self, act_id: int) -> None` `@abstractmethod` — Elimina una actividad y todas sus notas en cascada.
- `def listar_notas_por_estudiante( self, estudiante_id: int, asignacion_id: int, periodo_id: int, ) -> list[Nota]` `@abstractmethod` — Retorna todas las notas de un estudiante en una asignación+periodo.
- `def listar_notas_por_actividad( self, actividad_id: int, ) -> list[Nota]` `@abstractmethod` — Retorna las notas de todos los estudiantes en una actividad.
- `def get_nota( self, estudiante_id: int, actividad_id: int, ) -> Nota | None` `@abstractmethod` — Retorna la nota de un estudiante en una actividad, o None.
- `def guardar_nota(self, nota: Nota) -> Nota` `@abstractmethod` — Inserta o actualiza la nota de un estudiante en una actividad
- `def guardar_notas_masivas(self, notas: list[Nota]) -> int` `@abstractmethod` — Inserta o actualiza múltiples notas en una sola operación.
- `def eliminar_nota( self, estudiante_id: int, actividad_id: int, ) -> bool` `@abstractmethod` — Elimina la nota de un estudiante en una actividad.
- `def get_puntos_extra( self, estudiante_id: int, asignacion_id: int, periodo_id: int, tipo: TipoPuntosExtra | None = None, ) -> PuntosExtra | None` `@abstractmethod` — Retorna los puntos extra de un estudiante. Si tipo es None,
- `def listar_puntos_extra( self, asignacion_id: int, periodo_id: int, ) -> list[PuntosExtra]` `@abstractmethod` — Retorna todos los puntos extra de una asignación+periodo.
- `def guardar_puntos_extra(self, pe: PuntosExtra) -> PuntosExtra` `@abstractmethod` — Inserta o actualiza los puntos extra (ON CONFLICT REPLACE).
- `def listar_resultados_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[ResultadoEstudianteDTO]` `@abstractmethod` — Retorna el resultado de todos los estudiantes del grupo en una

## `habilitacion_repo.py`

### IHabilitacionRepository(ABC)

- `def get_habilitacion(self, habilitacion_id: int) -> Habilitacion | None` `@abstractmethod` — Retorna la habilitación con ese id, o None si no existe.
- `def listar_habilitaciones( self, filtro: FiltroHabilitacionesDTO, ) -> list[Habilitacion]` `@abstractmethod` — Retorna habilitaciones según los filtros indicados.
- `def listar_por_estudiante( self, estudiante_id: int, periodo_id: int | None = None, tipo: TipoHabilitacion | None = None, ) -> list[Habilitacion]` `@abstractmethod` — Retorna todas las habilitaciones de un estudiante.
- `def existe_habilitacion( self, estudiante_id: int, asignacion_id: int, tipo: TipoHabilitacion, periodo_id: int | None = None, ) -> bool` `@abstractmethod` — True si ya existe una habilitación para esa combinación.
- `def guardar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion` `@abstractmethod` — Inserta una habilitación nueva.
- `def actualizar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion` `@abstractmethod` — Actualiza el estado y los datos de una habilitación existente.
- `def actualizar_estado_habilitacion( self, habilitacion_id: int, estado: EstadoHabilitacion, ) -> bool` `@abstractmethod` — Actualiza solo el estado de una habilitación.
- `def get_plan(self, plan_id: int) -> PlanMejoramiento | None` `@abstractmethod` — Retorna el plan de mejoramiento con ese id, o None si no existe.
- `def listar_planes_por_estudiante( self, estudiante_id: int, asignacion_id: int | None = None, estado: EstadoPlanMejoramiento | None = None, ) -> list[PlanMejoramiento]` `@abstractmethod` — Retorna los planes de mejoramiento de un estudiante.
- `def listar_planes_por_seguimiento( self, fecha_limite: date, solo_activos: bool = True, ) -> list[PlanMejoramiento]` `@abstractmethod` — Retorna planes cuya fecha_seguimiento es menor o igual a fecha_limite.
- `def guardar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento` `@abstractmethod` — Inserta un plan de mejoramiento nuevo.
- `def actualizar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento` `@abstractmethod` — Actualiza un plan de mejoramiento existente.

## `infraestructura_repo.py`

### IInfraestructuraRepository(ABC)

- `def get_escenario(self, escenario_id: int) -> EscenarioHorario | None` `@abstractmethod` — Retorna el escenario con ese id, o None si no existe.
- `def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]` `@abstractmethod` — Retorna todos los escenarios del año, ordenados por nombre.
- `def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None` `@abstractmethod` — Retorna el escenario activo del año, o None si no hay ninguno.
- `def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` `@abstractmethod` — Inserta un escenario nuevo. Retorna la entidad con id asignado.
- `def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` `@abstractmethod` — Actualiza nombre, descripcion y/o activo de un escenario existente.
- `def activar_escenario(self, escenario_id: int) -> None` `@abstractmethod` — Desactiva todos los escenarios del año y activa el indicado.
- `def eliminar_escenario(self, escenario_id: int) -> bool` `@abstractmethod` — Elimina un escenario. Retorna True si la fila fue afectada.
- `def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario` `@abstractmethod` — Crea un nuevo escenario inactivo con el mismo nombre dado
- `def listar_horario_grupo_escenario( self, grupo_id: int, escenario_id: int ) -> list[HorarioInfo]` `@abstractmethod` — Retorna los bloques horarios de un grupo en un escenario específico.
- `def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]` `@abstractmethod` — Retorna todos los bloques horarios de un escenario.
- `def crear_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja` `@abstractmethod` — Inserta una plantilla de franja nueva. Retorna la entidad con id asignado.
- `def get_plantilla_franja(self, plantilla_id: int) -> PlantillaFranja | None` `@abstractmethod` — Retorna la plantilla con ese id, o None si no existe.
- `def listar_plantillas_franja( self, institucion_id: int | None = None ) -> list[PlantillaFranja]` `@abstractmethod` — Retorna las plantillas de franja, ordenadas por nombre.
- `def get_plantilla_activa( self, jornada: str, institucion_id: int | None = None ) -> PlantillaFranja | None` `@abstractmethod` — Retorna la plantilla activa de la jornada indicada, o None.
- `def actualizar_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja` `@abstractmethod` — Actualiza nombre, jornada, dias_activos y/o activa de una plantilla.
- `def activar_plantilla_franja(self, plantilla_id: int) -> None` `@abstractmethod` — Desactiva las demás plantillas de la misma jornada y activa la indicada.
- `def eliminar_plantilla_franja(self, plantilla_id: int) -> bool` `@abstractmethod` — Elimina una plantilla (cascada sobre sus franjas). True si afectó filas.
- `def crear_franja(self, f: Franja) -> Franja` `@abstractmethod` — Inserta una franja nueva. Retorna la entidad con id asignado.
- `def listar_franjas(self, plantilla_id: int) -> list[Franja]` `@abstractmethod` — Retorna las franjas de una plantilla, ordenadas por orden.
- `def actualizar_franja(self, f: Franja) -> Franja` `@abstractmethod` — Actualiza los campos de una franja existente.
- `def eliminar_franja(self, franja_id: int) -> bool` `@abstractmethod` — Elimina una franja. Retorna True si la fila fue afectada.
- `def reemplazar_franjas(self, plantilla_id: int, franjas: list[Franja]) -> int` `@abstractmethod` — Reemplaza atómicamente todo el set de franjas de una plantilla
- `def get_area(self, area_id: int) -> AreaConocimiento | None` `@abstractmethod` — Retorna el área con ese id, o None si no existe.
- `def listar_areas(self) -> list[AreaConocimiento]` `@abstractmethod` — Retorna todas las áreas de conocimiento, ordenadas por nombre.
- `def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento` `@abstractmethod` — Inserta un área nueva. Retorna la entidad con id asignado.
- `def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento` `@abstractmethod` — Actualiza nombre y/o código de un área existente.
- `def eliminar_area(self, area_id: int) -> bool` `@abstractmethod` — Elimina un área. Retorna True si la fila fue afectada.
- `def actualizar_color_area(self, area_id: int, color: str | None) -> bool` `@abstractmethod` — Actualiza solo el color (hex) de un área. None borra el color.
- `def get_asignatura(self, asignatura_id: int) -> Asignatura | None` `@abstractmethod` — Retorna la asignatura con ese id, o None si no existe.
- `def listar_asignaturas( self, area_id: int | None = None, institucion_id: int | None = None, ) -> list[Asignatura]` `@abstractmethod` — Retorna asignaturas, opcionalmente filtradas por área y/o institución.
- `def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura` `@abstractmethod` — Inserta una asignatura nueva. Retorna la entidad con id asignado.
- `def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura` `@abstractmethod` — Actualiza los campos de una asignatura existente.
- `def eliminar_asignatura(self, asignatura_id: int) -> bool` `@abstractmethod` — Elimina una asignatura. Retorna True si la fila fue afectada.
- `def get_grupo(self, grupo_id: int) -> Grupo | None` `@abstractmethod` — Retorna el grupo con ese id, o None si no existe.
- `def get_grupo_por_codigo(self, codigo: str) -> Grupo | None` `@abstractmethod` — Busca un grupo por su código (ej. '601', '1101').
- `def listar_grupos( self, grado: int | None = None, institucion_id: int | None = None, ) -> list[Grupo]` `@abstractmethod` — Retorna grupos, opcionalmente filtrados por grado y/o institución.
- `def guardar_grupo(self, grupo: Grupo) -> Grupo` `@abstractmethod` — Inserta un grupo nuevo. Retorna la entidad con id asignado.
- `def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool` `@abstractmethod` — Asigna (o quita, con None) el aula propia de un grupo.
- `def actualizar_grupo(self, grupo: Grupo) -> Grupo` `@abstractmethod` — Actualiza los campos de un grupo existente.
- `def eliminar_grupo(self, grupo_id: int) -> bool` `@abstractmethod` — Elimina un grupo. Retorna True si la fila fue afectada.
- `def get_horario(self, horario_id: int) -> Horario | None` `@abstractmethod` — Retorna el bloque horario con ese id, o None si no existe.
- `def get_info_horario(self, horario_id: int) -> HorarioInfo | None` `@abstractmethod` — Retorna el bloque horario enriquecido con nombres (JOIN).
- `def listar_horario_grupo( self, grupo_id: int, periodo_id: int, ) -> list[HorarioInfo]` `@abstractmethod` — Retorna todos los bloques horarios de un grupo en un periodo.
- `def listar_horario_docente( self, usuario_id: int, periodo_id: int, ) -> list[HorarioInfo]` `@abstractmethod` — Retorna todos los bloques horarios de un docente en un periodo.
- `def existe_conflicto_horario( self, usuario_id: int, periodo_id: int, dia_semana: str, hora_inicio: str, hora_fin: str, excluir_horario_id: int | None = None, ) -> bool` `@abstractmethod` — True si el docente ya tiene un bloque que se solapa con el
- `def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO` `@abstractmethod` — Retorna métricas del horario maestro para el panel de estadísticas:
- `def guardar_horario(self, horario: Horario) -> Horario` `@abstractmethod` — Inserta un bloque horario nuevo. Retorna la entidad con id asignado.
- `def actualizar_horario(self, horario: Horario) -> Horario` `@abstractmethod` — Actualiza los campos de un bloque horario existente.
- `def eliminar_horario(self, horario_id: int) -> bool` `@abstractmethod` — Elimina un bloque horario. Retorna True si la fila fue afectada.
- `def existe_cruce( self, escenario_id: int, dia_semana: str, hora_inicio: str, hora_fin: str, *, usuario_id: int | None = None, grupo_id: int | None = None, sala: str | None = None, excluir_horario_id: int | None = None, ) -> bool` `@abstractmethod` — True si existe algún bloque en el escenario indicado que se solapa
- `def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int` `@abstractmethod` — Retorna el número de bloques horarios de una asignación en un escenario.
- `def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int` `@abstractmethod` — Retorna el número de bloques horarios de un docente en un escenario.
- `def crear_bloques_masivo(self, horarios: list) -> int` `@abstractmethod` — Inserta múltiples bloques horarios en una sola operación. Retorna el número creados.
- `def eliminar_horarios_por_asignacion(self, asignacion_id: int) -> int` `@abstractmethod` — Elimina todos los bloques horarios de una asignación.
- `def get_logro(self, logro_id: int) -> Logro | None` `@abstractmethod` — Retorna el logro con ese id, o None si no existe.
- `def listar_logros( self, asignacion_id: int, periodo_id: int, ) -> list[Logro]` `@abstractmethod` — Retorna los logros de una asignación en un periodo,
- `def guardar_logro(self, logro: Logro) -> Logro` `@abstractmethod` — Inserta un logro nuevo. Retorna la entidad con id asignado.
- `def actualizar_logro(self, logro: Logro) -> Logro` `@abstractmethod` — Actualiza descripción y/o orden de un logro existente.
- `def eliminar_logro(self, logro_id: int) -> bool` `@abstractmethod` — Elimina un logro. Retorna True si la fila fue afectada.
- `def upsert_disponibilidad(self, d: DisponibilidadDocente) -> DisponibilidadDocente` `@abstractmethod` — Inserta o reemplaza la disponibilidad de un docente en una franja.
- `def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]` `@abstractmethod` — Retorna todas las restricciones de disponibilidad de un docente.
- `def es_disponible(self, usuario_id: int, dia: str, franja_orden: int) -> bool` `@abstractmethod` — Retorna True si el docente está disponible en esa franja.
- `def limpiar_disponibilidad_docente(self, usuario_id: int) -> int` `@abstractmethod` — Borra todas las restricciones de un docente. Retorna filas borradas.
- `def cargar_disponibilidad_lote(self, usuario_id: int, slots: list[dict]) -> int` `@abstractmethod` — Carga en bloque la no-disponibilidad de un docente.
- `def reemplazar_disponibilidad_docente( self, usuario_id: int, slots: list[dict] ) -> int` `@abstractmethod` — Reemplaza ATÓMICAMENTE la disponibilidad de un docente: borra todas
- `def crear_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion` `@abstractmethod` — Inserta una config de generación nueva. Retorna con id asignado.
- `def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None` `@abstractmethod` — Retorna la config con ese id, o None si no existe.
- `def listar_configs_generacion( self, periodo_id: int | None = None ) -> list[ConfigGeneracion]` `@abstractmethod` — Retorna configs, opcionalmente filtradas por periodo.
- `def actualizar_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion` `@abstractmethod` — Actualiza los campos de una config existente.
- `def eliminar_config_generacion(self, config_id: int) -> bool` `@abstractmethod` — Elimina una config. Retorna True si la fila fue afectada.
- `def cambiar_estado_config( self, config_id: int, nuevo_estado: str ) -> ConfigGeneracion` `@abstractmethod` — Cambia el estado de una config validando la transición.
- `def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion` `@abstractmethod` — Crea una copia de la config con nombre '<nombre> (copia)',
- `def listar_salas(self, institucion_id: int | None = None) -> list[Sala]` `@abstractmethod` — Retorna las salas ordenadas por nombre.
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring
- `` `@abstractmethod` — ⚠️ sin docstring

## `institucion_repo.py`

### IInstitucionRepository(ABC)

- `def get_by_id(self, institucion_id: int) -> Institucion | None` `@abstractmethod` — Retorna la institución con ese id, o None si no existe.
- `def listar(self, solo_activas: bool = False) -> list[Institucion]` `@abstractmethod` — Retorna las instituciones ordenadas por id.
- `def existe_nombre(self, nombre: str) -> bool` `@abstractmethod` — True si ya existe una institución con ese nombre (case-insensitive).
- `def guardar(self, institucion: Institucion) -> Institucion` `@abstractmethod` — Inserta una institución nueva. Retorna la entidad con id asignado.
- `def get_por_defecto(self) -> Institucion | None` `@abstractmethod` — Retorna la institución por defecto (id mínimo / institución #1),

## `nivelacion_repo.py`

### INivelacionRepository(ABC)

- `def guardar_actividad(self, actividad: ActividadNivelacion) -> ActividadNivelacion` `@abstractmethod` — Inserta una actividad de nivelación. Retorna la entidad con id.
- `def listar_actividades( self, asignacion_id: int, periodo_id: int, ) -> list[ActividadNivelacion]` `@abstractmethod` — Lista actividades de nivelación para una asignacion+periodo.
- `def get_actividad(self, actividad_id: int) -> ActividadNivelacion | None` `@abstractmethod` — Retorna la actividad por id, o None.
- `def suma_pesos_actividades( self, asignacion_id: int, periodo_id: int, excluir_id: int | None = None, ) -> float` `@abstractmethod` — Suma de pesos de actividades para asignacion+periodo. Excluye excluir_id si dado.
- `def guardar_nota(self, nota: NotaNivelacion) -> NotaNivelacion` `@abstractmethod` — Inserta una nota (upsert por actividad_nivelacion_id+estudiante_id).
- `def actualizar_nota(self, nota: NotaNivelacion) -> NotaNivelacion` `@abstractmethod` — Actualiza el valor de una nota existente.
- `def listar_notas_por_actividad( self, actividad_nivelacion_id: int, ) -> list[NotaNivelacion]` `@abstractmethod` — Lista todas las notas de una actividad.
- `def listar_notas_por_asignacion( self, asignacion_id: int, periodo_id: int, ) -> list[NotaNivelacion]` `@abstractmethod` — Lista todas las notas de una asignacion+periodo (todas las actividades).
- `def get_nota( self, actividad_nivelacion_id: int, estudiante_id: int, ) -> NotaNivelacion | None` `@abstractmethod` — Retorna la nota de un estudiante en una actividad, o None.
- `def guardar_cierre(self, cierre: CierreNivelacion) -> CierreNivelacion` `@abstractmethod` — Persiste el registro de cierre. Retorna con id.
- `def get_cierre( self, asignacion_id: int, periodo_id: int, ) -> CierreNivelacion | None` `@abstractmethod` — Retorna el cierre si existe, None si la nivelación está abierta.

## `periodo_repo.py`

### IPeriodoRepository(ABC)

- `def get_by_id(self, periodo_id: int) -> Periodo | None` `@abstractmethod` — Retorna el periodo con ese id, o None si no existe.
- `def get_por_numero(self, anio_id: int, numero: int) -> Periodo | None` `@abstractmethod` — Retorna el periodo de un año por su número (1–6).
- `def get_activo(self, anio_id: int) -> Periodo | None` `@abstractmethod` — Retorna el periodo activo (activo=True, cerrado=False) del año.
- `def listar_por_anio( self, anio_id: int, incluir_cerrados: bool = True, ) -> list[Periodo]` `@abstractmethod` — Retorna todos los periodos de un año lectivo, ordenados por numero.
- `def suma_pesos_otros( self, anio_id: int, excluir_periodo_id: int | None = None, ) -> float` `@abstractmethod` — Suma de los pesos porcentuales de los periodos del año,
- `def guardar(self, periodo: Periodo) -> Periodo` `@abstractmethod` — Inserta un periodo nuevo. Retorna la entidad con id asignado.
- `def actualizar(self, periodo: Periodo) -> Periodo` `@abstractmethod` — Actualiza un periodo existente (nombre, fechas, peso, activo).
- `def cerrar(self, periodo_id: int) -> bool` `@abstractmethod` — Marca el periodo como cerrado (cerrado=True, activo=False)
- `def activar(self, periodo_id: int) -> bool` `@abstractmethod` — Marca el periodo como activo (activo=True).
- `def desactivar(self, periodo_id: int) -> bool` `@abstractmethod` — Marca el periodo como inactivo (activo=False).
- `def get_hito(self, hito_id: int) -> HitoPeriodo | None` `@abstractmethod` — Retorna el hito con ese id, o None si no existe.
- `def listar_hitos( self, periodo_id: int, tipo: TipoHito | None = None, ) -> list[HitoPeriodo]` `@abstractmethod` — Retorna los hitos de un periodo, opcionalmente filtrados por tipo.
- `def listar_hitos_proximos( self, anio_id: int, dias: int = 7, ) -> list[HitoPeriodo]` `@abstractmethod` — Retorna los hitos de todos los periodos del año cuya fecha_limite
- `def guardar_hito(self, hito: HitoPeriodo) -> HitoPeriodo` `@abstractmethod` — Inserta un hito nuevo. Retorna la entidad con id asignado.
- `def actualizar_hito(self, hito: HitoPeriodo) -> HitoPeriodo` `@abstractmethod` — Actualiza descripción, tipo y/o fecha_limite de un hito existente.
- `def eliminar_hito(self, hito_id: int) -> bool` `@abstractmethod` — Elimina un hito. Retorna True si la fila fue afectada.

## `plan_mejoramiento_repo.py`

### IPlanMejoramientoRepository(ABC)
> Contrato que toda implementación de repositorio debe cumplir.

- `def guardar_corte(self, corte: CortePlan) -> CortePlan` `@abstractmethod` — Persiste un nuevo corte. Retorna la instancia con id asignado.
- `def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None` `@abstractmethod` — Obtiene el corte de una asignación en un periodo, o None.
- `def get_corte_by_id(self, corte_id: int) -> CortePlan | None` `@abstractmethod` — Obtiene un corte por su id primario.
- `def guardar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan` `@abstractmethod` — Persiste una nota de corte (INSERT OR REPLACE).
- `def get_nota_corte(self, corte_id: int, estudiante_id: int) -> NotaCortePlan | None` `@abstractmethod` — Obtiene la nota de corte de un estudiante específico.
- `def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]` `@abstractmethod` — Lista todas las notas de corte para un corte dado.
- `def actualizar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan` `@abstractmethod` — Actualiza una nota de corte existente (cierre de plan).
- `def guardar_actividad(self, actividad: ActividadPlan) -> ActividadPlan` `@abstractmethod` — Persiste una nueva actividad de plan.
- `def get_actividad(self, actividad_id: int) -> ActividadPlan | None` `@abstractmethod` — Obtiene una actividad por su id.
- `def listar_actividades(self, corte_id: int) -> list[ActividadPlan]` `@abstractmethod` — Lista todas las actividades de un corte.
- `def suma_pesos_actividades(self, corte_id: int, excluir_id: int | None = None) -> float` `@abstractmethod` — Suma de pesos de las actividades de un corte, excluyendo opcionalmente una.
- `def guardar_nota_actividad(self, nota: NotaActividadPlan) -> NotaActividadPlan` `@abstractmethod` — Persiste una nota de actividad (INSERT OR REPLACE).
- `def get_nota_actividad( self, actividad_plan_id: int, estudiante_id: int ) -> NotaActividadPlan | None` `@abstractmethod` — Obtiene la nota de un estudiante para una actividad.
- `def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]` `@abstractmethod` — Lista todas las notas de una actividad.
- `def listar_notas_por_corte_estudiante( self, corte_id: int, estudiante_id: int ) -> list[NotaActividadPlan]` `@abstractmethod` — Lista todas las notas de actividades del plan para un estudiante en un corte.

## `service_ports.py`

### IAuthenticationService(ABC)
> Gestión de credenciales de usuarios.

- `def hashear_password(self, password_plain: str) -> str` `@abstractmethod` — Retorna el hash seguro de una contraseña en texto plano.
- `def verificar_password( self, password_plain: str, password_hash: str, ) -> bool` `@abstractmethod` — True si la contraseña en texto plano coincide con el hash almacenado.
- `def cambiar_password( self, usuario_id: int, password_actual: str, password_nueva: str, ) -> bool` `@abstractmethod` — Verifica password_actual y, si es correcta, persiste el hash
- `def resetear_password( self, usuario_id: int, password_nueva: str, ) -> None` `@abstractmethod` — Establece una nueva contraseña sin verificar la anterior.
- `def autenticar_usuario( self, nombre_usuario: str, password_plain: str, ) -> "Usuario"` `@abstractmethod` — Autentica un usuario por nombre de usuario y contraseña en texto plano.

### INotificationService(ABC)
> Envío de notificaciones a usuarios, docentes y acudientes.

- `def notificar_acudiente( self, acudiente_id: int, asunto: str, cuerpo: str, ) -> bool` `@abstractmethod` — Envía una notificación al acudiente indicado.
- `def notificar_docente( self, usuario_id: int, asunto: str, cuerpo: str, ) -> bool` `@abstractmethod` — Envía una notificación a un docente.
- `def notificar_directivos( self, asunto: str, cuerpo: str, ) -> int` `@abstractmethod` — Envía una notificación a todos los usuarios con rol

### IExporterService(ABC)
> Exportación de datos a formatos externos para descarga.

- `def exportar_excel( self, datos: list[dict], nombre_hoja: str = "Datos", ruta_destino: Path | None = None, ) -> bytes` `@abstractmethod` — Genera un archivo Excel (.xlsx) con los datos indicados.
- `def exportar_pdf( self, html_content: str, ruta_destino: Path | None = None, ) -> bytes` `@abstractmethod` — Genera un PDF a partir de HTML con estilos CSS.
- `def exportar_csv( self, datos: list[dict], ruta_destino: Path | None = None, encoding: str = "utf-8-sig", ) -> bytes` `@abstractmethod` — Genera un archivo CSV con los datos indicados.

## `siee_repo.py`

### ISIEERepository(ABC)

- `def get_configuracion(self, anio_id: int) -> ConfiguracionSIEE | None` `@abstractmethod` — Retorna la configuración SIEE del año, o None si no ha sido configurada.
- `def guardar_configuracion(self, cfg: ConfiguracionSIEE) -> ConfiguracionSIEE` `@abstractmethod` — Inserta o reemplaza la configuración SIEE del año.
- `def listar_categorias_institucionales(self, anio_id: int) -> list[Categoria]` `@abstractmethod` — Retorna las categorías institucionales del año, ordenadas por nombre.
- `def get_categoria_institucional(self, cat_id: int) -> Categoria | None` `@abstractmethod` — Retorna la categoría institucional con ese id, o None.
- `def guardar_categoria_institucional(self, cat: Categoria) -> Categoria` `@abstractmethod` — Inserta una categoría institucional nueva.
- `def actualizar_categoria_institucional(self, cat: Categoria) -> Categoria` `@abstractmethod` — Actualiza nombre, peso y permite_subcategorias de una categoría institucional.
- `def eliminar_categoria_institucional(self, cat_id: int) -> None` `@abstractmethod` — Elimina una categoría institucional.
- `def suma_pesos_institucionales(self, anio_id: int) -> float` `@abstractmethod` — Suma de pesos de todas las categorías institucionales del año.

## `usuario_repo.py`

### IUsuarioRepository(ABC)

- `def get_by_id(self, usuario_id: int) -> Usuario | None` `@abstractmethod` — Retorna el usuario con ese id, o None si no existe.
- `def get_by_username(self, username: str) -> Usuario | None` `@abstractmethod` — Busca un usuario por su nombre de usuario (case-insensitive).
- `def get_by_email(self, email: str) -> Usuario | None` `@abstractmethod` — Busca un usuario por email. Retorna None si no existe.
- `def existe_usuario(self, username: str) -> bool` `@abstractmethod` — True si ya existe un usuario con ese nombre de usuario.
- `def listar_filtrado( self, filtro: FiltroUsuariosDTO, ) -> list[Usuario]` `@abstractmethod` — Retorna usuarios según los filtros indicados.
- `def listar_resumenes( self, filtro: FiltroUsuariosDTO, ) -> list[UsuarioResumenDTO]` `@abstractmethod` — Versión optimizada para selects y lookups: retorna solo los campos
- `def listar_docentes_info( self, periodo_id: int | None = None, solo_activos: bool = True, ) -> list[DocenteInfoDTO]` `@abstractmethod` — Retorna los docentes con su carga académica calculada por JOIN.
- `def get_docente_info( self, usuario_id: int, periodo_id: int | None = None, ) -> DocenteInfoDTO | None` `@abstractmethod` — Retorna la vista estadística de un docente específico.
- `def listar_asignaciones_docente( self, usuario_id: int, periodo_id: int | None = None, ) -> list[AsignacionDocenteInfoDTO]` `@abstractmethod` — Retorna el detalle de las asignaciones de un docente, con la
- `def guardar(self, usuario: Usuario) -> Usuario` `@abstractmethod` — Inserta un usuario nuevo. Retorna la entidad con id asignado.
- `def actualizar(self, usuario: Usuario) -> Usuario` `@abstractmethod` — Actualiza nombre_completo, email y teléfono de un usuario.
- `def actualizar_carga( self, usuario_id: int, carga_horaria_max: int | None, horas_extra: int ) -> bool` `@abstractmethod` — Actualiza el tope semanal de carga y las horas extra de un docente.
- `def cambiar_rol(self, usuario_id: int, nuevo_rol: Rol) -> bool` `@abstractmethod` — Cambia el rol de un usuario.
- `def desactivar(self, usuario_id: int) -> bool` `@abstractmethod` — Marca el usuario como inactivo (activo=False, soft-delete).
- `def reactivar(self, usuario_id: int) -> bool` `@abstractmethod` — Marca el usuario como activo (activo=True).
- `def marcar_debe_cambiar_password(self, usuario_id: int, valor: bool) -> bool` `@abstractmethod` — Activa o limpia el flag `debe_cambiar_password` del usuario (A2).
- `def get_password_hash(self, usuario_id: int) -> str | None` `@abstractmethod` — Retorna el hash de contraseña almacenado para el usuario.
- `def actualizar_password_hash(self, usuario_id: int, nuevo_hash: str) -> bool` `@abstractmethod` — Persiste el hash de contraseña en la BD.

