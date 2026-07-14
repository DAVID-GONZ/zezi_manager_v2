# API Reference — Infraestructura

> Generado automáticamente desde `src/infrastructure/` por `tools/gen_api_reference.py` (firmas del fuente + primera línea del docstring). Los métodos sin docstring se marcan `⚠️ sin docstring`. **No editar a mano** — re-generar con el script.

**Cobertura de docstrings:** 35/429 métodos (8%).

| Archivo | Con docstring | Total | % |
|---|---:|---:|---:|
| `src/infrastructure/auth/bcrypt_auth.py` | 2 | 2 | 100% |
| `src/infrastructure/auth/bcrypt_auth_service.py` | 5 | 6 | 83% ⚠️ |
| `src/infrastructure/auth/jwt_handler.py` | 5 | 6 | 83% ⚠️ |
| `src/infrastructure/context/context_initializer.py` | 3 | 3 | 100% |
| `src/infrastructure/db/connection.py` | 2 | 2 | 100% |
| `src/infrastructure/db/queries.py` | 5 | 5 | 100% |
| `src/infrastructure/db/repositories/sqlite_acudiente_repo.py` | 0 | 14 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_alerta_repo.py` | 0 | 13 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_asignacion_repo.py` | 0 | 12 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_asistencia_repo.py` | 0 | 15 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | 0 | 12 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_cierre_repo.py` | 0 | 13 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_configuracion_repo.py` | 0 | 19 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_convivencia_repo.py` | 0 | 17 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_estadisticos_repo.py` | 0 | 19 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_estudiante_repo.py` | 0 | 20 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_evaluacion_repo.py` | 0 | 25 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_habilitacion_repo.py` | 0 | 13 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_infraestructura_repo.py` | 1 | 101 | 1% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_institucion_repo.py` | 0 | 6 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_nivelacion_repo.py` | 0 | 12 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_periodo_repo.py` | 0 | 17 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_plan_mejoramiento_repo.py` | 0 | 15 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_siee_repo.py` | 0 | 9 | 0% ⚠️ |
| `src/infrastructure/db/repositories/sqlite_usuario_repo.py` | 1 | 19 | 5% ⚠️ |
| `src/infrastructure/db/schema.py` | 2 | 2 | 100% |
| `src/infrastructure/db/seed.py` | 4 | 5 | 80% ⚠️ |
| `src/infrastructure/exporters/boletin_pdf.py` | 3 | 3 | 100% |
| `src/infrastructure/exporters/exporter_factory.py` | 1 | 1 | 100% |
| `src/infrastructure/exporters/null_exporter.py` | 0 | 3 | 0% ⚠️ |
| `src/infrastructure/exporters/openpyxl_exporter.py` | 1 | 3 | 33% ⚠️ |
| `src/infrastructure/exporters/pdf_exporter.py` | 0 | 7 | 0% ⚠️ |
| `src/infrastructure/notifications/log_notification_service.py` | 0 | 6 | 0% ⚠️ |
| `src/infrastructure/notifications/null_notification_service.py` | 0 | 4 | 0% ⚠️ |

## `auth/bcrypt_auth.py`

### Funciones de módulo

- `def hashear(password: str) -> str` — Genera un hash bcrypt con salt aleatorio.
- `def verificar(password: str, password_hash: str) -> bool` — Verifica un password contra su hash bcrypt.

## `auth/bcrypt_auth_service.py`

### BcryptAuthService(IAuthenticationService)
> Autenticación basada en bcrypt.

- `def __init__(self, repo: IUsuarioRepository | None = None) -> None` — ⚠️ sin docstring
- `def hashear_password(self, password_plain: str) -> str` — Genera un hash bcrypt con salt interno aleatorio.
- `def verificar_password(self, password_plain: str, password_hash: str) -> bool` — Verifica el password contra su hash.
- `def cambiar_password( self, usuario_id: int, password_actual: str, password_nueva: str, ) -> bool` — Verifica la contraseña actual y, si es correcta, persiste el nuevo hash.
- `def resetear_password(self, usuario_id: int, password_nueva: str) -> None` — Establece una nueva contraseña sin verificar la anterior.
- `def autenticar_usuario( self, nombre_usuario: str, password_plain: str, ) -> Usuario` — Autentica un usuario por nombre de usuario y contraseña en texto plano.

## `auth/jwt_handler.py`

### JWTHandler
> Manejador de tokens JWT con firma HMAC-SHA256 (HS256).

- `def __init__(self, secret: str, expiracion_horas: int = 8) -> None` — ⚠️ sin docstring
- `def crear_token(self, payload: dict[str, Any]) -> str` — Genera un token JWT firmado con los datos del payload.
- `def verificar_token(self, token: str) -> dict[str, Any] | None` — Verifica firma e integridad; retorna el payload si es válido.
- `def token_expirado(self, token: str) -> bool` — True si el token tiene firma válida pero ya expiró.

### Funciones de módulo

- `def crear_token(payload: dict[str, Any], secret: str, expiracion_horas: int = 8) -> str` — Atajo funcional para crear un token sin instanciar JWTHandler.
- `def verificar_token(token: str, secret: str) -> dict[str, Any] | None` — Atajo funcional para verificar un token sin instanciar JWTHandler.

## `context/context_initializer.py`

### ContextInitializer
> Resuelve y escribe el contexto académico inicial de un usuario.

- `def inicializar(ctx: "SessionContext") -> "SessionContext"` `@staticmethod` — Punto de entrada principal.
- `def contexto_es_valido(ctx: "SessionContext") -> bool` `@staticmethod` — Verifica que el contexto guardado sigue siendo válido en la BD.
- `def refrescar_si_invalido(ctx: "SessionContext") -> "SessionContext"` `@staticmethod` — Si el contexto guardado no es válido, lo limpia y re-inicializa.

## `db/connection.py`

### Funciones de módulo

- `def get_connection( db_path: Path | str | None = None, timeout: float = 5.0, ) -> Iterator[sqlite3.Connection]` — Context manager que abre, configura y cierra una conexión SQLite.
- `def verify_db_integrity(db_path: Path | str | None = None) -> bool` — Ejecuta PRAGMA integrity_check sobre la BD.

## `db/queries.py`

### Funciones de módulo

- `def fetch_df( query: str, params: tuple | list | None = None, return_empty_on_error: bool = True, ) -> pd.DataFrame | None` — Ejecuta un SELECT y retorna un DataFrame de pandas.
- `def fetch_one( query: str, params: tuple | list | None = None, ) -> dict[str, Any] | None` — Ejecuta un SELECT y retorna la primera fila como diccionario.
- `def fetch_all( query: str, params: tuple | list | None = None, ) -> list[dict[str, Any]]` — Ejecuta un SELECT y retorna todas las filas como lista de diccionarios.
- `def get_scalar( query: str, params: tuple | list | None = None, default: Any = None, ) -> Any` — Ejecuta un SELECT y retorna el valor de la primera columna de la primera fila.
- `def execute( query: str, params: tuple | list | dict | None = None, return_metadata: bool = False, ) -> bool | dict[str, Any]` — Ejecuta un INSERT, UPDATE o DELETE con commit automático.

