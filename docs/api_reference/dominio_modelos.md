# API Reference — Dominio · Modelos

> Generado automáticamente desde `src/domain/models/` por `tools/gen_api_reference.py` (firmas del fuente + primera línea del docstring). Los métodos sin docstring se marcan `⚠️ sin docstring`. **No editar a mano** — re-generar con el script.

**Cobertura de docstrings:** 443/484 métodos (92%).

| Archivo | Con docstring | Total | % |
|---|---:|---:|---:|
| `src/domain/models/acudiente.py` | 21 | 21 | 100% |
| `src/domain/models/alerta.py` | 6 | 14 | 43% ⚠️ |
| `src/domain/models/asignacion.py` | 10 | 10 | 100% |
| `src/domain/models/asistencia.py` | 23 | 23 | 100% |
| `src/domain/models/auditoria.py` | 20 | 20 | 100% |
| `src/domain/models/cierre.py` | 28 | 28 | 100% |
| `src/domain/models/configuracion.py` | 39 | 39 | 100% |
| `src/domain/models/convivencia.py` | 22 | 22 | 100% |
| `src/domain/models/dtos.py` | 2 | 18 | 11% ⚠️ |
| `src/domain/models/estudiante.py` | 24 | 24 | 100% |
| `src/domain/models/evaluacion.py` | 52 | 52 | 100% |
| `src/domain/models/habilitacion.py` | 30 | 30 | 100% |
| `src/domain/models/infraestructura.py` | 77 | 77 | 100% |
| `src/domain/models/institucion.py` | 1 | 7 | 14% ⚠️ |
| `src/domain/models/nivelacion.py` | 16 | 16 | 100% |
| `src/domain/models/periodo.py` | 25 | 25 | 100% |
| `src/domain/models/piar.py` | 5 | 16 | 31% ⚠️ |
| `src/domain/models/plan_mejoramiento.py` | 11 | 11 | 100% |
| `src/domain/models/usuario.py` | 31 | 31 | 100% |

## `acudiente.py`

### TipoDocumentoAcudiente(str, Enum)

_(sin métodos públicos)_

### Parentesco(str, Enum)

_(sin métodos públicos)_

### Acudiente(BaseModel)
> Acudiente o responsable legal de uno o más estudiantes.