## `db/repositories/sqlite_acudiente_repo.py`

### SqliteAcudienteRepository(IAcudienteRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_by_id(self, acudiente_id: int) -> Acudiente | None` — ⚠️ sin docstring
- `def get_by_documento(self, numero_documento: str) -> Acudiente | None` — ⚠️ sin docstring
- `def existe_documento(self, numero_documento: str) -> bool` — ⚠️ sin docstring
- `def listar_por_estudiante( self, estudiante_id: int, solo_activos: bool = True, ) -> list[Acudiente]` — ⚠️ sin docstring
- `def get_principal(self, estudiante_id: int) -> Acudiente | None` — ⚠️ sin docstring
- `def listar_estudiantes_de_acudiente(self, acudiente_id: int) -> list[int]` — ⚠️ sin docstring
- `def guardar(self, acudiente: Acudiente) -> Acudiente` — ⚠️ sin docstring
- `def actualizar(self, acudiente: Acudiente) -> Acudiente` — ⚠️ sin docstring
- `def desactivar(self, acudiente_id: int) -> bool` — ⚠️ sin docstring
- `def vincular(self, vinculo: EstudianteAcudiente) -> None` — ⚠️ sin docstring
- `def desvincular(self, estudiante_id: int, acudiente_id: int) -> bool` — ⚠️ sin docstring
- `def establecer_principal(self, estudiante_id: int, acudiente_id: int) -> None` — ⚠️ sin docstring
- `def get_vinculo( self, estudiante_id: int, acudiente_id: int ) -> EstudianteAcudiente | None` — ⚠️ sin docstring

## `db/repositories/sqlite_alerta_repo.py`

### SqliteAlertaRepository(IAlertaRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_configuracion( self, anio_id: int, tipo_alerta: TipoAlerta, ) -> ConfiguracionAlerta | None` — ⚠️ sin docstring
- `def listar_configuraciones( self, anio_id: int, solo_activas: bool = True, ) -> list[ConfiguracionAlerta]` — ⚠️ sin docstring
- `def guardar_configuracion( self, config: ConfiguracionAlerta, ) -> ConfiguracionAlerta` — ⚠️ sin docstring
- `def desactivar_configuracion( self, anio_id: int, tipo_alerta: TipoAlerta, ) -> bool` — ⚠️ sin docstring
- `def get_alerta(self, alerta_id: int) -> Alerta | None` — ⚠️ sin docstring
- `def listar_alertas(self, filtro: FiltroAlertasDTO) -> list[Alerta]` — ⚠️ sin docstring
- `def contar_pendientes( self, estudiante_id: int | None = None, nivel: NivelAlerta | None = None, ) -> int` — ⚠️ sin docstring
- `def existe_pendiente( self, estudiante_id: int, tipo_alerta: TipoAlerta, ) -> bool` — ⚠️ sin docstring
- `def guardar_alerta(self, alerta: Alerta) -> Alerta` — ⚠️ sin docstring
- `def guardar_alertas_masivas(self, alertas: list[Alerta]) -> int` — ⚠️ sin docstring
- `def resolver_alerta( self, alerta_id: int, usuario_id: int, observacion: str | None = None, fecha: datetime | None = None, ) -> bool` — ⚠️ sin docstring
- `def resolver_alertas_de_estudiante( self, estudiante_id: int, tipo_alerta: TipoAlerta, usuario_id: int, observacion: str | None = None, ) -> int` — ⚠️ sin docstring

## `db/repositories/sqlite_asignacion_repo.py`

### SqliteAsignacionRepository(IAsignacionRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_by_id(self, asignacion_id: int) -> Asignacion | None` — ⚠️ sin docstring
- `def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]` — ⚠️ sin docstring
- `def existe( self, grupo_id: int, asignatura_id: int, usuario_id: int, periodo_id: int, ) -> bool` — ⚠️ sin docstring
- `def get_info(self, asignacion_id: int) -> AsignacionInfo | None` — ⚠️ sin docstring
- `def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]` — ⚠️ sin docstring
- `def listar_por_grupo( self, grupo_id: int, periodo_id: int, solo_activas: bool = True, institucion_id: int | None = None, ) -> list[AsignacionInfo]` — ⚠️ sin docstring
- `def listar_por_docente( self, usuario_id: int, periodo_id: int | None = None, solo_activas: bool = True, institucion_id: int | None = None, ) -> list[AsignacionInfo]` — ⚠️ sin docstring
- `def guardar(self, asignacion: Asignacion) -> Asignacion` — ⚠️ sin docstring
- `def desactivar(self, asignacion_id: int) -> bool` — ⚠️ sin docstring
- `def reactivar(self, asignacion_id: int) -> bool` — ⚠️ sin docstring
- `def reasignar_docente( self, asignacion_id: int, nuevo_usuario_id: int, ) -> bool` — ⚠️ sin docstring

## `db/repositories/sqlite_asistencia_repo.py`

### SqliteAsistenciaRepository(IAsistenciaRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def registrar(self, control: ControlDiario) -> ControlDiario` — ⚠️ sin docstring
- `def registrar_masivo(self, controles: list[ControlDiario]) -> int` — ⚠️ sin docstring
- `def get_por_fecha_estudiante( self, estudiante_id: int, asignacion_id: int, fecha: date, ) -> ControlDiario | None` — ⚠️ sin docstring
- `def listar_por_grupo_y_fecha( self, grupo_id: int, asignacion_id: int, fecha: date, ) -> list[ControlDiario]` — ⚠️ sin docstring
- `def listar_por_estudiante_y_periodo( self, estudiante_id: int, periodo_id: int, ) -> list[ControlDiario]` — ⚠️ sin docstring
- `def listar_por_asignacion_y_rango( self, asignacion_id: int, fecha_desde: date, fecha_hasta: date, ) -> list[ControlDiario]` — ⚠️ sin docstring
- `def resumen_por_estudiante( self, estudiante_id: int, periodo_id: int, asignacion_id: int | None = None, ) -> ResumenAsistenciaDTO` — ⚠️ sin docstring
- `def resumen_por_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[ResumenAsistenciaDTO]` — ⚠️ sin docstring
- `def contar_faltas_injustificadas( self, estudiante_id: int, periodo_id: int, ) -> int` — ⚠️ sin docstring
- `def fechas_con_registro( self, asignacion_id: int, periodo_id: int, ) -> list[date]` — ⚠️ sin docstring
- `def porcentaje_asistencia_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> float` — ⚠️ sin docstring
- `def estudiantes_en_riesgo( self, grupo_id: int, asignacion_id: int, periodo_id: int, umbral_pct: float = 80.0, ) -> list[int]` — ⚠️ sin docstring
- `def contar_clases_dictadas_docente(self, usuario_id: int, anio: int, mes: int) -> int` — ⚠️ sin docstring
- `def clases_dictadas_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]` — ⚠️ sin docstring

## `db/repositories/sqlite_auditoria_repo.py`

### SqliteAuditoriaRepository(IAuditoriaRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def registrar_evento(self, evento: EventoSesion) -> EventoSesion` — ⚠️ sin docstring
- `def listar_eventos(self, filtro: FiltroAuditoriaDTO) -> list[EventoSesion]` — ⚠️ sin docstring
- `def get_ultimo_login(self, usuario_id: int) -> EventoSesion | None` — ⚠️ sin docstring
- `def contar_fallos_recientes( self, usuario: str, ventana_minutos: int = 30, ) -> int` — ⚠️ sin docstring
- `def registrar_cambio(self, registro: RegistroCambio) -> RegistroCambio` — ⚠️ sin docstring
- `def registrar_cambios_masivos(self, registros: list[RegistroCambio]) -> int` — ⚠️ sin docstring
- `def verificar_cadena_eventos(self) -> int | None` — ⚠️ sin docstring
- `def verificar_cadena_cambios(self) -> int | None` — ⚠️ sin docstring
- `def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]` — ⚠️ sin docstring
- `def listar_cambios_por_registro( self, tabla: str, registro_id: int, ) -> list[RegistroCambio]` — ⚠️ sin docstring
- `def get_cambio(self, cambio_id: int) -> RegistroCambio | None` — ⚠️ sin docstring

## `db/repositories/sqlite_cierre_repo.py`

### SqliteCierreRepository(ICierreRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_cierre_periodo( self, estudiante_id: int, asignacion_id: int, periodo_id: int ) -> CierrePeriodo | None` — ⚠️ sin docstring
- `def listar_cierres_periodo_por_estudiante( self, estudiante_id: int, periodo_id: int | None = None ) -> list[CierrePeriodo]` — ⚠️ sin docstring
- `def guardar_cierre_periodo(self, cierre: CierrePeriodo) -> CierrePeriodo` — ⚠️ sin docstring
- `def listar_cierres_periodo_por_asignaciones( self, asignacion_ids: list[int], periodo_id: int, nota_maxima: float | None = None, ) -> list[CierrePeriodo]` — ⚠️ sin docstring
- `def borrar_cierres_periodo(self, asignacion_id: int, periodo_id: int) -> int` — ⚠️ sin docstring
- `def get_cierre_anio( self, estudiante_id: int, asignacion_id: int, anio_id: int ) -> CierreAnio | None` — ⚠️ sin docstring
- `def listar_cierres_anio_por_estudiante( self, estudiante_id: int, anio_id: int ) -> list[CierreAnio]` — ⚠️ sin docstring
- `def guardar_cierre_anio(self, cierre: CierreAnio) -> CierreAnio` — ⚠️ sin docstring
- `def get_promocion( self, estudiante_id: int, anio_id: int ) -> PromocionAnual | None` — ⚠️ sin docstring
- `def listar_promociones( self, anio_id: int, estado: EstadoPromocion | None = None ) -> list[PromocionAnual]` — ⚠️ sin docstring
- `def guardar_promocion(self, promocion: PromocionAnual) -> PromocionAnual` — ⚠️ sin docstring
- `def actualizar_promocion(self, promocion: PromocionAnual) -> PromocionAnual` — ⚠️ sin docstring

## `db/repositories/sqlite_configuracion_repo.py`

### SqliteConfiguracionRepository(IConfiguracionRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_activa(self, institucion_id: int | None = None) -> ConfiguracionAnio | None` — ⚠️ sin docstring
- `def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None` — ⚠️ sin docstring
- `def get_by_anio( self, institucion_id: int | None, anio: int ) -> ConfiguracionAnio | None` — ⚠️ sin docstring
- `def listar( self, institucion_id: int | None = None ) -> list[ConfiguracionAnio]` — ⚠️ sin docstring
- `def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio` — ⚠️ sin docstring
- `def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio` — ⚠️ sin docstring
- `def activar(self, anio_id: int) -> bool` — ⚠️ sin docstring
- `def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]` — ⚠️ sin docstring
- `def get_nivel(self, nivel_id: int) -> NivelDesempeno | None` — ⚠️ sin docstring
- `def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno` — ⚠️ sin docstring
- `def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno` — ⚠️ sin docstring
- `def eliminar_nivel(self, nivel_id: int) -> bool` — ⚠️ sin docstring
- `def reemplazar_niveles( self, anio_id: int, niveles: list[NivelDesempeno], ) -> list[NivelDesempeno]` — ⚠️ sin docstring
- `def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None` — ⚠️ sin docstring
- `def get_criterios(self, anio_id: int) -> CriterioPromocion | None` — ⚠️ sin docstring
- `def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion` — ⚠️ sin docstring
- `def get_numero_periodos(self, anio_id: int) -> int` — ⚠️ sin docstring
- `def guardar_numero_periodos( self, anio_id: int, numero_periodos: int, pesos_iguales: bool = True, ) -> None` — ⚠️ sin docstring

## `db/repositories/sqlite_convivencia_repo.py`

### SqliteConvivenciaRepository(IConvivenciaRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_observacion(self, observacion_id: int) -> ObservacionPeriodo | None` — ⚠️ sin docstring
- `def get_observacion_por_asignacion( self, estudiante_id: int, asignacion_id: int, periodo_id: int ) -> ObservacionPeriodo | None` — ⚠️ sin docstring
- `def listar_observaciones_por_estudiante( self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False ) -> list[ObservacionPeriodo]` — ⚠️ sin docstring
- `def guardar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo` — ⚠️ sin docstring
- `def actualizar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo` — ⚠️ sin docstring
- `def eliminar_observacion(self, observacion_id: int) -> bool` — ⚠️ sin docstring
- `def get_registro(self, registro_id: int) -> RegistroComportamiento | None` — ⚠️ sin docstring
- `def listar_registros( self, filtro: FiltroConvivenciaDTO, institucion_id: int | None = None, ) -> list[RegistroComportamiento]` — ⚠️ sin docstring
- `def contar_registros( self, filtro: FiltroConvivenciaDTO, institucion_id: int | None = None, ) -> int` — ⚠️ sin docstring
- `def guardar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento` — ⚠️ sin docstring
- `def actualizar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento` — ⚠️ sin docstring
- `def eliminar_registro(self, registro_id: int) -> bool` — ⚠️ sin docstring
- `def get_nota(self, estudiante_id: int, periodo_id: int) -> NotaComportamiento | None` — ⚠️ sin docstring
- `def listar_notas_por_estudiante(self, estudiante_id: int) -> list[NotaComportamiento]` — ⚠️ sin docstring
- `def listar_notas_por_grupo( self, grupo_id: int, periodo_id: int ) -> list[NotaComportamiento]` — ⚠️ sin docstring
- `def guardar_nota(self, nota: NotaComportamiento) -> NotaComportamiento` — ⚠️ sin docstring