- `def validar_documento(cls, v: str) -> str` `@classmethod` — Normaliza el documento a mayúsculas; exige no vacío y solo letras, números y guiones.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre completo; exige entre 3 y 150 caracteres.
- `def limpiar_celular(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el celular quitando espacios y guiones; cadena vacía → None.
- `def validar_email(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el email y valida formato mínimo ('@' con dominio); vacío → None.
- `def limpiar_direccion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la dirección opcional (strip); cadena vacía → None.
- `def esta_activo(self) -> bool` `@property` — True si el acudiente está activo (no dado de baja).
- `def tiene_contacto(self) -> bool` `@property` — True si tiene al menos un medio de contacto.
- `def contacto_display(self) -> str` `@property` — Primer medio de contacto disponible para notificaciones.
- `def documento_display(self) -> str` `@property` — Documento formateado para UI: 'CC 12345678'.
- `def desactivar(self) -> "Acudiente"` — Retorna una copia con activo=False (soft delete); falla si ya está inactivo.
- `def reactivar(self) -> "Acudiente"` — Retorna una copia con activo=True; falla si ya está activo.

### EstudianteAcudiente(BaseModel)
> Vínculo entre un estudiante y un acudiente.

- `def validar_id(cls, v: int) -> int` `@classmethod` — Las FK del vínculo (estudiante, acudiente) deben ser positivas.

### NuevoAcudienteDTO(BaseModel)
> Datos para registrar un acudiente nuevo.

- `def validar_documento(cls, v: str) -> str` `@classmethod` — Normaliza el documento a mayúsculas y exige que no esté vacío.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre completo; exige al menos 3 caracteres.
- `def validar_email(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el email y exige que contenga '@'; vacío → None.
- `def to_acudiente(self) -> Acudiente` — Construye un Acudiente a partir de los datos del DTO.

### ActualizarAcudienteDTO(BaseModel)
> Campos actualizables de un acudiente. Todos opcionales.

- `def validar_nombre(cls, v: str | None) -> str | None` `@classmethod` — Si se actualiza, el nombre debe tener al menos 3 caracteres.
- `def aplicar_a(self, acudiente: Acudiente) -> Acudiente` — Devuelve una copia del acudiente con solo los campos no nulos del DTO aplicados.

### VincularAcudienteDTO(BaseModel)
> Vincula un acudiente existente a un estudiante.

- `def validar_id(cls, v: int) -> int` `@classmethod` — Las FK del vínculo (estudiante, acudiente) deben ser positivas.
- `def to_vinculo(self) -> EstudianteAcudiente` — Construye un EstudianteAcudiente a partir de los datos del DTO.

### AcudienteResumenDTO(BaseModel)
> Vista mínima para mostrar en el perfil del estudiante.

- `def desde_acudiente( cls, acudiente: Acudiente, es_principal: bool = False, ) -> "AcudienteResumenDTO"` `@classmethod` — Construye el resumen desde un Acudiente persistido, marcando si es el principal.

## `alerta.py`

### TipoAlerta(str, Enum)

_(sin métodos públicos)_

### NivelAlerta(str, Enum)

_(sin métodos públicos)_

### ConfiguracionAlerta(BaseModel)
> Define cuándo se genera automáticamente una alerta para un año lectivo.

- `def validar_umbral(cls, v: float) -> float` `@classmethod` — ⚠️ sin docstring
- `def validar_umbral_segun_tipo(self) -> Self` — Para tipos de conteo (faltas, materias, planes), el umbral debe ser
- `def umbral_entero(self) -> int` `@property` — Umbral como entero para tipos de conteo.
- `def notifica_a_alguien(self) -> bool` `@property` — True si al menos un destinatario está habilitado.

### Alerta(BaseModel)
> Alerta generada para un estudiante específico.

- `def coercer_estudiante_id(cls, v)` `@classmethod` — ⚠️ sin docstring
- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — ⚠️ sin docstring
- `def validar_coherencia_resolucion(self) -> Self` — Si la alerta está resuelta, debe tener fecha_resolucion.
- `def esta_pendiente(self) -> bool` `@property` — ⚠️ sin docstring
- `def dias_pendiente(self) -> int | None` `@property` — Días transcurridos desde la generación. None si ya está resuelta.
- `def es_critica(self) -> bool` `@property` — ⚠️ sin docstring
- `def resolver( self, usuario_id: int, observacion: str | None = None, fecha: datetime | None = None, ) -> "Alerta"` — Retorna una nueva instancia de la alerta marcada como resuelta.

### CrearAlertaDTO(BaseModel)
> Datos necesarios para generar una alerta nueva.

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — ⚠️ sin docstring
- `def to_alerta(self) -> Alerta` — ⚠️ sin docstring

### ResolverAlertaDTO(BaseModel)
> Datos para marcar una alerta como resuelta.

- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — ⚠️ sin docstring

### FiltroAlertasDTO(BaseModel)
> Parámetros para listar alertas.

_(sin métodos públicos)_

## `asignacion.py`

### Asignacion(BaseModel)
> Pivot docente-asignatura-grupo-periodo.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK de la asignación (grupo, asignatura, docente, periodo) deben ser positivas.
- `def esta_activa(self) -> bool` `@property` — True si la asignación está activa (acepta nuevos registros).
- `def desactivar(self) -> "Asignacion"` — Retorna una copia con activo=False (soft-delete).
- `def reactivar(self) -> "Asignacion"` — Retorna una copia con activo=True.

### AsignacionInfo(BaseModel)
> Vista enriquecida de una asignación con nombres resueltos por JOIN.

- `def no_vacio(cls, v: str) -> str` `@classmethod` — Normaliza los nombres resueltos por JOIN; ninguno puede quedar vacío.
- `def display_completo(self) -> str` `@property` — Representación larga para encabezados de planillas e informes:
- `def display_corto(self) -> str` `@property` — Representación corta para selectores y chips de UI:
- `def display_docente_materia(self) -> str` `@property` — Para listas de asignaciones de un docente: 'Matemáticas — 601'

### NuevaAsignacionDTO(BaseModel)
> Datos necesarios para crear una asignación.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del DTO (grupo, asignatura, docente, periodo) deben ser positivas.
- `def to_asignacion(self) -> Asignacion` — Construye una Asignacion a partir de los datos del DTO.

### FiltroAsignacionesDTO(BaseModel)
> Parámetros para listar asignaciones.

_(sin métodos públicos)_

## `asistencia.py`

### EstadoAsistencia(str, Enum)

- `def es_falta(self) -> bool` `@property` — True si el estado es una falta (justificada o injustificada).
- `def afecta_porcentaje(self) -> bool` `@property` — False para estados que no penalizan el porcentaje de asistencia.
- `def descripcion(self) -> str` `@property` — Etiqueta legible del estado (p. ej. 'FI' → 'Falta Injustificada').

### ControlDiario(BaseModel)
> Registro de asistencia de un estudiante a una clase específica.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del registro (estudiante, grupo, asignación, periodo) deben ser positivas.
- `def validar_fecha(cls, v: date | str) -> date` `@classmethod` — Acepta date o string ISO; no se puede registrar asistencia en fecha futura.
- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación opcional (strip); cadena vacía → None.
- `def parsear_hora(cls, v: time | str | None) -> time | None` `@classmethod` — Acepta time, string 'HH:MM' o None y lo convierte a datetime.time.
- `def validar_horas(self) -> Self` — Si ambas están presentes, la hora de entrada debe ser anterior a la de salida.
- `def es_presencia_efectiva(self) -> bool` `@property` — True si el estudiante estuvo presente (incluso con retraso).
- `def requiere_justificacion(self) -> bool` `@property` — True si el estado normalmente requiere una observación.
- `def estado_descripcion(self) -> str` `@property` — Etiqueta legible del estado de asistencia del registro.

### ResumenAsistenciaDTO(BaseModel)
> Resumen de asistencia de un estudiante en un periodo o rango de fechas.

- `def no_negativo(cls, v: int) -> int` `@classmethod` — Ningún conteo del resumen (clases, presentes, faltas…) puede ser negativo.
- `def porcentaje_asistencia(self) -> float` `@property` — Porcentaje considerando solo faltas injustificadas y retrasos
- `def total_faltas(self) -> int` `@property` — Total de faltas (justificadas + injustificadas).
- `def en_riesgo_por_faltas(self, umbral: float = 80.0) -> bool` `@property` — True si el porcentaje de asistencia está por debajo del umbral.
- `def resumen_display(self) -> str` `@property` — 'P:18 FI:2 FJ:1 R:1 E:0 (90.0%)'

### RegistroAsistenciaItemDTO(BaseModel)
> Un ítem dentro de un registro masivo de asistencia.

- `def validar_id(cls, v: int) -> int` `@classmethod` — El estudiante del ítem debe referenciarse con id positivo.

### RegistrarAsistenciaDTO(BaseModel)
> Datos para registrar la asistencia de un único estudiante.

- `def validar_fecha(cls, v: date | str) -> date` `@classmethod` — Acepta date o string ISO; la fecha del registro no puede ser futura.
- `def to_control(self) -> ControlDiario` — Construye un ControlDiario a partir de los datos del DTO.

### RegistrarAsistenciaMasivaDTO(BaseModel)
> Registra la asistencia de todos los estudiantes de un grupo

- `def validar_fecha(cls, v: date | str) -> date` `@classmethod` — Acepta date o string ISO; la fecha del registro masivo no puede ser futura.
- `def validar_registros(cls, v: list) -> list` `@classmethod` — La lista de registros del grupo no puede estar vacía.
- `def total_estudiantes(self) -> int` `@property` — Cantidad de estudiantes incluidos en el registro masivo.
- `def to_controles( self, uniforme_default: bool = True, materiales_default: bool = True, ) -> list[ControlDiario]` — Construye la lista de ControlDiario para persistir.

### FiltroAsistenciaDTO(BaseModel)
> Parámetros para consultar registros de asistencia.

_(sin métodos públicos)_

## `auditoria.py`

### TipoEventoSesion(str, Enum)

_(sin métodos públicos)_

### AccionCambio(str, Enum)

_(sin métodos públicos)_

### EventoSesion(BaseModel)
> Registro de un evento de autenticación o acceso.

- `def validar_usuario(cls, v: str) -> str` `@classmethod` — Normaliza el username del evento y exige que no esté vacío.
- `def limpiar_detalles(cls, v: str | None) -> str | None` `@classmethod` — Normaliza los detalles opcionales (strip); cadena vacía → None.
- `def limpiar_ip(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la IP opcional (strip); cadena vacía → None.
- `def es_exitoso(self) -> bool` `@property` — True si el evento es un login exitoso.
- `def es_fallido(self) -> bool` `@property` — True si el evento es un login fallido.
- `def es_acceso_denegado(self) -> bool` `@property` — True si el evento es un acceso denegado.
- `def fecha_display(self) -> str` `@property` — Fecha y hora del evento formateada 'YYYY-MM-DD HH:MM:SS'.

### RegistroCambio(BaseModel)
> Registro de una operación CRUD sobre datos del sistema.

- `def validar_tabla(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la tabla auditada; exige no vacío y ≤100 caracteres.
- `def validar_json(cls, v: str | dict | None) -> str | None` `@classmethod` — Acepta dict (lo serializa) o JSON string (lo valida).
- `def anterior_como_dict(self) -> dict | None` `@property` — Deserializa valor_anterior como dict.
- `def nuevo_como_dict(self) -> dict | None` `@property` — Deserializa valor_nuevo como dict.
- `def es_creacion(self) -> bool` `@property` — True si el cambio corresponde a una operación CREATE.
- `def es_eliminacion(self) -> bool` `@property` — True si el cambio corresponde a una operación DELETE.
- `def timestamp_display(self) -> str` `@property` — Marca de tiempo del cambio formateada 'YYYY-MM-DD HH:MM:SS'.
- `def para_creacion( cls, tabla: str, datos_nuevos: dict, registro_id: int | None = None, usuario_id: int | None = None, ) -> "RegistroCambio"` `@classmethod` — Construye un registro de creación (sin valor anterior).
- `def para_actualizacion( cls, tabla: str, datos_anteriores: dict, datos_nuevos: dict, registro_id: int | None = None, usuario_id: int | None = None, ) -> "RegistroCambio"` `@classmethod` — Construye un registro de actualización.
- `def para_eliminacion( cls, tabla: str, datos_anteriores: dict, registro_id: int | None = None, usuario_id: int | None = None, ) -> "RegistroCambio"` `@classmethod` — Construye un registro de eliminación (sin valor nuevo).

### CrearEventoSesionDTO(BaseModel)
> Datos para registrar un evento de sesión.

- `def to_evento(self) -> EventoSesion` — Construye un EventoSesion a partir de los datos del DTO.

### CrearRegistroCambioDTO(BaseModel)
> Datos para registrar un cambio de datos.

- `def to_registro(self) -> RegistroCambio` — Construye un RegistroCambio a partir de los datos del DTO.
- `def desde_legacy( cls, tabla: str, accion: str, datos_anteriores: dict | None = None, datos_nuevos: dict | None = None, id_registro: int | None = None, usuario_id: int | None = None, descripcion: str | None = None, # ignorado en v2.0 ) -> "CrearRegistroCambioDTO"` `@classmethod` — Compatibilidad con la firma de `registrar_cambio()` del legacy.

### ResumenUsoDTO(BaseModel)
> Agregación de solo lectura del uso de la plataforma (paso_21).

_(sin métodos públicos)_

### FiltroAuditoriaDTO(BaseModel)
> Parámetros para consultar registros de auditoría.

_(sin métodos públicos)_

## `cierre.py`

### EstadoPromocion(str, Enum)

_(sin métodos públicos)_

### CierrePeriodo(BaseModel)
> Nota definitiva de un estudiante en una asignatura al cierre de un periodo.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del cierre (estudiante, asignación, periodo) deben ser positivas.
- `def validar_nota(cls, v: float) -> float` `@classmethod` — La nota definitiva debe estar en 0-100; se redondea a 2 decimales.
- `def validar_fecha(cls, v: date | str) -> date` `@classmethod` — Acepta date o string ISO; la fecha de cierre no puede ser futura.
- `def aprobo(self, nota_minima: float) -> bool` — Indica si la nota definitiva es aprobatoria.
- `def nota_display(self) -> str` `@property` — Nota formateada con un decimal: '75.5'.

### CierreAnio(BaseModel)
> Nota definitiva anual de un estudiante en una asignatura.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del cierre anual (estudiante, asignación, año) deben ser positivas.
- `def validar_nota(cls, v: float | None) -> float | None` `@classmethod` — Cada nota anual, si está presente, debe estar en 0-100 (redondeada a 2).
- `def validar_fecha(cls, v: date | str) -> date` `@classmethod` — Acepta date o string ISO; la fecha de cierre no puede ser futura.
- `def validar_coherencia_notas(self) -> Self` — Si hay habilitación, nota_definitiva_anual debe ser nota_habilitacion.
- `def tiene_habilitacion(self) -> bool` `@property` — True si el cierre anual incluye una nota de habilitación.
- `def mejoro_con_habilitacion(self) -> bool | None` `@property` — True si la habilitación mejoró la nota del promedio de periodos.
- `def nota_display(self) -> str` `@property` — Nota anual formateada con un decimal: '75.5'.

### PromocionAnual(BaseModel)
> Decisión de promoción de un estudiante al año siguiente.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK de la promoción (estudiante, año) deben ser positivas.
- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación opcional (strip); cadena vacía → None.
- `def validar_fecha(cls, v: date | str | None) -> date | None` `@classmethod` — Acepta date, string ISO o None; la fecha de decisión no puede ser futura.
- `def validar_coherencia_estado(self) -> Self` — Una promoción decidida debe tener fecha_decision.
- `def esta_pendiente(self) -> bool` `@property` — True si la promoción aún no ha sido decidida (estado PENDIENTE).
- `def esta_finalizado(self) -> bool` `@property` — True si la promoción ya fue decidida (cualquier estado distinto de PENDIENTE).
- `def fue_promovido(self) -> bool` `@property` — True si el estudiante pasó de año (PROMOVIDO o CONDICIONAL).
- `def fue_reprobado(self) -> bool` `@property` — True si el estudiante reprobó el año.
- `def es_condicional(self) -> bool` `@property` — True si fue promovido de forma condicional (con materias pendientes).
- `def decidir( self, estado: EstadoPromocion, asignaturas_perdidas: int = 0, observacion: str | None = None, usuario_id: int | None = None, fecha: date | None = None, ) -> "PromocionAnual"` — Registra la decisión de promoción. PENDIENTE → otro estado.

### CrearCierrePeriodoDTO(BaseModel)
> Datos para registrar el cierre de un periodo.

- `def validar_nota(cls, v: float) -> float` `@classmethod` — La nota definitiva del cierre debe estar en 0-100 (redondeada a 2).
- `def to_cierre(self) -> CierrePeriodo` — Construye un CierrePeriodo a partir de los datos del DTO.

### CrearCierreAnioDTO(BaseModel)
> Datos para registrar el cierre anual de una asignatura.

- `def validar_nota(cls, v: float | None) -> float | None` `@classmethod` — Cada nota anual, si está presente, debe estar en 0-100 (redondeada a 2).
- `def to_cierre(self) -> CierreAnio` — Construye un CierreAnio a partir de los datos del DTO.

### DecidirPromocionDTO(BaseModel)
> Datos para registrar la decisión de promoción.

- `def validar_estado(cls, v: EstadoPromocion) -> EstadoPromocion` `@classmethod` — El estado de la decisión no puede ser PENDIENTE (debe ser un resultado final).
- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación opcional (strip); cadena vacía → None.

## `configuracion.py`

### ConfiguracionAnio(BaseModel)
> Configuración del año lectivo activo.

- `def validar_anio(cls, v: int) -> int` `@classmethod` — El año lectivo debe estar en el rango válido 2000..2100.
- `def validar_nota_minima(cls, v: float) -> float` `@classmethod` — La nota mínima de aprobación debe estar en 0-100 (redondeada a 2).
- `def validar_escala(cls, v: float) -> float` `@classmethod` — Los límites de la escala de notas deben estar en 0-100 (redondeados a 2).
- `def validar_nombre_institucion(cls, v: str) -> str` `@classmethod` — Normaliza el nombre institucional; exige no vacío y ≤200 caracteres.
- `def limpiar_campo_opcional(cls, v: str | None) -> str | None` `@classmethod` — Normaliza los campos institucionales opcionales (strip); vacío → None.
- `def validar_fechas(self) -> Self` — Si ambas están definidas, la fecha de inicio no puede ser posterior a la de fin.
- `def validar_escala_coherente(self) -> Self` — El límite inferior de la escala debe ser estrictamente menor que el superior.
- `def anio_display(self) -> str` `@property` — '2025' o '2025 (activo)'
- `def rango_fechas_display(self) -> str` `@property` — '20 enero – 15 diciembre 2025' o 'Fechas no definidas'
- `def duracion_semanas(self) -> int | None` `@property` — Semanas de duración del año escolar.
- `def tiene_informacion_institucional(self) -> bool` `@property` — True si tiene los campos mínimos para generar boletines.
- `def aprobacion_en_rango(self) -> bool` `@property` — True si la nota mínima de aprobación cae dentro de la escala
- `def activar(self) -> "ConfiguracionAnio"` — Retorna una copia del año marcada como activa.
- `def desactivar(self) -> "ConfiguracionAnio"` — Retorna una copia marcada como inactiva.

### NuevaConfiguracionAnioDTO(BaseModel)
> Datos para crear un año lectivo nuevo.

- `def validar_anio(cls, v: int) -> int` `@classmethod` — El año lectivo debe estar en el rango válido 2000..2100.
- `def validar_nota(cls, v: float) -> float` `@classmethod` — La nota mínima de aprobación debe estar en 0-100 (redondeada a 2).
- `def validar_escala(cls, v: float) -> float` `@classmethod` — Los límites de la escala de notas deben estar en 0-100 (redondeados a 2).
- `def validar_fechas(self) -> Self` — Si ambas están definidas, la fecha de inicio no puede ser posterior a la de fin.
- `def to_configuracion(self) -> ConfiguracionAnio` — Construye una ConfiguracionAnio a partir de los datos del DTO.

### ActualizarConfiguracionAnioDTO(BaseModel)
> Campos académicos actualizables. Todos opcionales.

- `def validar_nota(cls, v: float | None) -> float | None` `@classmethod` — Si se actualiza, la nota mínima debe permanecer en 0-100.
- `def aplicar_a(self, config: ConfiguracionAnio) -> ConfiguracionAnio` — Devuelve una copia de la configuración con los campos no nulos del DTO aplicados.

### ActualizarInfoInstitucionalDTO(BaseModel)
> Campos institucionales para boletines e informes.

- `def validar_nombre(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el nombre; si se envía no puede quedar como cadena vacía.
- `def aplicar_a(self, config: ConfiguracionAnio) -> ConfiguracionAnio` — Devuelve una copia de la configuración con los campos institucionales no nulos aplicados.

### InformacionInstitucionalDTO(BaseModel)
> Datos de la institución necesarios para generar boletines.

- `def desde_configuracion( cls, config: ConfiguracionAnio ) -> "InformacionInstitucionalDTO"` `@classmethod` — Construye el DTO desde una ConfiguracionAnio.

### NivelDesempeno(BaseModel)
> Nivel de desempeño del SIE (Sistema Institucional de Evaluación).

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre del nivel; exige no vacío y ≤50 caracteres.
- `def validar_rango(cls, v: float) -> float` `@classmethod` — Los límites del rango del nivel deben estar en 0-100 (redondeados a 2).
- `def validar_orden_rangos(self) -> "NivelDesempeno"` — El rango mínimo del nivel debe ser estrictamente menor que el máximo.
- `def clasifica(self, nota: float) -> bool` — True si la nota cae dentro de este nivel.
- `def amplitud(self) -> float` `@property` — Amplitud del rango en puntos.

### CriterioPromocion(BaseModel)
> Criterios de promoción al grado siguiente para un año lectivo.

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_nota(cls, v: float) -> float` `@classmethod` — Las notas mínimas de promoción deben estar en 0-100 (redondeadas a 2).
- `def puede_ser_promovido(self, asignaturas_perdidas: int) -> bool` — True si la cantidad de materias perdidas no supera el máximo.
- `def puede_habilitar(self, nota: float) -> bool` — True si la nota es suficiente para presentar habilitación.

### NuevoNivelDesempenoDTO(BaseModel)
> Datos para crear un nivel de desempeño.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre y exige que no esté vacío.
- `def validar_rango(cls, v: float) -> float` `@classmethod` — Los límites del rango deben estar en 0-100.
- `def validar_orden_rangos(self) -> "NuevoNivelDesempenoDTO"` — El rango mínimo debe ser estrictamente menor que el máximo.
- `def to_nivel(self) -> NivelDesempeno` — Construye un NivelDesempeno a partir de los datos del DTO.

### ActualizarNivelDesempenoDTO(BaseModel)
> Campos actualizables de un nivel de desempeño.

- `def aplicar_a(self, nivel: NivelDesempeno) -> NivelDesempeno` — Devuelve una copia del nivel con solo los campos no nulos del DTO aplicados.

## `convivencia.py`

### TipoRegistro(str, Enum)

_(sin métodos públicos)_

### ObservacionPeriodo(BaseModel)
> Observación narrativa de un docente sobre un estudiante en un periodo.

- `def validar_texto(cls, v: str) -> str` `@classmethod` — Normaliza el texto de la observación; exige no vacío y ≤2000 caracteres.
- `def hacer_publica(self) -> "ObservacionPeriodo"` — Retorna una copia marcada como pública (aparece en boletín).
- `def hacer_privada(self) -> "ObservacionPeriodo"` — Retorna una copia marcada como privada (solo visible al docente).

### RegistroComportamiento(BaseModel)
> Evento puntual de convivencia registrado por un docente o directivo.

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — Normaliza la descripción del registro; exige no vacío y ≤1000 caracteres.
- `def limpiar_seguimiento(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el seguimiento opcional (strip); cadena vacía → None.
- `def validar_fecha(cls, v: date | str) -> date` `@classmethod` — Acepta date o string ISO; la fecha del registro no puede ser futura.
- `def validar_notificacion(self) -> Self` — No tiene sentido marcar acudiente_notificado=True en un registro
- `def es_negativo(self) -> bool` `@property` — True para registros que implican una situación problemática.
- `def es_positivo(self) -> bool` `@property` — True para registros que reconocen comportamiento positivo.
- `def pendiente_notificacion(self) -> bool` `@property` — True si requiere firma pero el acudiente aún no ha sido notificado.
- `def tiene_seguimiento(self) -> bool` `@property` — True si el registro tiene texto de seguimiento asociado.
- `def registrar_notificacion(self) -> "RegistroComportamiento"` — Retorna una copia marcando que el acudiente fue notificado.
- `def agregar_seguimiento(self, texto: str) -> "RegistroComportamiento"` — Retorna una copia con el texto de seguimiento añadido o reemplazado.

### NotaComportamiento(BaseModel)
> Calificación cuantitativa de convivencia por periodo.

- `def validar_valor(cls, v: float) -> float` `@classmethod` — La nota de comportamiento debe estar en 0-100 (redondeada a 2).
- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación opcional (strip); cadena vacía → None.
- `def aprobado(self, nota_minima: float = 60.0) -> bool` `@property` — Indica si la nota de comportamiento es aprobatoria.

### NuevaObservacionDTO(BaseModel)
> Datos para registrar una observación de periodo.

- `def validar_texto(cls, v: str) -> str` `@classmethod` — Normaliza el texto y exige que no esté vacío.
- `def to_observacion(self, usuario_id: int | None = None) -> ObservacionPeriodo` — Construye una ObservacionPeriodo del DTO, fijando el usuario autor.

### NuevoRegistroComportamientoDTO(BaseModel)
> Datos para crear un registro de comportamiento.

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — Normaliza la descripción y exige que no esté vacía.
- `def to_registro(self, usuario_id: int | None = None) -> RegistroComportamiento` — Construye un RegistroComportamiento del DTO, fijando el usuario que lo registra.

### NuevaNotaComportamientoDTO(BaseModel)
> Datos para registrar la nota de comportamiento de un periodo.

- `def validar_valor(cls, v: float) -> float` `@classmethod` — El valor de la nota de comportamiento debe estar en 0-100 (redondeado a 2).
- `def to_nota(self, usuario_id: int | None = None) -> NotaComportamiento` — Construye una NotaComportamiento del DTO, fijando el usuario autor.

### FiltroConvivenciaDTO(BaseModel)
> Parámetros para consultar registros de comportamiento.

_(sin métodos públicos)_

## `dtos.py`

### FormatoInforme(str, Enum)

_(sin métodos públicos)_

### ContextoAcademicoDTO(BaseModel)
> Captura el contexto de trabajo activo en la sesión: usuario, periodo,

- `def validar_id_requerido(cls, v: int) -> int` `@classmethod` — ⚠️ sin docstring
- `def tiene_grupo(self) -> bool` `@property` — ⚠️ sin docstring
- `def tiene_asignacion(self) -> bool` `@property` — ⚠️ sin docstring
- `def contexto_completo(self) -> bool` `@property` — True si tiene todos los selectores necesarios para notas y asistencia.

### InformeNotasDTO(BaseModel)
> Parámetros para generar un informe de calificaciones.

- `def validar_id(cls, v: int) -> int` `@classmethod` — ⚠️ sin docstring
- `def validar_rango_fechas(cls, v: date, info) -> date` `@classmethod` — ⚠️ sin docstring

### InformeAsistenciaDTO(BaseModel)
> Parámetros para generar un informe de asistencia.

- `def validar_id(cls, v: int) -> int` `@classmethod` — ⚠️ sin docstring
- `def validar_rango_fechas(cls, v: date, info) -> date` `@classmethod` — ⚠️ sin docstring

### DashboardMetricsDTO(BaseModel)
> Métricas agregadas para el panel principal.

- `def validar_porcentaje(cls, v: float) -> float` `@classmethod` — ⚠️ sin docstring
- `def validar_no_negativo(cls, v: int) -> int` `@classmethod` — ⚠️ sin docstring
- `def pct_en_riesgo(self) -> float` `@property` — Porcentaje de estudiantes en riesgo.

### MatriculaMasivaDTO(BaseModel)
> Entrada para carga masiva de estudiantes desde un archivo Excel/CSV.

- `def validar_filas(cls, v: list[dict]) -> list[dict]` `@classmethod` — ⚠️ sin docstring
- `def total_filas(self) -> int` `@property` — ⚠️ sin docstring

### MatriculaMasivaResultadoDTO(BaseModel)
> Resultado de una operación de carga masiva.

- `def tasa_exito(self) -> float` `@property` — ⚠️ sin docstring
- `def fue_exitosa(self) -> bool` `@property` — ⚠️ sin docstring
- `def agregar_error(self, fila: int, dato: str, motivo: str) -> None` — ⚠️ sin docstring

### RespuestaOperacionDTO(BaseModel)
> Envuelve el resultado de una operación con metadatos de éxito/error.

- `def ok(cls, mensaje: str = "Operación exitosa", datos: dict | None = None) -> "RespuestaOperacionDTO"` `@classmethod` — ⚠️ sin docstring
- `def error(cls, mensaje: str, datos: dict | None = None) -> "RespuestaOperacionDTO"` `@classmethod` — ⚠️ sin docstring

## `estudiante.py`

### TipoDocumento(str, Enum)

_(sin métodos públicos)_

### Genero(str, Enum)

_(sin métodos públicos)_

### EstadoMatricula(str, Enum)

_(sin métodos públicos)_

### TipoMovimiento(str, Enum)
> Tipo de movimiento registrado en historial_estudiantes.

_(sin métodos públicos)_

### Estudiante(BaseModel)
> Entidad de dominio que representa a un estudiante matriculado.

- `def validar_documento(cls, v: str) -> str` `@classmethod` — Normaliza el documento a mayúsculas; exige no vacío y solo letras, números y guiones.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza nombre/apellido a title-case; exige no vacío y ≤100 caracteres.
- `def validar_fecha_nacimiento(cls, v: date | str | None) -> date | None` `@classmethod` — Acepta date o string ISO; rechaza fechas futuras o edades mayores a 25 años.
- `def validar_id_publico(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el id público a mayúsculas (strip); cadena vacía → None.
- `def validar_coherencia_documento_edad(self) -> Self` — Detecta inconsistencias entre tipo de documento y edad.
- `def nombre_completo(self) -> str` `@property` — Nombre completo para mostrar: 'Ana Sofía García Pérez'.
- `def edad(self) -> int | None` `@property` — Edad en años completos. None si no hay fecha de nacimiento.
- `def es_activo(self) -> bool` `@property` — True si el estudiante está matriculado activamente.
- `def puede_recibir_calificaciones(self) -> bool` `@property` — Un estudiante puede recibir calificaciones si está activo o reactivado.
- `def requiere_atencion_diferencial(self) -> bool` `@property` — True si el estudiante tiene PIAR activo.
- `def documento_display(self) -> str` `@property` — Cadena formateada para mostrar en UI: 'TI 1098765432'.
- `def retirar(self, motivo: str | None = None) -> "Estudiante"` — Retorna una nueva instancia con estado RETIRADO.
- `def reactivar(self) -> "Estudiante"` — Retorna una nueva instancia con estado ACTIVO.
- `def asignar_grupo(self, grupo_id: int) -> "Estudiante"` — Retorna una nueva instancia con el grupo actualizado.

### NuevoEstudianteDTO(BaseModel)
> Datos necesarios para matricular un estudiante nuevo.

- `def validar_documento(cls, v: str) -> str` `@classmethod` — Normaliza el documento a mayúsculas y exige que no esté vacío.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza nombre/apellido a title-case; exige no vacío y ≤100 caracteres.
- `def to_estudiante(self) -> Estudiante` — Construye el Estudiante completo desde este DTO.

### ActualizarEstudianteDTO(BaseModel)
> Campos actualizables de un estudiante existente.

- `def validar_nombre(cls, v: str | None) -> str | None` `@classmethod` — Si se actualiza, normaliza a title-case; exige no vacío y ≤100 caracteres.
- `def aplicar_a(self, estudiante: Estudiante) -> Estudiante` — Retorna una copia del estudiante con los campos del DTO aplicados.

### FiltroEstudiantesDTO(BaseModel)
> Parámetros de filtrado para listar estudiantes.

- `def limpiar_busqueda(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el término de búsqueda (strip); cadena vacía → None.

### EstudianteResumenDTO(BaseModel)
> Vista reducida de un estudiante para listados y selects.

- `def desde_estudiante(cls, est: Estudiante) -> "EstudianteResumenDTO"` `@classmethod` — Construye el resumen desde un Estudiante persistido; exige que tenga id.

### MovimientoEstudiante(BaseModel)
> Un registro de la tabla `historial_estudiantes`: un movimiento de un

- `def limpiar_motivo(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el motivo del movimiento (strip); cadena vacía → None.

### MovimientoEstudianteInfoDTO(BaseModel)
> Vista de lectura de un movimiento, con los códigos de grupo legibles

- `def fecha_display(self) -> str` `@property` — Fecha formateada 'YYYY-MM-DD HH:MM' o '—' si no hay fecha.
- `def ruta_display(self) -> str` `@property` — Origen → destino legible: 'A1 → A2', '— → A1', etc.

## `evaluacion.py`

### EstadoActividad(str, Enum)

_(sin métodos públicos)_

### TipoPuntosExtra(str, Enum)

_(sin métodos públicos)_

### ModoSIEE(str, Enum)
> Define cómo se distribuyen las categorías de evaluación en la institución.

_(sin métodos públicos)_

### ConfiguracionSIEE(BaseModel)
> Configuración del Sistema Institucional de Evaluación (SIEE) para un año lectivo.

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_porcentaje(cls, v: float | None) -> float | None` `@classmethod` — Si se define, la autonomía docente debe estar en (0, 1.0] (fracción, no porcentaje).
- `def peso_institucional(self) -> float | None` `@property` — Peso total reservado para categorías institucionales en MIXTO_AUTONOMIA.

### Categoria(BaseModel)
> Categoría de evaluación: agrupa actividades y define su peso

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la categoría; exige no vacío y ≤100 caracteres.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso de la categoría debe estar en (0, 1.0] (escala 0-1, no porcentaje).
- `def validar_id_opcional(cls, v: int | None) -> int | None` `@classmethod` — Cada FK opcional, si está presente, debe ser un id positivo.
- `def peso_porcentaje(self) -> float` `@property` — Peso en porcentaje: 0.40 → 40.0
- `def es_docente(self) -> bool` `@property` — True si la categoría pertenece a un docente (no es institucional).

### Actividad(BaseModel)
> Actividad evaluativa: un taller, examen, proyecto, quiz, etc.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la actividad; exige no vacío y ≤150 caracteres.
- `def validar_valor_maximo(cls, v: float) -> float` `@classmethod` — El valor máximo de la actividad debe ser positivo.
- `def limpiar_descripcion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la descripción opcional (strip); cadena vacía → None.
- `def parsear_fecha(cls, v: date | str | None) -> date | None` `@classmethod` — Acepta un date o string ISO ('YYYY-MM-DD') y lo convierte a date.
- `def validar_id(cls, v: int) -> int` `@classmethod` — La categoría dueña de la actividad debe referenciarse con id positivo.
- `def esta_publicada(self) -> bool` `@property` — True si la actividad está en estado PUBLICADA.
- `def acepta_notas(self) -> bool` `@property` — Alias de esta_publicada. Solo las actividades PUBLICADAS aceptan notas.
- `def publicar(self) -> "Actividad"` — Borrador → Publicada.
- `def cerrar(self) -> "Actividad"` — Publicada → Cerrada.
- `def reabrir(self) -> "Actividad"` — Cerrada → Publicada (permite volver a registrar notas).

### Nota(BaseModel)
> Calificación de un estudiante en una actividad específica.

- `def validar_id(cls, v: int) -> int` `@classmethod` — Las FK de la nota (estudiante y actividad) deben ser positivas.
- `def validar_valor(cls, v: float) -> float` `@classmethod` — La nota debe estar en el rango 0-100; se redondea a 2 decimales.
- `def es_aprobatoria(self, nota_minima: float = 60.0) -> bool` `@property` — True si el valor alcanza la nota mínima aprobatoria (por defecto 60).

### PuntosExtra(BaseModel)
> Puntos adicionales que afectan la nota o el comportamiento.

- `def validar_id(cls, v: int) -> int` `@classmethod` — Las FK (estudiante, asignación, periodo) deben ser positivas.
- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación opcional (strip); cadena vacía → None.
- `def balance(self) -> int` `@property` — Diferencia neta entre puntos positivos y negativos.
- `def tiene_impacto(self) -> bool` `@property` — True si hay al menos un punto positivo o negativo registrado.

### CalculadorNotas
> Lógica de cálculo de notas definitivas y promedios.

- `def calcular_definitiva( notas: "list[Nota] | dict[int, float]", actividades: list[Actividad], categorias: list[Categoria], ) -> float` `@staticmethod` — Calcula la nota definitiva del periodo.
- `def calcular_definitiva_con_corte( notas: "list[Nota] | dict[int, float]", actividades: list[Actividad], categorias: list[Categoria], nota_definitiva_plan: float, categoria_ids_en_corte: "set[int]", ) -> float` `@staticmethod` — Calcula la nota definitiva cuando hay un Plan de Mejoramiento activo.
- `def calcular_promedio_ajustado( notas: "list[Nota] | dict[int, float]", actividades: list[Actividad], categorias: list[Categoria], hasta_fecha: date | None = None, ) -> float` `@staticmethod` — Calcula el promedio ajustado a una fecha dada.
- `def pesos_validos(categorias: list[Categoria]) -> bool` `@staticmethod` — True si la suma de pesos de las categorías es <= 1.0.
- `def peso_total(categorias: list[Categoria]) -> float` `@staticmethod` — Suma de pesos de las categorías, redondeada a 4 decimales.

### NuevaConfiguracionSIEEDTO(BaseModel)
> Datos para crear o reemplazar la configuración SIEE de un año.

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_porcentaje(cls, v: float | None) -> float | None` `@classmethod` — Si se define, la autonomía docente debe estar en (0, 1.0].
- `def to_configuracion_siee(self) -> ConfiguracionSIEE` — Construye una ConfiguracionSIEE a partir de los datos del DTO.

### NuevaCategoriaInstitucionalDTO(BaseModel)
> Datos para crear una categoría institucional en la configuración SIEE.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre; exige no vacío y ≤100 caracteres.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso institucional debe estar en (0, 1.0]; se redondea a 4 decimales.
- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def to_categoria(self) -> Categoria` — Construye la Categoria institucional (es_institucional=True) del DTO.

### NuevaCategoriaDTO(BaseModel)
> Datos para crear una categoría de evaluación de docente.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre y exige que no esté vacío.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso de la categoría debe estar en (0, 1.0]; se redondea a 4 decimales.
- `def to_categoria(self) -> Categoria` — Construye una Categoria de docente a partir de los datos del DTO.

### ActualizarCategoriaDTO(BaseModel)
> Campos actualizables de una categoría.

- `def validar_peso(cls, v: float | None) -> float | None` `@classmethod` — Si se actualiza el peso, debe permanecer en (0, 1.0].
- `def aplicar_a(self, categoria: Categoria) -> Categoria` — Devuelve una copia de la categoría con solo los campos no nulos del DTO aplicados.

### NuevaActividadDTO(BaseModel)
> Datos para crear una actividad evaluativa.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre y exige que no esté vacío.
- `def validar_valor(cls, v: float) -> float` `@classmethod` — El valor máximo de la actividad debe ser positivo.
- `def to_actividad(self) -> Actividad` — Construye una Actividad a partir de los datos del DTO.

### ActualizarActividadDTO(BaseModel)
> Campos actualizables de una actividad.

- `def aplicar_a(self, actividad: Actividad) -> Actividad` — Aplica los campos no nulos a la actividad; rechaza si está CERRADA.

### RegistrarNotaDTO(BaseModel)
> Datos para registrar la nota de un único estudiante.

- `def validar_valor(cls, v: float) -> float` `@classmethod` — La nota debe estar en el rango 0-100; se redondea a 2 decimales.
- `def to_nota(self, usuario_registro_id: int | None = None) -> Nota` — Construye una Nota del DTO, fijando el usuario que la registra si se indica.

### RegistrarNotasMasivasDTO(BaseModel)
> Registra notas para múltiples estudiantes en una misma actividad.

- `def validar_id(cls, v: int) -> int` `@classmethod` — La actividad destino del registro masivo debe tener id positivo.
- `def total_notas(self) -> int` `@property` — Cantidad de notas incluidas en el registro masivo.
- `def to_notas(self, usuario_registro_id: int | None = None) -> "list[Nota]"` — Convierte la lista de RegistrarNotaDTO a entidades Nota listas para persistir.

### ResultadoEstudianteDTO(BaseModel)
> Resumen de notas de un estudiante en una asignación.

_(sin métodos públicos)_

### Funciones de módulo

- `def nivel_desempeno(nota: float) -> str` — Clasifica una nota numérica en un nivel de desempeño académico.

## `habilitacion.py`

### TipoHabilitacion(str, Enum)

_(sin métodos públicos)_

### EstadoHabilitacion(str, Enum)

_(sin métodos públicos)_

### EstadoPlanMejoramiento(str, Enum)

_(sin métodos públicos)_

### Habilitacion(BaseModel)
> Actividad de recuperación programada para un estudiante.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK de la habilitación (estudiante, asignación) deben ser positivas.
- `def validar_nota(cls, v: float | None) -> float | None` `@classmethod` — Cada nota, si está presente, debe estar en 0-100 (redondeada a 2).
- `def limpiar_observacion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación opcional (strip); cadena vacía → None.
- `def validar_coherencia(self) -> Self` — Reglas cruzadas: PERIODO exige periodo_id, ANUAL lo prohíbe, y no hay nota si está PENDIENTE.
- `def esta_pendiente(self) -> bool` `@property` — True si la habilitación está programada pero aún no se presenta.
- `def fue_realizada(self) -> bool` `@property` — True si la habilitación ya se presentó (estado distinto de PENDIENTE).
- `def tiene_resultado_final(self) -> bool` `@property` — True si ya se decidió el resultado (APROBADA o REPROBADA).
- `def mejoro_nota(self) -> bool | None` `@property` — True si la nota de habilitación superó la nota anterior.
- `def registrar_nota( self, nota: float, fecha: date | None = None, usuario_id: int | None = None, observacion: str | None = None, ) -> "Habilitacion"` — Registra la nota obtenida. PENDIENTE → REALIZADA.
- `def aprobar(self) -> "Habilitacion"` — Marca la habilitación como aprobada. REALIZADA → APROBADA.
- `def reprobar(self) -> "Habilitacion"` — Marca la habilitación como reprobada. REALIZADA → REPROBADA.

### PlanMejoramiento(BaseModel)
> Plan de trabajo diseñado para que el estudiante supere sus dificultades

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del plan (estudiante, asignación, periodo) deben ser positivas.
- `def validar_texto_requerido(cls, v: str) -> str` `@classmethod` — Normaliza el texto; exige no vacío y ≤2000 caracteres.
- `def limpiar_observacion_cierre(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la observación de cierre opcional (strip); cadena vacía → None.
- `def validar_coherencia(self) -> Self` — Reglas de fechas y estado: cronología válida, cierre exige observación y un plan ACTIVO no lleva fecha_cierre.
- `def esta_activo(self) -> bool` `@property` — True si el plan sigue en curso (estado ACTIVO).
- `def esta_cerrado(self) -> bool` `@property` — True si el plan ya fue cerrado (CUMPLIDO o INCUMPLIDO).
- `def tiene_seguimiento_programado(self) -> bool` `@property` — True si el plan tiene una fecha de seguimiento fijada.
- `def seguimiento_vencido(self) -> bool` `@property` — True si la fecha de seguimiento ya pasó y el plan aún está activo.
- `def dias_activo(self) -> int` `@property` — Días transcurridos desde el inicio del plan.
- `def programar_seguimiento(self, fecha: date) -> "PlanMejoramiento"` — Retorna una copia con la fecha de seguimiento establecida.
- `def cerrar( self, estado: EstadoPlanMejoramiento, observacion: str, fecha: date | None = None, ) -> "PlanMejoramiento"` — Cierra el plan con el estado y observación indicados.

### NuevaHabilitacionDTO(BaseModel)
> Datos para programar una habilitación.

- `def validar_nota(cls, v: float | None) -> float | None` `@classmethod` — Si se indica nota previa, debe estar en 0-100.
- `def validar_tipo_periodo(self) -> Self` — Coherencia tipo/periodo: PERIODO exige periodo_id y ANUAL lo prohíbe.
- `def to_habilitacion(self, usuario_id: int | None = None) -> Habilitacion` — Construye una Habilitacion del DTO, fijando el usuario que la registra.

### RegistrarNotaHabilitacionDTO(BaseModel)
> Datos para registrar la nota cuando el estudiante presenta la habilitación.

- `def validar_nota(cls, v: float) -> float` `@classmethod` — La nota de la habilitación debe estar en 0-100 (redondeada a 2).

### NuevoPlanMejoramientoDTO(BaseModel)
> Datos para crear un plan de mejoramiento.

- `def validar_texto(cls, v: str) -> str` `@classmethod` — Normaliza el texto y exige que no esté vacío.
- `def to_plan(self, usuario_id: int | None = None) -> PlanMejoramiento` — Construye un PlanMejoramiento del DTO, fijando el usuario responsable.

### CerrarPlanMejoramientoDTO(BaseModel)
> Datos para cerrar un plan de mejoramiento.

- `def validar_estado_cierre(cls, v: EstadoPlanMejoramiento) -> EstadoPlanMejoramiento` `@classmethod` — El estado de cierre debe ser CUMPLIDO o INCUMPLIDO, nunca ACTIVO.
- `def validar_observacion(cls, v: str) -> str` `@classmethod` — Normaliza la observación de cierre; es obligatoria (no vacía).

### FiltroHabilitacionesDTO(BaseModel)
> Parámetros para listar habilitaciones.

_(sin métodos públicos)_

## `infraestructura.py`

### Jornada(str, Enum)

_(sin métodos públicos)_

### DiaSemana(str, Enum)

_(sin métodos públicos)_

### AreaConocimiento(BaseModel)
> Área del currículo colombiano (Ley 115 de 1994, Art. 23).

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre del área (strip) y exige no vacío y ≤120 caracteres.
- `def limpiar_codigo(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el código a mayúsculas sin espacios; cadena vacía → None.
- `def normalizar_color(cls, v: str | None) -> str | None` `@classmethod` — Acepta solo hex válido (#RGB o #RRGGBB). Cualquier otro valor → None (soft).

### Asignatura(BaseModel)
> Asignatura que se dicta en la institución.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la asignatura y exige no vacío y ≤100 caracteres.
- `def limpiar_codigo(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el código a mayúsculas sin espacios; cadena vacía → None.
- `def validar_area_id(cls, v: int | None) -> int | None` `@classmethod` — Si se especifica área, su id debe ser positivo (FK válida).

### Grupo(BaseModel)
> Grupo escolar (curso). Cada grupo tiene un grado, jornada y

- `def validar_codigo(cls, v: str) -> str` `@classmethod` — Normaliza el código del grupo a mayúsculas; exige no vacío y ≤20 caracteres.
- `def limpiar_nombre(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el nombre opcional (strip); cadena vacía → None.
- `def validar_grado(cls, v: int | None) -> int | None` `@classmethod` — Si se indica grado, debe estar en el rango 1..13 del sistema colombiano.
- `def descripcion_completa(self) -> str` `@property` — Descripción larga para encabezados:
- `def descripcion_corta(self) -> str` `@property` — '601' o 'Sexto A' si hay nombre.
- `def esta_lleno(self, matriculados: int) -> bool` — True si el número de matriculados alcanza la capacidad máxima.
- `def cupos_disponibles(self, matriculados: int) -> int` — Cupos libres. 0 si ya está lleno.

### Grado(BaseModel)
> Grado ofrecido por la institución (1–13), con su rango de estudiantes

- `def validar_rango_estudiantes(self) -> "Grado"` — El mínimo de estudiantes no puede superar el máximo del grado.

### EscenarioHorario(BaseModel)
> Escenario de horario para un año lectivo.

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre del escenario y exige que no esté vacío.

### NuevoEscenarioDTO(BaseModel)
> DTO para crear un nuevo escenario de horario.

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre del escenario y exige que no esté vacío.
- `def to_escenario(self) -> EscenarioHorario` — Construye un EscenarioHorario a partir de los datos del DTO.

### Horario(BaseModel)
> Franja horaria de una asignatura para un grupo en un escenario.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del bloque (grupo, asignatura, docente) deben ser positivas.
- `def validar_escenario_id(cls, v: int) -> int` `@classmethod` — El escenario dueño del bloque debe referenciarse con un id positivo.
- `def parsear_hora(cls, v: time | str) -> time` `@classmethod` — Acepta un time o un string 'HH:MM' y lo convierte a datetime.time.
- `def validar_sala(cls, v: str) -> str` `@classmethod` — Normaliza la sala; si queda vacía usa 'Aula' por defecto.
- `def validar_orden_horas(self) -> Self` — Invariante temporal: la hora de inicio debe ser anterior a la de fin.
- `def duracion_minutos(self) -> int` `@property` — Duración de la clase en minutos.
- `def franja_display(self) -> str` `@property` — Representación para mostrar en grillas de horario:

### Logro(BaseModel)
> Logro o competencia evaluado en una asignación durante un periodo.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del logro (asignación y periodo) deben ser positivas.
- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — Normaliza el enunciado del logro; exige no vacío y ≤500 caracteres.

### Franja(BaseModel)
> Una franja horaria dentro de una plantilla (rejilla fija).

- `def validar_plantilla_id(cls, v: int) -> int` `@classmethod` — La plantilla dueña de la franja debe referenciarse con id positivo.
- `def normalizar_hora(cls, v: str) -> str` `@classmethod` — Normaliza la hora 'HH:MM' (strip); no puede quedar vacía.
- `def validar_tipo(cls, v: str) -> str` `@classmethod` — El tipo de franja debe ser uno de TIPOS_FRANJA (lectiva/descanso/almuerzo).
- `def limpiar_etiqueta(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la etiqueta opcional (strip); cadena vacía → None.
- `def validar_orden_horas(self) -> Self` — Invariante temporal: la hora de inicio debe ser anterior a la de fin.
- `def es_lectiva(self) -> bool` `@property` — True si la franja es de tipo lectiva (dictada, no descanso ni almuerzo).

### PlantillaFranja(BaseModel)
> Plantilla (rejilla) de franjas para una jornada. A lo sumo una activa

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la plantilla y exige que no esté vacío.
- `def validar_jornada(cls, v: str) -> str` `@classmethod` — La jornada debe ser una de JORNADAS_VALIDAS (AM/PM/UNICA).
- `def validar_dias(cls, v: list[str]) -> list[str]` `@classmethod` — Acepta lista o CSV de días, normaliza y exige que todos estén en DIAS_VALIDOS y no vacío.

### NuevaPlantillaFranjaDTO(BaseModel)

- `def to_plantilla(self) -> PlantillaFranja` — Construye una PlantillaFranja a partir de los datos del DTO.

### NuevaFranjaDTO(BaseModel)

- `def to_franja(self) -> Franja` — Construye una Franja a partir de los datos del DTO.

### PesosGeneracion(BaseModel)

_(sin métodos públicos)_

### DisponibilidadDocente(BaseModel)

- `def validar_dia(cls, v: str) -> str` `@classmethod` — El día de la disponibilidad debe pertenecer a DIAS_VALIDOS.

### ConfigGeneracion(BaseModel)

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la configuración y exige que no esté vacío.
- `def validar_estado(cls, v: str) -> str` `@classmethod` — El estado debe ser uno de ESTADOS_CONFIG (borrador/generado/aplicado).
- `def puede_transicionar_a(self, nuevo: str) -> bool` — True si el estado destino es alcanzable desde el actual según TRANSICIONES_CONFIG.

### NuevaDisponibilidadDTO(BaseModel)

- `def to_modelo(self) -> DisponibilidadDocente` — Construye una DisponibilidadDocente a partir de los datos del DTO.

### NuevaConfigGeneracionDTO(BaseModel)

- `def to_config(self) -> ConfigGeneracion` — Construye una ConfigGeneracion a partir de los datos del DTO.

### BloqueGeneradoDTO(BaseModel)
> Un bloque colocado por el generador en una franja lectiva concreta.

_(sin métodos públicos)_

### MetricasCalidadDTO(BaseModel)
> Métricas de calidad blanda de una solución del generador (paso_15d).

_(sin métodos públicos)_

### ResultadoGeneracionDTO(BaseModel)
> Resultado de una corrida del generador de horarios v1.

_(sin métodos públicos)_

### VentanaGrupo(BaseModel)
> Restringe a qué franjas puede asignarse un grupo/grado.

- `def validar_exclusividad(self) -> "VentanaGrupo"` — La ventana aplica a grupo_id XOR grado: exige exactamente uno de los dos.

### BloqueAnclado(BaseModel)
> Un bloque pre-colocado que el motor debe respetar.

- `def validar_dia(cls, v: str) -> str` `@classmethod` — El día del bloque anclado debe pertenecer a DIAS_VALIDOS.

### FranjaReunion(BaseModel)
> Franja reservada para reunión de un conjunto de docentes.

- `def validar_dia(cls, v: str) -> str` `@classmethod` — El día de la franja de reunión debe pertenecer a DIAS_VALIDOS.
- `def validar_modo(cls, v: str) -> str` `@classmethod` — El modo de la reunión debe ser 'estricta' o 'preferente'.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la franja de reunión y exige que no esté vacío.

### LimitesDocente(BaseModel)
> Límites de carga diaria por docente (amplía carga_horaria_max en usuario).

- `def validar_rango(self) -> "LimitesDocente"` — El mínimo de horas diarias no puede superar el máximo del docente.

### PlanEstudios(BaseModel)
> Horas semanales de una asignatura para un grado específico.

_(sin métodos públicos)_

### NuevaAreaDTO(BaseModel)

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre y exige que no esté vacío.
- `def to_area(self) -> AreaConocimiento` — Construye un AreaConocimiento a partir de los datos del DTO.

### NuevaAsignaturaDTO(BaseModel)

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre y exige que no esté vacío.
- `def to_asignatura(self) -> Asignatura` — Construye una Asignatura a partir de los datos del DTO.

### NuevoGrupoDTO(BaseModel)

- `def validar_codigo(cls, v: str) -> str` `@classmethod` — Normaliza el código a mayúsculas y exige que no esté vacío.
- `def to_grupo(self) -> Grupo` — Construye un Grupo a partir de los datos del DTO.

### Sala(BaseModel)
> Sala o espacio físico donde se dictan clases.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la sala y exige que no esté vacío.
- `def validar_tipo(cls, v: str) -> str` `@classmethod` — El tipo de sala debe ser uno de aula/laboratorio/computo/ed_fisica/otro.

### NuevaSalaDTO(BaseModel)

- `def to_sala(self) -> Sala` — Construye una Sala a partir de los datos del DTO.

### NuevoHorarioDTO(BaseModel)

- `def parsear_hora(cls, v: time | str) -> time` `@classmethod` — Acepta un time o string 'HH:MM' y lo convierte a datetime.time.
- `def validar_horas(self) -> Self` — Invariante temporal: la hora de inicio debe ser anterior a la de fin.
- `def to_horario(self) -> Horario` — Construye un Horario a partir de los datos del DTO.

### NuevoLogroDTO(BaseModel)

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — Normaliza la descripción y exige que no esté vacía.
- `def to_logro(self) -> Logro` — Construye un Logro a partir de los datos del DTO.

### HorarioInfo(BaseModel)
> Vista enriquecida de un bloque horario con nombres resueltos por JOIN.

- `def no_vacio(cls, v: str) -> str` `@classmethod` — Normaliza los nombres resueltos por JOIN; ninguno puede quedar vacío.
- `def limpiar_periodo_nombre(cls, v: str | None) -> str` `@classmethod` — Normaliza el nombre de periodo; None se representa como cadena vacía.
- `def parsear_hora(cls, v: time | str) -> time` `@classmethod` — Acepta un time o string 'HH:MM' y lo convierte a datetime.time.
- `def franja_display(self) -> str` `@property` — 'Lunes 07:00–07:55'
- `def duracion_minutos(self) -> int` `@property` — Duración del bloque en minutos.
- `def display_completo(self) -> str` `@property` — Descripción completa para encabezados de horario:
- `def display_corto(self) -> str` `@property` — Para chips o tooltips: 'Lunes 07:00–07:55 — Matemáticas'

### HorarioEstadisticasDTO(BaseModel)
> Métricas del horario maestro para el panel de estadísticas.

_(sin métodos públicos)_

### CupoDTO(BaseModel)

- `def disponibles(self) -> int | None` `@property` — Cupos libres (máximas − usadas); None si no hay tope definido.
- `def excedido(self) -> bool` `@property` — True si las usadas superan el máximo; False si no hay tope.

### NuevoPlanEstudiosDTO(BaseModel)

_(sin métodos públicos)_

### FilaReporteDTO(BaseModel)

_(sin métodos públicos)_

### ReporteLoteDTO(BaseModel)

- `def validas(self) -> int` `@property` — Número de filas del lote marcadas como válidas (ok=True).
- `def invalidas(self) -> int` `@property` — Número de filas del lote marcadas como inválidas (ok=False).
- `def todo_ok(self) -> bool` `@property` — True solo si hay filas y todas son válidas.

### ResultadoLoteDTO(BaseModel)

_(sin métodos públicos)_

## `institucion.py`

### Institucion(BaseModel)
> Una institución educativa (tenant) registrada en la plataforma.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — ⚠️ sin docstring
- `def limpiar_opcional(cls, v: str | None) -> str | None` `@classmethod` — ⚠️ sin docstring
- `def nombre_display(self) -> str` `@property` — 'Colegio X' o 'Colegio X (inactiva)'.

### NuevaInstitucionDTO(BaseModel)
> Datos para crear una institución nueva.

- `def validar_nombre(cls, v: str) -> str` `@classmethod` — ⚠️ sin docstring
- `def limpiar_opcional(cls, v: str | None) -> str | None` `@classmethod` — ⚠️ sin docstring
- `def to_institucion(self) -> Institucion` — ⚠️ sin docstring

### InstitucionResumenDTO(BaseModel)
> Vista mínima para selects, filtros y lookups.

- `def desde_institucion(cls, i: Institucion) -> "InstitucionResumenDTO"` `@classmethod` — ⚠️ sin docstring

## `nivelacion.py`

### ActividadNivelacion(BaseModel)
> Columna de la planilla de nivelación.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK de la actividad (asignación, periodo) deben ser positivas.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso de la actividad debe estar en (0, 1.0]; se redondea a 4 decimales.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre de la actividad; exige no vacío y ≤120 caracteres.
- `def limpiar_descripcion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la descripción opcional (strip); cadena vacía → None.

### NotaNivelacion(BaseModel)
> Celda de la planilla de nivelación.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK de la nota (actividad, estudiante, asignación, periodo) deben ser positivas.
- `def validar_valor(cls, v: float | None) -> float | None` `@classmethod` — Si está calificada, la nota debe estar en 0-100 (redondeada a 2).
- `def calificada(self) -> bool` `@property` — True si la nota ya tiene un valor registrado (no está pendiente).

### CierreNivelacion(BaseModel)
> Registro de cierre de nivelación para una asignacion+periodo.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK del cierre (asignación, periodo) deben ser positivas.

### CalculadorNivelacion
> Utilidad estática para cálculos de nivelación.

- `def nota_definitiva( notas: list[NotaNivelacion], actividades: list[ActividadNivelacion], ) -> float | None` `@staticmethod` — Calcula el promedio ponderado de las notas de nivelación.
- `def suma_pesos(actividades: list[ActividadNivelacion]) -> float` `@staticmethod` — Suma de los pesos de las actividades de nivelación (redondeada a 4).
- `def pesos_completos( actividades: list[ActividadNivelacion], tolerancia: float = 0.005, ) -> bool` `@staticmethod` — True si la suma de pesos es 1.0 (con tolerancia de redondeo).

### NuevaActividadNivelacionDTO(BaseModel)
> Datos para crear una actividad de nivelación.

- `def validar_id_positivo(cls, v: int) -> int` `@classmethod` — Las FK (asignación, periodo) deben ser positivas.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso de la actividad debe estar en (0, 1.0]; se redondea a 4 decimales.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre y exige que no esté vacío.
- `def to_actividad(self, usuario_id: int | None = None) -> ActividadNivelacion` — Construye una ActividadNivelacion del DTO, fijando el usuario que la crea.

### CalificarNotaNivelacionDTO(BaseModel)
> Datos para calificar (upsert) una nota de nivelación.

- `def validar_valor(cls, v: float) -> float` `@classmethod` — La nota de nivelación debe estar en 0-100 (redondeada a 2).

## `periodo.py`

### TipoHito(str, Enum)

_(sin métodos públicos)_

### Periodo(BaseModel)
> Periodo académico dentro de un año lectivo.

- `def validar_anio_id(cls, v: int) -> int` `@classmethod` — El año lectivo referenciado (FK) debe ser positivo.
- `def validar_numero(cls, v: int) -> int` `@classmethod` — El número de periodo debe estar en el rango 1..6.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre del periodo; exige no vacío y ≤50 caracteres.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso porcentual del periodo debe estar en (0, 100] (redondeado a 2).
- `def validar_coherencia_fechas(self) -> Self` — Coherencia de fechas y cierre: inicio ≤ fin, y fecha_cierre_real existe si y solo si está cerrado.
- `def esta_abierto(self) -> bool` `@property` — True si el periodo acepta modificaciones de notas y asistencia.
- `def esta_vigente(self) -> bool` `@property` — True si el periodo está activo y no cerrado.
- `def duracion_dias(self) -> int | None` `@property` — Días de duración del periodo. None si faltan fechas.
- `def en_curso(self) -> bool` `@property` — True si la fecha actual está dentro del rango del periodo.
- `def cerrar(self, fecha: datetime | None = None) -> "Periodo"` — Retorna una copia del periodo marcada como cerrada.
- `def activar(self) -> "Periodo"` — Retorna una copia con activo=True.
- `def desactivar(self) -> "Periodo"` — Retorna una copia con activo=False.

### HitoPeriodo(BaseModel)
> Fecha límite o evento importante dentro de un periodo.

- `def validar_periodo_id(cls, v: int) -> int` `@classmethod` — El periodo dueño del hito debe referenciarse con id positivo.
- `def limpiar_descripcion(cls, v: str | None) -> str | None` `@classmethod` — Normaliza la descripción opcional (strip); cadena vacía → None.
- `def esta_vencido(self) -> bool` `@property` — True si la fecha límite ya pasó.
- `def dias_restantes(self) -> int | None` `@property` — Días que faltan para el hito. Negativo si ya venció.

### NuevoPeriodoDTO(BaseModel)
> Datos para crear un periodo nuevo.

- `def validar_numero(cls, v: int) -> int` `@classmethod` — El número de periodo debe estar en el rango 1..6.
- `def validar_peso(cls, v: float) -> float` `@classmethod` — El peso porcentual debe estar en (0, 100] (redondeado a 2).
- `def validar_fechas(self) -> Self` — Si ambas están definidas, fecha_inicio no puede ser posterior a fecha_fin.
- `def to_periodo(self) -> Periodo` — Construye un Periodo a partir de los datos del DTO.

### ActualizarPeriodoDTO(BaseModel)
> Campos actualizables de un periodo. Todos opcionales.

- `def validar_nombre(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el nombre opcional (strip); cadena vacía → None.
- `def aplicar_a(self, periodo: Periodo) -> Periodo` — Aplica los campos no nulos al periodo; rechaza si el periodo está cerrado.

### NuevoHitoPeriodoDTO(BaseModel)
> Datos para registrar un hito dentro de un periodo.

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — Normaliza la descripción del hito; es obligatoria y ≤300 caracteres.
- `def validar_periodo_id(cls, v: int) -> int` `@classmethod` — El periodo dueño del hito debe referenciarse con id positivo.
- `def to_hito(self) -> HitoPeriodo` — Construye un HitoPeriodo a partir de los datos del DTO.

## `piar.py`

### PIAR(BaseModel)
> Plan Individual de Apoyos y Ajustes Razonables de un estudiante.

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — ⚠️ sin docstring
- `def limpiar_campo_opcional(cls, v: str | None) -> str | None` `@classmethod` — ⚠️ sin docstring
- `def validar_fecha_elaboracion(cls, v: date | str) -> date` `@classmethod` — ⚠️ sin docstring
- `def validar_fecha_revision(cls, v: date | str | None) -> date | None` `@classmethod` — ⚠️ sin docstring
- `def validar_orden_fechas(self) -> Self` — ⚠️ sin docstring
- `def tiene_revision_programada(self) -> bool` `@property` — ⚠️ sin docstring
- `def revision_vencida(self) -> bool` `@property` — True si la fecha de revisión ya pasó y no se ha actualizado.
- `def dias_para_revision(self) -> int | None` `@property` — Días que faltan para la revisión programada.
- `def tiene_ajustes_evaluativos(self) -> bool` `@property` — ⚠️ sin docstring
- `def tiene_ajustes_pedagogicos(self) -> bool` `@property` — ⚠️ sin docstring
- `def programar_revision(self, fecha: date) -> "PIAR"` — Retorna una copia con la fecha de revisión actualizada.
- `def actualizar_ajustes( self, ajustes_evaluativos: str | None = None, ajustes_pedagogicos: str | None = None, profesionales_apoyo: str | None = None, ) -> "PIAR"` — Retorna una copia con los ajustes actualizados.

### NuevoPIARDTO(BaseModel)
> Datos para registrar un PIAR nuevo.

- `def validar_descripcion(cls, v: str) -> str` `@classmethod` — ⚠️ sin docstring
- `def to_piar(self, usuario_id: int | None = None) -> PIAR` — ⚠️ sin docstring

### ActualizarPIARDTO(BaseModel)
> Campos actualizables de un PIAR. Todos opcionales.

- `def validar_descripcion(cls, v: str | None) -> str | None` `@classmethod` — ⚠️ sin docstring
- `def aplicar_a(self, piar: PIAR) -> PIAR` — Retorna una copia del PIAR con los campos del DTO aplicados.

## `plan_mejoramiento.py`

### EstadoNotaCorte(str, Enum)

_(sin métodos públicos)_

### CortePlan(BaseModel)
> Registro de un corte de plan de mejoramiento para una asignación en un periodo.

_(sin métodos públicos)_

### NotaCortePlan(BaseModel)
> Nota de corte por estudiante. Todos los estudiantes tienen una.

_(sin métodos públicos)_

### ActividadPlan(BaseModel)
> Actividad de plan de mejoramiento (columna compartida para todos los en-plan).

- `def peso_valido(cls, v: float) -> float` `@classmethod` — El peso de la actividad debe estar en (0, 1.0] (fracción del peso del plan).

### NotaActividadPlan(BaseModel)
> Nota de una actividad del plan por estudiante (celda).

_(sin métodos públicos)_

### EjecutarCorteDTO(BaseModel)
> Datos para ejecutar un corte de plan de mejoramiento.

_(sin métodos públicos)_

### NuevaActividadPlanDTO(BaseModel)
> Datos para crear una actividad de plan de mejoramiento.

- `def peso_valido(cls, v: float) -> float` `@classmethod` — El peso de la actividad debe estar en (0, 1.0].
- `def to_actividad(self, usuario_id: int | None = None) -> ActividadPlan` — Construye una ActividadPlan del DTO, fijando el usuario que la crea.

### CalificarNotaPlanDTO(BaseModel)
> Datos para calificar la nota de una actividad de plan.

- `def valor_valido(cls, v: float) -> float` `@classmethod` — La nota de la actividad de plan debe estar en 0-100.

### CerrarPlanEstudianteDTO(BaseModel)
> Datos para cerrar el plan de un estudiante específico.

_(sin métodos públicos)_

### CalculadorPlan
> Utilidades de cálculo para Plan de Mejoramiento.

- `def nota_al_corte( categorias_con_notas: list[dict], ) -> float` `@staticmethod` — Calcula la contribución parcial al corte.
- `def peso_registrado(categorias_con_notas: list[dict]) -> float` `@staticmethod` — Suma de pesos de categorías que tienen al menos una nota registrada.
- `def nota_umbral(peso_registrado: float, nota_minima: float) -> float` `@staticmethod` — Umbral de aprobación proporcional al peso registrado.
- `def nota_definitiva_aprobado(peso_registrado: float, nota_minima: float) -> float` `@staticmethod` — Nota definitiva del plan si el estudiante aprobó.
- `def suma_pesos_actividades(actividades: list[ActividadPlan]) -> float` `@staticmethod` — Suma de los pesos de todas las actividades del plan.
- `def pesos_completos(actividades: list[ActividadPlan], tolerancia: float = 0.005) -> bool` `@staticmethod` — Verifica que la suma de pesos de actividades sea ~1.0.
- `def nota_plan_estudiante( notas: list[NotaActividadPlan], actividades: list[ActividadPlan], ) -> float | None` `@staticmethod` — Promedio ponderado de las actividades del plan para un estudiante.

## `usuario.py`

### Rol(str, Enum)

_(sin métodos públicos)_

### Usuario(BaseModel)
> Entidad que representa a cualquier usuario del sistema.

- `def validar_usuario(cls, v: str) -> str` `@classmethod` — Normaliza el username a minúsculas; exige sin espacios y entre 3 y 50 caracteres.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre completo; exige entre 3 y 150 caracteres.
- `def validar_email(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el email a minúsculas y valida formato mínimo ('@' con dominio); vacío → None.
- `def limpiar_telefono(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el teléfono opcional (strip); cadena vacía → None.
- `def validar_carga_horaria_max(cls, v: int | None) -> int | None` `@classmethod` — Si se define, la carga horaria máxima no puede ser negativa.
- `def validar_horas_extra(cls, v: int) -> int` `@classmethod` — Las horas extra no pueden ser negativas.
- `def carga_maxima_efectiva(self) -> int | None` `@property` — Tope efectivo = carga_horaria_max + horas_extra.
- `def esta_activo(self) -> bool` `@property` — True si el usuario está activo (no dado de baja por soft delete).
- `def es_docente(self) -> bool` `@property` — True si el rol del usuario es PROFESOR.
- `def es_directivo(self) -> bool` `@property` — True si el rol es directivo (admin, director o coordinador).
- `def puede_gestionar_evaluaciones(self) -> bool` `@property` — Puede registrar notas y asistencia.
- `def nombre_display(self) -> str` `@property` — Nombre para mostrar en la UI: 'Carlos López (c.lopez)'
- `def desactivar(self) -> "Usuario"` — Retorna una copia con activo=False (soft delete).
- `def reactivar(self) -> "Usuario"` — Retorna una copia con activo=True.
- `def registrar_sesion(self, momento: datetime | None = None) -> "Usuario"` — Retorna una copia con ultima_sesion actualizada.

### DocenteInfoDTO(BaseModel)
> Vista estadística de un docente para el grid principal de profesores.

- `def tiene_carga(self) -> bool` `@property` — True si el docente tiene al menos una asignación.
- `def resumen_carga(self) -> str` `@property` — '3 grupos · 5 materias · 18 hrs/sem'

### AsignacionDocenteInfoDTO(BaseModel)
> Detalle de una asignación de un docente específico.

- `def horas_pendientes(self) -> int` `@property` — Horas teóricas sin bloque horario asignado.
- `def horario_completo(self) -> bool` `@property` — True si todas las horas teóricas tienen bloque horario.
- `def display(self) -> str` `@property` — '601 — Matemáticas (P1)'

### NuevoUsuarioDTO(BaseModel)
> Datos para crear un usuario nuevo.

- `def validar_usuario(cls, v: str) -> str` `@classmethod` — Normaliza el username a minúsculas; exige mínimo 3 caracteres y sin espacios.
- `def validar_nombre(cls, v: str) -> str` `@classmethod` — Normaliza el nombre completo; exige al menos 3 caracteres.
- `def validar_email(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el email y valida formato mínimo ('@' con dominio); vacío → None.
- `def to_usuario(self) -> Usuario` — Construye un Usuario del DTO, excluyendo la contraseña (la gestiona auth).

### ActualizarUsuarioDTO(BaseModel)
> Campos actualizables de un usuario. Todos opcionales.

- `def validar_nombre(cls, v: str | None) -> str | None` `@classmethod` — Si se actualiza el nombre, debe tener al menos 3 caracteres.
- `def validar_email(cls, v: str | None) -> str | None` `@classmethod` — Si se actualiza el email, normaliza y exige que contenga '@'; vacío → None.
- `def aplicar_a(self, usuario: Usuario) -> Usuario` — Devuelve una copia del usuario con solo los campos no nulos del DTO aplicados.

### UsuarioResumenDTO(BaseModel)
> Vista mínima para selects, lookups y referencias en otros módulos.

- `def desde_usuario(cls, u: Usuario) -> "UsuarioResumenDTO"` `@classmethod` — Construye el resumen desde un Usuario persistido; exige que tenga id.

### FiltroUsuariosDTO(BaseModel)
> Parámetros para listar usuarios.

- `def limpiar_busqueda(cls, v: str | None) -> str | None` `@classmethod` — Normaliza el término de búsqueda (strip); cadena vacía → None.

### ResumenUsuariosDTO(BaseModel)
> Agregación de solo lectura para el dashboard de plataforma (paso_21).

- `def directores(self) -> int` `@property` — Cantidad de usuarios con rol director.
- `def administradores(self) -> int` `@property` — Cantidad de usuarios con rol admin.