## `db/repositories/sqlite_estadisticos_repo.py`

### SqliteEstadisticosRepository(IEstadisticosRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def calcular_metricas_dashboard( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, ) -> DashboardMetricsDTO` — ⚠️ sin docstring
- `def promedio_general_grupo( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, ) -> float` — ⚠️ sin docstring
- `def porcentaje_asistencia_global( self, grupo_id: int, periodo_id: int, ) -> float` — ⚠️ sin docstring
- `def contar_alertas_pendientes(self, grupo_id: int) -> int` — ⚠️ sin docstring
- `def promedio_por_asignacion( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> float` — ⚠️ sin docstring
- `def distribucion_desempenos( self, grupo_id: int, asignacion_id: int, periodo_id: int, niveles: list[NivelDesempeno], ) -> dict[str, int]` — ⚠️ sin docstring
- `def comparativo_periodos( self, grupo_id: int, asignacion_id: int, anio_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def promedios_por_area( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def estudiantes_en_riesgo_academico( self, grupo_id: int, periodo_id: int, nota_minima: float = 60.0, min_asignaturas: int = 1, ) -> list[int]` — ⚠️ sin docstring
- `def ranking_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def tendencia_asistencia( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def distribucion_estados_asistencia( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> dict[str, int]` — ⚠️ sin docstring
- `def consolidado_notas_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def consolidado_asistencia_grupo( self, grupo_id: int, periodo_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def consolidado_anual_grupo( self, grupo_id: int, anio_id: int, ) -> list[dict[str, Any]]` — ⚠️ sin docstring
- `def boletin_datos_periodo( self, estudiante_id: int, grupo_id: int, periodo_id: int, ) -> dict[str, Any]` — ⚠️ sin docstring
- `def boletin_datos_acumulado( self, estudiante_id: int, grupo_id: int, hasta_periodo_id: int, ) -> dict[str, Any]` — ⚠️ sin docstring
- `def boletin_datos_anual( self, estudiante_id: int, grupo_id: int, anio_id: int, ) -> dict[str, Any]` — ⚠️ sin docstring

## `db/repositories/sqlite_estudiante_repo.py`

### SqliteEstudianteRepository(IEstudianteRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_by_id(self, estudiante_id: int) -> Estudiante | None` — ⚠️ sin docstring
- `def get_by_documento( self, numero_documento: str, institucion_id: int | None = None ) -> Estudiante | None` — ⚠️ sin docstring
- `def existe_documento( self, numero_documento: str, institucion_id: int | None = None ) -> bool` — ⚠️ sin docstring
- `def get_resumen(self, estudiante_id: int) -> EstudianteResumenDTO | None` — ⚠️ sin docstring
- `def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]` — ⚠️ sin docstring
- `def listar_resumenes(self, filtro: FiltroEstudiantesDTO) -> list[EstudianteResumenDTO]` — ⚠️ sin docstring
- `def listar_por_grupo( self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None, ) -> list[Estudiante]` — ⚠️ sin docstring
- `def contar_por_grupo( self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None, ) -> int` — ⚠️ sin docstring
- `def guardar(self, estudiante: Estudiante) -> Estudiante` — ⚠️ sin docstring
- `def actualizar(self, estudiante: Estudiante) -> Estudiante` — ⚠️ sin docstring
- `def actualizar_estado_matricula(self, estudiante_id: int, estado: str) -> bool` — ⚠️ sin docstring
- `def asignar_grupo(self, estudiante_id: int, grupo_id: int) -> bool` — ⚠️ sin docstring
- `def registrar_movimiento( self, estudiante_id: int, grupo_origen_id: int | None, grupo_destino_id: int | None, tipo: TipoMovimiento, motivo: str | None = None, usuario_registro_id: int | None = None, ) -> MovimientoEstudiante` — ⚠️ sin docstring
- `def listar_historial( self, estudiante_id: int ) -> list[MovimientoEstudianteInfoDTO]` — ⚠️ sin docstring
- `def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None` — ⚠️ sin docstring
- `def listar_piars(self, estudiante_id: int) -> list[PIAR]` — ⚠️ sin docstring
- `def existe_piar(self, estudiante_id: int, anio_id: int) -> bool` — ⚠️ sin docstring
- `def guardar_piar(self, piar: PIAR) -> PIAR` — ⚠️ sin docstring
- `def actualizar_piar(self, piar: PIAR) -> PIAR` — ⚠️ sin docstring

## `db/repositories/sqlite_evaluacion_repo.py`

### SqliteEvaluacionRepository(IEvaluacionRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def listar_categorias( self, asignacion_id: int, periodo_id: int, ) -> list[Categoria]` — ⚠️ sin docstring
- `def get_categoria(self, cat_id: int) -> Categoria | None` — ⚠️ sin docstring
- `def guardar_categoria(self, categoria: Categoria) -> Categoria` — ⚠️ sin docstring
- `def actualizar_categoria(self, categoria: Categoria) -> Categoria` — ⚠️ sin docstring
- `def eliminar_categoria(self, cat_id: int) -> None` — ⚠️ sin docstring
- `def suma_pesos_otras( self, asignacion_id: int, periodo_id: int, excluir_cat_id: int | None = None, ) -> float` — ⚠️ sin docstring
- `def listar_actividades( self, asignacion_id: int, periodo_id: int, ) -> list[Actividad]` — ⚠️ sin docstring
- `def listar_actividades_por_categoria(self, cat_id: int) -> list[Actividad]` — ⚠️ sin docstring
- `def listar_actividades_publicadas( self, asignacion_id: int, periodo_id: int, hasta_fecha: date | None = None, ) -> list[Actividad]` — ⚠️ sin docstring
- `def get_actividad(self, act_id: int) -> Actividad | None` — ⚠️ sin docstring
- `def guardar_actividad(self, actividad: Actividad) -> Actividad` — ⚠️ sin docstring
- `def actualizar_actividad(self, actividad: Actividad) -> Actividad` — ⚠️ sin docstring
- `def actualizar_estado_actividad( self, act_id: int, estado: EstadoActividad, ) -> bool` — ⚠️ sin docstring
- `def eliminar_actividad(self, act_id: int) -> None` — ⚠️ sin docstring
- `def listar_notas_por_estudiante( self, estudiante_id: int, asignacion_id: int, periodo_id: int, ) -> list[Nota]` — ⚠️ sin docstring
- `def listar_notas_por_actividad(self, actividad_id: int) -> list[Nota]` — ⚠️ sin docstring
- `def get_nota(self, estudiante_id: int, actividad_id: int) -> Nota | None` — ⚠️ sin docstring
- `def guardar_nota(self, nota: Nota) -> Nota` — ⚠️ sin docstring
- `def guardar_notas_masivas(self, notas: list[Nota]) -> int` — ⚠️ sin docstring
- `def eliminar_nota(self, estudiante_id: int, actividad_id: int) -> bool` — ⚠️ sin docstring
- `def get_puntos_extra( self, estudiante_id: int, asignacion_id: int, periodo_id: int, tipo: TipoPuntosExtra | None = None, ) -> PuntosExtra | None` — ⚠️ sin docstring
- `def listar_puntos_extra( self, asignacion_id: int, periodo_id: int, ) -> list[PuntosExtra]` — ⚠️ sin docstring
- `def guardar_puntos_extra(self, pe: PuntosExtra) -> PuntosExtra` — ⚠️ sin docstring
- `def listar_resultados_grupo( self, grupo_id: int, asignacion_id: int, periodo_id: int, ) -> list[ResultadoEstudianteDTO]` — ⚠️ sin docstring

## `db/repositories/sqlite_habilitacion_repo.py`

### SqliteHabilitacionRepository(IHabilitacionRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_habilitacion(self, habilitacion_id: int) -> Habilitacion | None` — ⚠️ sin docstring
- `def listar_habilitaciones( self, filtro: FiltroHabilitacionesDTO, ) -> list[Habilitacion]` — ⚠️ sin docstring
- `def listar_por_estudiante( self, estudiante_id: int, periodo_id: int | None = None, tipo: TipoHabilitacion | None = None, ) -> list[Habilitacion]` — ⚠️ sin docstring
- `def existe_habilitacion( self, estudiante_id: int, asignacion_id: int, tipo: TipoHabilitacion, periodo_id: int | None = None, ) -> bool` — ⚠️ sin docstring
- `def guardar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion` — ⚠️ sin docstring
- `def actualizar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion` — ⚠️ sin docstring
- `def actualizar_estado_habilitacion( self, habilitacion_id: int, estado: EstadoHabilitacion, ) -> bool` — ⚠️ sin docstring
- `def get_plan(self, plan_id: int) -> PlanMejoramiento | None` — ⚠️ sin docstring
- `def listar_planes_por_estudiante( self, estudiante_id: int, asignacion_id: int | None = None, estado: EstadoPlanMejoramiento | None = None, ) -> list[PlanMejoramiento]` — ⚠️ sin docstring
- `def listar_planes_por_seguimiento( self, fecha_limite: date, solo_activos: bool = True, ) -> list[PlanMejoramiento]` — ⚠️ sin docstring
- `def guardar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento` — ⚠️ sin docstring
- `def actualizar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento` — ⚠️ sin docstring

## `db/repositories/sqlite_infraestructura_repo.py`

### SqliteInfraestructuraRepository(IInfraestructuraRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_escenario(self, escenario_id: int) -> EscenarioHorario | None` — ⚠️ sin docstring
- `def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]` — ⚠️ sin docstring
- `def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None` — ⚠️ sin docstring
- `def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` — ⚠️ sin docstring
- `def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario` — ⚠️ sin docstring
- `def activar_escenario(self, escenario_id: int) -> None` — ⚠️ sin docstring
- `def eliminar_escenario(self, escenario_id: int) -> bool` — ⚠️ sin docstring
- `def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario` — ⚠️ sin docstring
- `def crear_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja` — ⚠️ sin docstring
- `def get_plantilla_franja(self, plantilla_id: int) -> PlantillaFranja | None` — ⚠️ sin docstring
- `def listar_plantillas_franja( self, institucion_id: int | None = None ) -> list[PlantillaFranja]` — ⚠️ sin docstring
- `def get_plantilla_activa( self, jornada: str, institucion_id: int | None = None ) -> PlantillaFranja | None` — ⚠️ sin docstring
- `def actualizar_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja` — ⚠️ sin docstring
- `def activar_plantilla_franja(self, plantilla_id: int) -> None` — ⚠️ sin docstring
- `def eliminar_plantilla_franja(self, plantilla_id: int) -> bool` — ⚠️ sin docstring
- `def crear_franja(self, f: Franja) -> Franja` — ⚠️ sin docstring
- `def listar_franjas(self, plantilla_id: int) -> list[Franja]` — ⚠️ sin docstring
- `def actualizar_franja(self, f: Franja) -> Franja` — ⚠️ sin docstring
- `def eliminar_franja(self, franja_id: int) -> bool` — ⚠️ sin docstring
- `def reemplazar_franjas(self, plantilla_id: int, franjas: list[Franja]) -> int` — ⚠️ sin docstring
- `def get_area(self, area_id: int) -> AreaConocimiento | None` — ⚠️ sin docstring
- `def listar_areas(self) -> list[AreaConocimiento]` — ⚠️ sin docstring
- `def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento` — ⚠️ sin docstring
- `def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento` — ⚠️ sin docstring
- `def actualizar_color_area(self, area_id: int, color: str | None) -> bool` — ⚠️ sin docstring
- `def eliminar_area(self, area_id: int) -> bool` — ⚠️ sin docstring
- `def get_asignatura(self, asignatura_id: int) -> Asignatura | None` — ⚠️ sin docstring
- `def listar_asignaturas( self, area_id: int | None = None, institucion_id: int | None = None, ) -> list[Asignatura]` — ⚠️ sin docstring
- `def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura` — ⚠️ sin docstring
- `def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura` — ⚠️ sin docstring
- `def eliminar_asignatura(self, asignatura_id: int) -> bool` — ⚠️ sin docstring
- `def get_grupo(self, grupo_id: int) -> Grupo | None` — ⚠️ sin docstring
- `def get_grupo_por_codigo(self, codigo: str) -> Grupo | None` — ⚠️ sin docstring
- `def listar_grupos( self, grado: int | None = None, institucion_id: int | None = None, ) -> list[Grupo]` — ⚠️ sin docstring
- `def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool` — ⚠️ sin docstring
- `def guardar_grupo(self, grupo: Grupo) -> Grupo` — ⚠️ sin docstring
- `def actualizar_grupo(self, grupo: Grupo) -> Grupo` — ⚠️ sin docstring
- `def eliminar_grupo(self, grupo_id: int) -> bool` — ⚠️ sin docstring
- `def get_horario(self, horario_id: int) -> Horario | None` — ⚠️ sin docstring
- `def get_info_horario(self, horario_id: int) -> HorarioInfo | None` — ⚠️ sin docstring
- `def listar_horario_grupo( self, grupo_id: int, periodo_id: int ) -> list[HorarioInfo]` — ⚠️ sin docstring
- `def listar_horario_docente( self, usuario_id: int, periodo_id: int ) -> list[HorarioInfo]` — ⚠️ sin docstring
- `def listar_horario_grupo_escenario( self, grupo_id: int, escenario_id: int ) -> list[HorarioInfo]` — ⚠️ sin docstring
- `def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]` — ⚠️ sin docstring
- `def existe_conflicto_horario( self, usuario_id: int, periodo_id: int, dia_semana: str, hora_inicio: str, hora_fin: str, excluir_horario_id: int | None = None, ) -> bool` — ⚠️ sin docstring
- `def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO` — ⚠️ sin docstring
- `def guardar_horario(self, horario: Horario) -> Horario` — ⚠️ sin docstring
- `def actualizar_horario(self, horario: Horario) -> Horario` — ⚠️ sin docstring
- `def eliminar_horario(self, horario_id: int) -> bool` — ⚠️ sin docstring
- `def existe_cruce( self, escenario_id: int, dia_semana: str, hora_inicio: str, hora_fin: str, *, usuario_id: int | None = None, grupo_id: int | None = None, sala: str | None = None, excluir_horario_id: int | None = None, ) -> bool` — ⚠️ sin docstring
- `def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int` — ⚠️ sin docstring
- `def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int` — ⚠️ sin docstring
- `def crear_bloques_masivo(self, horarios: list) -> int` — ⚠️ sin docstring
- `def eliminar_horarios_por_asignacion(self, asignacion_id: int) -> int` — ⚠️ sin docstring
- `def get_logro(self, logro_id: int) -> Logro | None` — ⚠️ sin docstring
- `def listar_logros(self, asignacion_id: int, periodo_id: int) -> list[Logro]` — ⚠️ sin docstring
- `def guardar_logro(self, logro: Logro) -> Logro` — ⚠️ sin docstring
- `def actualizar_logro(self, logro: Logro) -> Logro` — ⚠️ sin docstring
- `def eliminar_logro(self, logro_id: int) -> bool` — ⚠️ sin docstring
- `def upsert_disponibilidad(self, d: DisponibilidadDocente) -> DisponibilidadDocente` — ⚠️ sin docstring
- `def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]` — ⚠️ sin docstring
- `def es_disponible(self, usuario_id: int, dia: str, franja_orden: int) -> bool` — ⚠️ sin docstring
- `def limpiar_disponibilidad_docente(self, usuario_id: int) -> int` — ⚠️ sin docstring
- `def cargar_disponibilidad_lote(self, usuario_id: int, slots: list[dict]) -> int` — ⚠️ sin docstring
- `def reemplazar_disponibilidad_docente( self, usuario_id: int, slots: list[dict] ) -> int` — Borra + recarga la disponibilidad de un docente en una sola transacción.
- `def crear_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion` — ⚠️ sin docstring
- `def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None` — ⚠️ sin docstring
- `def listar_configs_generacion( self, periodo_id: int | None = None ) -> list[ConfigGeneracion]` — ⚠️ sin docstring
- `def actualizar_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion` — ⚠️ sin docstring
- `def eliminar_config_generacion(self, config_id: int) -> bool` — ⚠️ sin docstring
- `def cambiar_estado_config( self, config_id: int, nuevo_estado: str ) -> ConfigGeneracion` — ⚠️ sin docstring
- `def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion` — ⚠️ sin docstring
- `def listar_salas(self, institucion_id: int | None = None) -> list[Sala]` — ⚠️ sin docstring
- `def get_sala(self, sala_id: int) -> Sala | None` — ⚠️ sin docstring
- `def crear_sala(self, sala: Sala) -> Sala` — ⚠️ sin docstring
- `def actualizar_sala(self, sala: Sala) -> Sala` — ⚠️ sin docstring
- `def eliminar_sala(self, sala_id: int) -> bool` — ⚠️ sin docstring
- `def listar_ventanas_grupo(self) -> list[VentanaGrupo]` — ⚠️ sin docstring
- `def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]` — ⚠️ sin docstring
- `def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]` — ⚠️ sin docstring
- `def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo` — ⚠️ sin docstring
- `def eliminar_ventana_grupo(self, ventana_id: int) -> bool` — ⚠️ sin docstring
- `def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]` — ⚠️ sin docstring
- `def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado` — ⚠️ sin docstring
- `def eliminar_bloque_anclado(self, bloque_id: int) -> bool` — ⚠️ sin docstring
- `def listar_franjas_reunion(self) -> list[FranjaReunion]` — ⚠️ sin docstring
- `def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None` — ⚠️ sin docstring
- `def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion` — ⚠️ sin docstring
- `def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion` — ⚠️ sin docstring
- `def eliminar_franja_reunion(self, franja_id: int) -> bool` — ⚠️ sin docstring
- `def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None` — ⚠️ sin docstring
- `def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente` — ⚠️ sin docstring
- `def listar_limites_docente(self) -> list[LimitesDocente]` — ⚠️ sin docstring
- `def listar_grados(self) -> list[Grado]` — ⚠️ sin docstring
- `def upsert_grado(self, grado: Grado) -> Grado` — ⚠️ sin docstring
- `def eliminar_grado(self, numero: int) -> bool` — ⚠️ sin docstring
- `def listar_plan_estudios(self) -> list[PlanEstudios]` — ⚠️ sin docstring
- `def get_plan_estudios_por_grado(self, grado: int) -> list[PlanEstudios]` — ⚠️ sin docstring
- `def set_horas_plan(self, grado: int, asignatura_id: int, horas: int) -> PlanEstudios` — ⚠️ sin docstring
- `def eliminar_plan_estudios(self, grado: int, asignatura_id: int) -> bool` — ⚠️ sin docstring

## `db/repositories/sqlite_institucion_repo.py`

### SqliteInstitucionRepository(IInstitucionRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_by_id(self, institucion_id: int) -> Institucion | None` — ⚠️ sin docstring
- `def listar(self, solo_activas: bool = False) -> list[Institucion]` — ⚠️ sin docstring
- `def existe_nombre(self, nombre: str) -> bool` — ⚠️ sin docstring
- `def get_por_defecto(self) -> Institucion | None` — ⚠️ sin docstring
- `def guardar(self, institucion: Institucion) -> Institucion` — ⚠️ sin docstring

## `db/repositories/sqlite_nivelacion_repo.py`

### SqliteNivelacionRepository(INivelacionRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def guardar_actividad(self, actividad: ActividadNivelacion) -> ActividadNivelacion` — ⚠️ sin docstring
- `def listar_actividades( self, asignacion_id: int, periodo_id: int, ) -> list[ActividadNivelacion]` — ⚠️ sin docstring
- `def get_actividad(self, actividad_id: int) -> ActividadNivelacion | None` — ⚠️ sin docstring
- `def suma_pesos_actividades( self, asignacion_id: int, periodo_id: int, excluir_id: int | None = None, ) -> float` — ⚠️ sin docstring
- `def guardar_nota(self, nota: NotaNivelacion) -> NotaNivelacion` — ⚠️ sin docstring
- `def actualizar_nota(self, nota: NotaNivelacion) -> NotaNivelacion` — ⚠️ sin docstring
- `def listar_notas_por_actividad( self, actividad_nivelacion_id: int, ) -> list[NotaNivelacion]` — ⚠️ sin docstring
- `def listar_notas_por_asignacion( self, asignacion_id: int, periodo_id: int, ) -> list[NotaNivelacion]` — ⚠️ sin docstring
- `def get_nota( self, actividad_nivelacion_id: int, estudiante_id: int, ) -> NotaNivelacion | None` — ⚠️ sin docstring
- `def guardar_cierre(self, cierre: CierreNivelacion) -> CierreNivelacion` — ⚠️ sin docstring
- `def get_cierre( self, asignacion_id: int, periodo_id: int, ) -> CierreNivelacion | None` — ⚠️ sin docstring

## `db/repositories/sqlite_periodo_repo.py`

### SqlitePeriodoRepository(IPeriodoRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_by_id(self, periodo_id: int) -> Periodo | None` — ⚠️ sin docstring
- `def get_por_numero(self, anio_id: int, numero: int) -> Periodo | None` — ⚠️ sin docstring
- `def get_activo(self, anio_id: int) -> Periodo | None` — ⚠️ sin docstring
- `def listar_por_anio( self, anio_id: int, incluir_cerrados: bool = True ) -> list[Periodo]` — ⚠️ sin docstring
- `def suma_pesos_otros( self, anio_id: int, excluir_periodo_id: int | None = None ) -> float` — ⚠️ sin docstring
- `def guardar(self, periodo: Periodo) -> Periodo` — ⚠️ sin docstring
- `def actualizar(self, periodo: Periodo) -> Periodo` — ⚠️ sin docstring
- `def cerrar(self, periodo_id: int) -> bool` — ⚠️ sin docstring
- `def activar(self, periodo_id: int) -> bool` — ⚠️ sin docstring
- `def desactivar(self, periodo_id: int) -> bool` — ⚠️ sin docstring
- `def get_hito(self, hito_id: int) -> HitoPeriodo | None` — ⚠️ sin docstring
- `def listar_hitos( self, periodo_id: int, tipo: TipoHito | None = None ) -> list[HitoPeriodo]` — ⚠️ sin docstring
- `def listar_hitos_proximos(self, anio_id: int, dias: int = 7) -> list[HitoPeriodo]` — ⚠️ sin docstring
- `def guardar_hito(self, hito: HitoPeriodo) -> HitoPeriodo` — ⚠️ sin docstring
- `def actualizar_hito(self, hito: HitoPeriodo) -> HitoPeriodo` — ⚠️ sin docstring
- `def eliminar_hito(self, hito_id: int) -> bool` — ⚠️ sin docstring

## `db/repositories/sqlite_plan_mejoramiento_repo.py`

### SqlitePlanMejoramientoRepository(IPlanMejoramientoRepository)

- `def guardar_corte(self, corte: CortePlan) -> CortePlan` — ⚠️ sin docstring
- `def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None` — ⚠️ sin docstring
- `def get_corte_by_id(self, corte_id: int) -> CortePlan | None` — ⚠️ sin docstring
- `def guardar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan` — ⚠️ sin docstring
- `def get_nota_corte(self, corte_id: int, estudiante_id: int) -> NotaCortePlan | None` — ⚠️ sin docstring
- `def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]` — ⚠️ sin docstring
- `def actualizar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan` — ⚠️ sin docstring
- `def guardar_actividad(self, actividad: ActividadPlan) -> ActividadPlan` — ⚠️ sin docstring
- `def get_actividad(self, actividad_id: int) -> ActividadPlan | None` — ⚠️ sin docstring
- `def listar_actividades(self, corte_id: int) -> list[ActividadPlan]` — ⚠️ sin docstring
- `def suma_pesos_actividades(self, corte_id: int, excluir_id: int | None = None) -> float` — ⚠️ sin docstring
- `def guardar_nota_actividad(self, nota: NotaActividadPlan) -> NotaActividadPlan` — ⚠️ sin docstring
- `def get_nota_actividad( self, actividad_plan_id: int, estudiante_id: int ) -> NotaActividadPlan | None` — ⚠️ sin docstring
- `def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]` — ⚠️ sin docstring
- `def listar_notas_por_corte_estudiante( self, corte_id: int, estudiante_id: int ) -> list[NotaActividadPlan]` — ⚠️ sin docstring

## `db/repositories/sqlite_siee_repo.py`

### SqliteSIEERepository(ISIEERepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_configuracion(self, anio_id: int) -> ConfiguracionSIEE | None` — ⚠️ sin docstring
- `def guardar_configuracion(self, cfg: ConfiguracionSIEE) -> ConfiguracionSIEE` — ⚠️ sin docstring
- `def listar_categorias_institucionales(self, anio_id: int) -> list[Categoria]` — ⚠️ sin docstring
- `def get_categoria_institucional(self, cat_id: int) -> Categoria | None` — ⚠️ sin docstring
- `def guardar_categoria_institucional(self, cat: Categoria) -> Categoria` — ⚠️ sin docstring
- `def actualizar_categoria_institucional(self, cat: Categoria) -> Categoria` — ⚠️ sin docstring
- `def eliminar_categoria_institucional(self, cat_id: int) -> None` — ⚠️ sin docstring
- `def suma_pesos_institucionales(self, anio_id: int) -> float` — ⚠️ sin docstring

## `db/repositories/sqlite_usuario_repo.py`

### SqliteUsuarioRepository(IUsuarioRepository)

- `def __init__(self, conn: sqlite3.Connection | None = None)` — ⚠️ sin docstring
- `def get_by_id(self, usuario_id: int) -> Usuario | None` — ⚠️ sin docstring
- `def get_by_username(self, username: str) -> Usuario | None` — ⚠️ sin docstring
- `def get_by_email(self, email: str) -> Usuario | None` — ⚠️ sin docstring
- `def existe_usuario(self, username: str) -> bool` — ⚠️ sin docstring
- `def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]` — ⚠️ sin docstring
- `def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]` — ⚠️ sin docstring
- `def listar_docentes_info( self, periodo_id: int | None = None, solo_activos: bool = True, ) -> list[DocenteInfoDTO]` — ⚠️ sin docstring
- `def get_docente_info( self, usuario_id: int, periodo_id: int | None = None, ) -> DocenteInfoDTO | None` — ⚠️ sin docstring
- `def listar_asignaciones_docente( self, usuario_id: int, periodo_id: int | None = None, ) -> list[AsignacionDocenteInfoDTO]` — ⚠️ sin docstring
- `def guardar(self, usuario: Usuario) -> Usuario` — ⚠️ sin docstring
- `def actualizar(self, usuario: Usuario) -> Usuario` — ⚠️ sin docstring
- `def actualizar_carga( self, usuario_id: int, carga_horaria_max: int | None, horas_extra: int ) -> bool` — ⚠️ sin docstring
- `def cambiar_rol(self, usuario_id: int, nuevo_rol: Rol) -> bool` — ⚠️ sin docstring
- `def desactivar(self, usuario_id: int) -> bool` — ⚠️ sin docstring
- `def reactivar(self, usuario_id: int) -> bool` — ⚠️ sin docstring
- `def marcar_debe_cambiar_password(self, usuario_id: int, valor: bool) -> bool` — Marca/limpia el flag de cambio forzado de contraseña (A2).
- `def get_password_hash(self, usuario_id: int) -> str | None` — ⚠️ sin docstring
- `def actualizar_password_hash(self, usuario_id: int, nuevo_hash: str) -> bool` — ⚠️ sin docstring

## `db/schema.py`

### Funciones de módulo

- `def init_db(db_path: Path | None = None) -> bool` — Inicializa el esquema completo de la base de datos.
- `def get_db_stats() -> dict` — Retorna conteo de filas por tabla y tamaño de la BD.

## `db/seed.py`

### SeedResult
> Contiene todos los IDs creados por el seed.

- `def log_resumen(self) -> None` — ⚠️ sin docstring

### Funciones de módulo

- `def seed_base( conn: sqlite3.Connection, anio: int | None = None, hasher: PasswordHasher = _default_hasher, ) -> SeedResult` — Datos mínimos obligatorios. Seguro en producción.
- `def seed_siee( conn: sqlite3.Connection, anio_id: int, modo: str = "mixto_subcategorias", porcentaje_autonomia_docente: float | None = None, categorias_institucionales: list[tuple] | None = None, ) -> None` — Configura el SIEE para un año lectivo ya existente.
- `def seed_dev( conn: sqlite3.Connection, anio: int | None = None, hasher: PasswordHasher = _default_hasher, total_estudiantes: int = 336, seed_random: int | None = None, ) -> SeedResult` — Dataset completo para desarrollo.
- `def seed_test( conn: sqlite3.Connection, anio: int = 2025, hasher: PasswordHasher = _fast_hasher, ) -> SeedResult` — Dataset mínimo y determinista para tests de integración.

## `exporters/boletin_pdf.py`

### Funciones de módulo

- `def generar_boletin_periodo_pdf(datos: dict[str, Any]) -> bytes` — Genera el boletín de periodo formal como PDF.
- `def generar_boletin_acumulado_pdf(datos: dict[str, Any]) -> bytes` — Genera el boletín acumulado de un periodo como PDF.
- `def generar_boletin_anual_pdf(datos: dict[str, Any]) -> bytes` — Genera el boletín anual formal como PDF.

## `exporters/exporter_factory.py`

### Funciones de módulo

- `def crear_exporter() -> IExporterService` — Retorna el mejor exportador disponible según las dependencias instaladas.

## `exporters/null_exporter.py`

### NullExporter(IExporterService)
> Exportador fallback registrado en el container cuando openpyxl o

- `def exportar_excel( self, datos: list[dict], nombre_hoja: str = "Datos", ruta_destino: Path | None = None, ) -> bytes` — ⚠️ sin docstring
- `def exportar_pdf( self, html_content: str, ruta_destino: Path | None = None, ) -> bytes` — ⚠️ sin docstring
- `def exportar_csv( self, datos: list[dict], ruta_destino: Path | None = None, encoding: str = "utf-8-sig", ) -> bytes` — ⚠️ sin docstring

## `exporters/openpyxl_exporter.py`

### OpenpyxlExporter(IExporterService)
> Genera archivos Excel (.xlsx) con formato institucional.

- `def exportar_excel( self, datos: list[dict], nombre_hoja: str = "Datos", ruta_destino: Path | None = None, ) -> bytes` — Crea un workbook Excel con:
- `def exportar_pdf( self, html_content: str, ruta_destino: Path | None = None, ) -> bytes` — ⚠️ sin docstring
- `def exportar_csv( self, datos: list[dict], ruta_destino: Path | None = None, encoding: str = "utf-8-sig", ) -> bytes` — ⚠️ sin docstring

## `exporters/pdf_exporter.py`

### _HTMLTableParser(HTMLParser)
> Parser mínimo que extrae título, cabeceras, filas y metadatos de un HTML tabular simple.

- `def __init__(self) -> None` — ⚠️ sin docstring
- `def handle_starttag(self, tag: str, attrs) -> None` — ⚠️ sin docstring
- `def handle_endtag(self, tag: str) -> None` — ⚠️ sin docstring
- `def handle_data(self, data: str) -> None` — ⚠️ sin docstring

### WeasyPrintExporter(IExporterService)
> Exportador completo: PDF (weasyprint con fallback a reportlab), Excel via openpyxl, CSV nativo.

- `def exportar_pdf( self, html_content: str, ruta_destino: Path | None = None, ) -> bytes` — ⚠️ sin docstring
- `def exportar_excel( self, datos: list[dict], nombre_hoja: str = "Datos", ruta_destino: Path | None = None, ) -> bytes` — ⚠️ sin docstring
- `def exportar_csv( self, datos: list[dict], ruta_destino: Path | None = None, encoding: str = "utf-8-sig", ) -> bytes` — ⚠️ sin docstring

## `notifications/log_notification_service.py`

### LogNotificationService(NullNotificationService)
> Extiende NullNotificationService almacenando cada notificación en memoria.

- `def __init__(self) -> None` — ⚠️ sin docstring
- `def notificar_acudiente(self, acudiente_id: int, asunto: str, cuerpo: str) -> bool` — ⚠️ sin docstring
- `def notificar_docente(self, usuario_id: int, asunto: str, cuerpo: str) -> bool` — ⚠️ sin docstring
- `def notificar_directivos(self, asunto: str, cuerpo: str) -> int` — ⚠️ sin docstring
- `def limpiar(self) -> None` — ⚠️ sin docstring
- `def conteo(self, tipo: str | None = None) -> int` — ⚠️ sin docstring

## `notifications/null_notification_service.py`

### NullNotificationService(INotificationService)
> Implementación placeholder para v2.0.

- `def __init__(self) -> None` — ⚠️ sin docstring
- `def notificar_acudiente(self, acudiente_id: int, asunto: str, cuerpo: str) -> bool` — ⚠️ sin docstring
- `def notificar_docente(self, usuario_id: int, asunto: str, cuerpo: str) -> bool` — ⚠️ sin docstring
- `def notificar_directivos(self, asunto: str, cuerpo: str) -> int` — ⚠️ sin docstring

