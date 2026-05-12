# Esquema del Dominio (Modelos)

## Modulo: `acudiente.py`

### TipoDocumentoAcudiente
**Herencia**: str, Enum

### Parentesco
**Herencia**: str, Enum

### Acudiente
**Herencia**: BaseModel

Acudiente o responsable legal de uno o más estudiantes.

En v1.0, los datos del acudiente estaban embebidos en la tabla
`estudiantes` (celular_acudiente, email_acudiente), lo que impedía
que un acudiente tuviera múltiples estudiantes a cargo y que los
acudientes tuvieran acceso al portal.

**Atributos:**
- `id`: int | None
- `tipo_documento`: TipoDocumentoAcudiente
- `numero_documento`: str
- `nombre_completo`: str
- `parentesco`: Parentesco
- `celular`: str | None
- `email`: str | None
- `direccion`: str | None
- `activo`: bool
- `usuario_id`: int | None

**Field Validators:**
- `validar_documento()`
- `validar_nombre()`
- `limpiar_celular()`
- `validar_email()`
- `limpiar_direccion()`

**Propiedades:**
- `esta_activo`
- `tiene_contacto`
- `contacto_display`
- `documento_display`

**Métodos de Dominio:**
- `desactivar()`
- `reactivar()`

### EstudianteAcudiente
**Herencia**: BaseModel

Vínculo entre un estudiante y un acudiente.

es_principal=True indica que este es el acudiente de contacto
principal: aparece en el boletín y recibe notificaciones prioritarias.
El servicio garantiza que solo haya un acudiente principal por estudiante.

**Atributos:**
- `estudiante_id`: int
- `acudiente_id`: int
- `es_principal`: bool

**Field Validators:**
- `validar_id()`

### NuevoAcudienteDTO
**Herencia**: BaseModel

Datos para registrar un acudiente nuevo.

**Atributos:**
- `tipo_documento`: TipoDocumentoAcudiente
- `numero_documento`: str
- `nombre_completo`: str
- `parentesco`: Parentesco
- `celular`: str | None
- `email`: str | None
- `direccion`: str | None

**Field Validators:**
- `validar_documento()`
- `validar_nombre()`
- `validar_email()`

**Métodos de Dominio:**
- `to_acudiente()`

### ActualizarAcudienteDTO
**Herencia**: BaseModel

Campos actualizables de un acudiente. Todos opcionales.

**Atributos:**
- `nombre_completo`: str | None
- `parentesco`: Parentesco | None
- `celular`: str | None
- `email`: str | None
- `direccion`: str | None

**Field Validators:**
- `validar_nombre()`

**Métodos de Dominio:**
- `aplicar_a()`

### VincularAcudienteDTO
**Herencia**: BaseModel

Vincula un acudiente existente a un estudiante.

**Atributos:**
- `estudiante_id`: int
- `acudiente_id`: int
- `es_principal`: bool

**Field Validators:**
- `validar_id()`

**Métodos de Dominio:**
- `to_vinculo()`

### AcudienteResumenDTO
**Herencia**: BaseModel

Vista mínima para mostrar en el perfil del estudiante.

**Atributos:**
- `id`: int
- `nombre_completo`: str
- `parentesco`: Parentesco
- `celular`: str | None
- `email`: str | None
- `es_principal`: bool

**Métodos de Dominio:**
- `desde_acudiente()`

## Modulo: `alerta.py`

### TipoAlerta
**Herencia**: str, Enum

### NivelAlerta
**Herencia**: str, Enum

### ConfiguracionAlerta
**Herencia**: BaseModel

Define cuándo se genera automáticamente una alerta para un año lectivo.

El significado de `umbral` depende del tipo:
  - faltas_injustificadas:     número de faltas antes de generar alerta (ej. 3)
  - promedio_bajo:             nota por debajo de la cual se alerta (ej. 55.0)
  - materias_en_riesgo:        cantidad de materias perdidas (ej. 2)
  - plan_mejoramiento_vencido: días de vencimiento antes de alertar (ej. 1)
  - habilitacion_pendiente:    días antes de la fecha límite (ej. 1)

**Atributos:**
- `id`: int | None
- `anio_id`: int
- `tipo_alerta`: TipoAlerta
- `umbral`: float
- `activa`: bool
- `notificar_docente`: bool
- `notificar_director`: bool
- `notificar_acudiente`: bool

**Field Validators:**
- `validar_umbral()`

**Model Validators:**
- `validar_umbral_segun_tipo()`

**Propiedades:**
- `umbral_entero`
- `notifica_a_alguien`

### Alerta
**Herencia**: BaseModel

Alerta generada para un estudiante específico.

Una vez resuelta, la alerta es inmutable: no puede volver a abrirse
ni resolverse de nuevo.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `tipo_alerta`: TipoAlerta
- `nivel`: NivelAlerta
- `descripcion`: str
- `fecha_generacion`: datetime
- `resuelta`: bool
- `fecha_resolucion`: datetime | None
- `usuario_resolucion_id`: int | None
- `observacion_resolucion`: str | None

**Field Validators:**
- `validar_descripcion()`

**Model Validators:**
- `validar_coherencia_resolucion()`

**Propiedades:**
- `esta_pendiente`
- `dias_pendiente`
- `es_critica`

**Métodos de Dominio:**
- `resolver()`

### CrearAlertaDTO
**Herencia**: BaseModel

Datos necesarios para generar una alerta nueva.

**Atributos:**
- `estudiante_id`: int
- `tipo_alerta`: TipoAlerta
- `nivel`: NivelAlerta
- `descripcion`: str

**Field Validators:**
- `validar_descripcion()`

**Métodos de Dominio:**
- `to_alerta()`

### ResolverAlertaDTO
**Herencia**: BaseModel

Datos para marcar una alerta como resuelta.

**Atributos:**
- `usuario_id`: int
- `observacion`: str | None

**Field Validators:**
- `limpiar_observacion()`

### FiltroAlertasDTO
**Herencia**: BaseModel

Parámetros para listar alertas.

**Atributos:**
- `estudiante_id`: int | None
- `tipo_alerta`: TipoAlerta | None
- `nivel`: NivelAlerta | None
- `solo_pendientes`: bool
- `pagina`: int
- `por_pagina`: int

## Modulo: `asignacion.py`

### Asignacion
**Herencia**: BaseModel

Pivot docente-asignatura-grupo-periodo.

Cada asignación genera su propio conjunto de categorías, actividades
y notas. Una asignación inactiva (activo=False) no acepta nuevos datos
pero mantiene el histórico intacto.

**Atributos:**
- `id`: int | None
- `grupo_id`: int
- `asignatura_id`: int
- `usuario_id`: int
- `periodo_id`: int
- `activo`: bool

**Field Validators:**
- `validar_id_positivo()`

**Propiedades:**
- `esta_activa`

**Métodos de Dominio:**
- `desactivar()`
- `reactivar()`

### AsignacionInfo
**Herencia**: BaseModel

Vista enriquecida de una asignación con nombres resueltos por JOIN.

Este modelo no se persiste: lo construye el repositorio a partir
de una consulta que hace JOIN con grupos, asignaturas y usuarios.
Las páginas nunca deben recibir una Asignacion desnuda y hacer
sus propias queries para obtener los nombres.

Uso típico en un servicio:
    info = asignacion_repo.get_info(asignacion_id)
    # info.display_completo → "601 — Matemáticas | Carlos López (P1)"

**Atributos:**
- `asignacion_id`: int
- `grupo_id`: int
- `grupo_codigo`: str
- `asignatura_id`: int
- `asignatura_nombre`: str
- `usuario_id`: int
- `docente_nombre`: str
- `periodo_id`: int
- `periodo_nombre`: str
- `periodo_numero`: int
- `activo`: bool

**Field Validators:**
- `no_vacio()`

**Propiedades:**
- `display_completo`
- `display_corto`
- `display_docente_materia`

### NuevaAsignacionDTO
**Herencia**: BaseModel

Datos necesarios para crear una asignación.

**Atributos:**
- `grupo_id`: int
- `asignatura_id`: int
- `usuario_id`: int
- `periodo_id`: int

**Field Validators:**
- `validar_id_positivo()`

**Métodos de Dominio:**
- `to_asignacion()`

### FiltroAsignacionesDTO
**Herencia**: BaseModel

Parámetros para listar asignaciones.

**Atributos:**
- `usuario_id`: int | None
- `grupo_id`: int | None
- `asignatura_id`: int | None
- `periodo_id`: int | None
- `solo_activas`: bool
- `pagina`: int
- `por_pagina`: int

## Modulo: `asistencia.py`

### EstadoAsistencia
**Herencia**: str, Enum

**Propiedades:**
- `es_falta`
- `afecta_porcentaje`
- `descripcion`

### ControlDiario
**Herencia**: BaseModel

Registro de asistencia de un estudiante a una clase específica.

El campo `fecha_actualizacion` se actualiza automáticamente cuando
el trigger ON CONFLICT REPLACE recrea el registro. En el modelo,
se inicializa al momento de construcción.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `grupo_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `fecha`: date
- `estado`: EstadoAsistencia
- `hora_entrada`: time | None
- `hora_salida`: time | None
- `uniforme`: bool
- `materiales`: bool
- `observacion`: str | None
- `usuario_registro_id`: int | None
- `fecha_actualizacion`: datetime

**Field Validators:**
- `validar_id_positivo()`
- `validar_fecha()`
- `limpiar_observacion()`
- `parsear_hora()`

**Model Validators:**
- `validar_horas()`

**Propiedades:**
- `es_presencia_efectiva`
- `requiere_justificacion`
- `estado_descripcion`

### ResumenAsistenciaDTO
**Herencia**: BaseModel

Resumen de asistencia de un estudiante en un periodo o rango de fechas.
Calculado por el repositorio con GROUP BY; la página lo muestra directamente.

**Atributos:**
- `estudiante_id`: int
- `total_clases`: int
- `presentes`: int
- `faltas_justificadas`: int
- `faltas_injustificadas`: int
- `retrasos`: int
- `excusas`: int

**Field Validators:**
- `no_negativo()`

**Propiedades:**
- `porcentaje_asistencia`
- `total_faltas`
- `en_riesgo_por_faltas`
- `resumen_display`

### RegistroAsistenciaItemDTO
**Herencia**: BaseModel

Un ítem dentro de un registro masivo de asistencia.
Representa la asistencia de un único estudiante en un registro grupal.

**Atributos:**
- `estudiante_id`: int
- `estado`: EstadoAsistencia
- `observacion`: str | None

**Field Validators:**
- `validar_id()`

### RegistrarAsistenciaDTO
**Herencia**: BaseModel

Datos para registrar la asistencia de un único estudiante.

**Atributos:**
- `estudiante_id`: int
- `grupo_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `fecha`: date
- `estado`: EstadoAsistencia
- `hora_entrada`: time | None
- `hora_salida`: time | None
- `uniforme`: bool
- `materiales`: bool
- `observacion`: str | None
- `usuario_registro_id`: int | None

**Field Validators:**
- `validar_fecha()`

**Métodos de Dominio:**
- `to_control()`

### RegistrarAsistenciaMasivaDTO
**Herencia**: BaseModel

Registra la asistencia de todos los estudiantes de un grupo
en una misma fecha y asignación. Operación atómica — el servicio
crea un ControlDiario por cada item.

**Atributos:**
- `grupo_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `fecha`: date
- `registros`: list[RegistroAsistenciaItemDTO]
- `usuario_registro_id`: int | None

**Field Validators:**
- `validar_fecha()`
- `validar_registros()`

**Propiedades:**
- `total_estudiantes`

**Métodos de Dominio:**
- `to_controles()`

### FiltroAsistenciaDTO
**Herencia**: BaseModel

Parámetros para consultar registros de asistencia.

**Atributos:**
- `estudiante_id`: int | None
- `grupo_id`: int | None
- `asignacion_id`: int | None
- `periodo_id`: int | None
- `estado`: EstadoAsistencia | None
- `fecha_desde`: date | None
- `fecha_hasta`: date | None
- `pagina`: int
- `por_pagina`: int

## Modulo: `auditoria.py`

### TipoEventoSesion
**Herencia**: str, Enum

### AccionCambio
**Herencia**: str, Enum

### EventoSesion
**Herencia**: BaseModel

Registro de un evento de autenticación o acceso.

Inmutable: se crea una vez y no se modifica.
El trigger `tg_actualizar_ultima_sesion` de la BD reacciona
a inserciones con tipo=LOGIN_EXITOSO para actualizar `ultima_sesion`.

**Atributos:**
- `id`: int | None
- `usuario`: str
- `usuario_id`: int | None
- `tipo_evento`: TipoEventoSesion
- `ip_address`: str | None
- `fecha_hora`: datetime
- `detalles`: str | None

**Field Validators:**
- `validar_usuario()`
- `limpiar_detalles()`
- `limpiar_ip()`

**Propiedades:**
- `es_exitoso`
- `es_fallido`
- `es_acceso_denegado`
- `fecha_display`

### RegistroCambio
**Herencia**: BaseModel

Registro de una operación CRUD sobre datos del sistema.

`valor_anterior` y `valor_nuevo` son JSON strings que representan
el estado del registro antes y después del cambio. Pueden ser None
para operaciones CREATE (sin valor anterior) o DELETE (sin valor nuevo).

Reemplaza el `registrar_cambio()` del legacy, que recibía dicts
y los serializaba implícitamente.

**Atributos:**
- `id`: int | None
- `usuario_id`: int | None
- `accion`: AccionCambio
- `tabla`: str
- `registro_id`: int | None
- `valor_anterior`: str | None
- `valor_nuevo`: str | None
- `timestamp`: datetime

**Field Validators:**
- `validar_tabla()`
- `validar_json()`

**Propiedades:**
- `anterior_como_dict`
- `nuevo_como_dict`
- `es_creacion`
- `es_eliminacion`
- `timestamp_display`

**Métodos de Dominio:**
- `para_creacion()`
- `para_actualizacion()`
- `para_eliminacion()`

### CrearEventoSesionDTO
**Herencia**: BaseModel

Datos para registrar un evento de sesión.

**Atributos:**
- `usuario`: str
- `usuario_id`: int | None
- `tipo_evento`: TipoEventoSesion
- `ip_address`: str | None
- `detalles`: str | None

**Métodos de Dominio:**
- `to_evento()`

### CrearRegistroCambioDTO
**Herencia**: BaseModel

Datos para registrar un cambio de datos.

`desde_legacy()` permite migrar llamadas al `registrar_cambio()`
de v1.0 sin reescribir todo el código de servicios de una vez.

**Atributos:**
- `usuario_id`: int | None
- `accion`: AccionCambio
- `tabla`: str
- `registro_id`: int | None
- `valor_anterior`: dict | None
- `valor_nuevo`: dict | None

**Métodos de Dominio:**
- `to_registro()`
- `desde_legacy()`

### FiltroAuditoriaDTO
**Herencia**: BaseModel

Parámetros para consultar registros de auditoría.

**Atributos:**
- `usuario_id`: int | None
- `tabla`: str | None
- `accion`: AccionCambio | None
- `tipo_evento`: TipoEventoSesion | None
- `desde`: datetime | None
- `hasta`: datetime | None
- `pagina`: int
- `por_pagina`: int

## Modulo: `cierre.py`

### EstadoPromocion
**Herencia**: str, Enum

### CierrePeriodo
**Herencia**: BaseModel

Nota definitiva de un estudiante en una asignatura al cierre de un periodo.

Es un registro de libro mayor: una vez creado, representa la calificación
oficial. Si se requiere corrección, el repositorio lo reemplaza usando
ON CONFLICT REPLACE — el modelo no tiene un método de corrección.

nota_definitiva: calculada por el servicio a partir de las categorías
                 y actividades. El modelo solo valida el rango.
desempeno_id:    FK al nivel de desempeño correspondiente (Bajo, Básico…).
                 Lo resuelve el servicio comparando la nota con los rangos
                 configurados en niveles_desempeno.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `nota_definitiva`: float
- `desempeno_id`: int | None
- `logro_id`: int | None
- `fecha_cierre`: date
- `usuario_cierre_id`: int | None

**Field Validators:**
- `validar_id_positivo()`
- `validar_nota()`
- `validar_fecha()`

**Propiedades:**
- `nota_display`

**Métodos de Dominio:**
- `aprobo()`

### CierreAnio
**Herencia**: BaseModel

Nota definitiva anual de un estudiante en una asignatura.

Representa el resultado final después de ponderar los cuatro periodos
y, si aplica, la nota de habilitación.

nota_promedio_periodos: promedio ponderado de los cierres_periodo.
nota_habilitacion:      nota obtenida en la habilitación anual, si existe.
nota_definitiva_anual:  la nota que determina si aprobó:
                          - Si hay habilitación: nota_habilitacion
                          - Si no: nota_promedio_periodos
                        El servicio la calcula; el modelo la valida.
perdio:                 True si nota_definitiva_anual < nota_minima.
                        El servicio lo determina; el modelo lo almacena.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `asignacion_id`: int
- `anio_id`: int
- `nota_promedio_periodos`: float
- `nota_habilitacion`: float | None
- `nota_definitiva_anual`: float
- `perdio`: bool
- `desempeno_id`: int | None
- `fecha_cierre`: date
- `usuario_cierre_id`: int | None

**Field Validators:**
- `validar_id_positivo()`
- `validar_nota()`
- `validar_fecha()`

**Model Validators:**
- `validar_coherencia_notas()`

**Propiedades:**
- `tiene_habilitacion`
- `mejoro_con_habilitacion`
- `nota_display`

### PromocionAnual
**Herencia**: BaseModel

Decisión de promoción de un estudiante al año siguiente.

Máquina de estados:
  PENDIENTE → PROMOVIDO | REPROBADO | CONDICIONAL

CONDICIONAL: el estudiante pasa al año siguiente con materias
pendientes (permitido según criterios_promocion).

Una vez decidida (salida del estado PENDIENTE), la promoción
es inmutable — cambiar una decisión de promoción requiere
intervención administrativa directa en la BD.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `anio_id`: int
- `estado`: EstadoPromocion
- `asignaturas_perdidas`: int
- `observacion`: str | None
- `fecha_decision`: date | None
- `usuario_decision_id`: int | None

**Field Validators:**
- `validar_id_positivo()`
- `limpiar_observacion()`
- `validar_fecha()`

**Model Validators:**
- `validar_coherencia_estado()`

**Propiedades:**
- `esta_pendiente`
- `esta_finalizado`
- `fue_promovido`
- `fue_reprobado`
- `es_condicional`

**Métodos de Dominio:**
- `decidir()`

### CrearCierrePeriodoDTO
**Herencia**: BaseModel

Datos para registrar el cierre de un periodo.

**Atributos:**
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `nota_definitiva`: float
- `desempeno_id`: int | None
- `logro_id`: int | None
- `usuario_cierre_id`: int | None

**Field Validators:**
- `validar_nota()`

**Métodos de Dominio:**
- `to_cierre()`

### CrearCierreAnioDTO
**Herencia**: BaseModel

Datos para registrar el cierre anual de una asignatura.

**Atributos:**
- `estudiante_id`: int
- `asignacion_id`: int
- `anio_id`: int
- `nota_promedio_periodos`: float
- `nota_habilitacion`: float | None
- `nota_definitiva_anual`: float
- `perdio`: bool
- `desempeno_id`: int | None
- `usuario_cierre_id`: int | None

**Field Validators:**
- `validar_nota()`

**Métodos de Dominio:**
- `to_cierre()`

### DecidirPromocionDTO
**Herencia**: BaseModel

Datos para registrar la decisión de promoción.

**Atributos:**
- `estado`: EstadoPromocion
- `asignaturas_perdidas`: int
- `observacion`: str | None
- `usuario_id`: int | None
- `fecha`: date | None

**Field Validators:**
- `validar_estado()`
- `limpiar_observacion()`

## Modulo: `configuracion.py`

### ConfiguracionAnio
**Herencia**: BaseModel

Configuración del año lectivo activo.

Un año puede estar activo (el actual) o inactivo (histórico).
Los módulos de notas y asistencia usan el año activo como referencia
para determinar qué periodos y qué configuraciones están vigentes.

**Atributos:**
- `id`: int | None
- `anio`: int
- `fecha_inicio_clases`: date | None
- `fecha_fin_clases`: date | None
- `nota_minima_aprobacion`: float
- `activo`: bool
- `nombre_institucion`: str
- `dane_code`: str | None
- `rector`: str | None
- `direccion`: str | None
- `municipio`: str | None
- `telefono_institucion`: str | None
- `logo_path`: str | None
- `resolucion_aprobacion`: str | None

**Field Validators:**
- `validar_anio()`
- `validar_nota_minima()`
- `validar_nombre_institucion()`
- `limpiar_campo_opcional()`

**Model Validators:**
- `validar_fechas()`

**Propiedades:**
- `anio_display`
- `rango_fechas_display`
- `duracion_semanas`
- `tiene_informacion_institucional`

**Métodos de Dominio:**
- `activar()`
- `desactivar()`

### NuevaConfiguracionAnioDTO
**Herencia**: BaseModel

Datos para crear un año lectivo nuevo.

**Atributos:**
- `anio`: int
- `fecha_inicio_clases`: date | None
- `fecha_fin_clases`: date | None
- `nota_minima_aprobacion`: float
- `nombre_institucion`: str

**Field Validators:**
- `validar_anio()`
- `validar_nota()`

**Model Validators:**
- `validar_fechas()`

**Métodos de Dominio:**
- `to_configuracion()`

### ActualizarConfiguracionAnioDTO
**Herencia**: BaseModel

Campos académicos actualizables. Todos opcionales.

**Atributos:**
- `anio`: int | None
- `fecha_inicio_clases`: date | None
- `fecha_fin_clases`: date | None
- `nota_minima_aprobacion`: float | None

**Field Validators:**
- `validar_nota()`

**Métodos de Dominio:**
- `aplicar_a()`

### ActualizarInfoInstitucionalDTO
**Herencia**: BaseModel

Campos institucionales para boletines e informes.
Separados de los campos académicos para que directivos
puedan actualizar la información del colegio sin
afectar la configuración de notas.

**Atributos:**
- `nombre_institucion`: str | None
- `dane_code`: str | None
- `rector`: str | None
- `direccion`: str | None
- `municipio`: str | None
- `telefono_institucion`: str | None
- `logo_path`: str | None
- `resolucion_aprobacion`: str | None

**Field Validators:**
- `validar_nombre()`

**Métodos de Dominio:**
- `aplicar_a()`

### InformacionInstitucionalDTO
**Herencia**: BaseModel

Datos de la institución necesarios para generar boletines.
El generador de informes construye este DTO desde ConfiguracionAnio.
Todos los campos son obligatorios para garantizar boletines completos.

**Atributos:**
- `anio`: int
- `nombre_institucion`: str
- `dane_code`: str
- `rector`: str
- `nota_minima_aprobacion`: float
- `direccion`: str | None
- `municipio`: str | None
- `telefono_institucion`: str | None
- `logo_path`: str | None
- `resolucion_aprobacion`: str | None

**Métodos de Dominio:**
- `desde_configuracion()`

### NivelDesempeno
**Herencia**: BaseModel

Nivel de desempeño del SIE (Sistema Institucional de Evaluación).

Cada institución define sus propios nombres y rangos para el año lectivo.
Ejemplo por defecto:
  Bajo     [ 0.0 – 59.9]
  Básico   [60.0 – 69.9]
  Alto     [70.0 – 84.9]
  Superior [85.0 – 100.0]

`orden` controla el orden de presentación en la UI y en boletines.
El atributo `clasifica(nota)` permite resolver el nivel de una nota
sin consultar la BD de nuevo.

**Atributos:**
- `id`: int | None
- `anio_id`: int
- `nombre`: str
- `rango_min`: float
- `rango_max`: float
- `descripcion`: str | None
- `orden`: int

**Field Validators:**
- `validar_anio_id()`
- `validar_nombre()`
- `validar_rango()`

**Model Validators:**
- `validar_orden_rangos()`

**Propiedades:**
- `amplitud`

**Métodos de Dominio:**
- `clasifica()`

### CriterioPromocion
**Herencia**: BaseModel

Criterios de promoción al grado siguiente para un año lectivo.

Define cuántas asignaturas puede perder un estudiante y aun así
ser promovido (condicionalmente o no), y la nota mínima para
presentar habilitación.

**Atributos:**
- `id`: int | None
- `anio_id`: int
- `max_asignaturas_perdidas`: int
- `permite_condicionada`: bool
- `nota_minima_habilitacion`: float
- `nota_minima_anual`: float

**Field Validators:**
- `validar_anio_id()`
- `validar_nota()`

**Métodos de Dominio:**
- `puede_ser_promovido()`
- `puede_habilitar()`

### NuevoNivelDesempenoDTO
**Herencia**: BaseModel

Datos para crear un nivel de desempeño.

**Atributos:**
- `anio_id`: int
- `nombre`: str
- `rango_min`: float
- `rango_max`: float
- `descripcion`: str | None
- `orden`: int

**Field Validators:**
- `validar_nombre()`
- `validar_rango()`

**Model Validators:**
- `validar_orden_rangos()`

**Métodos de Dominio:**
- `to_nivel()`

### ActualizarNivelDesempenoDTO
**Herencia**: BaseModel

Campos actualizables de un nivel de desempeño.

**Atributos:**
- `nombre`: str | None
- `rango_min`: float | None
- `rango_max`: float | None
- `descripcion`: str | None
- `orden`: int | None

**Métodos de Dominio:**
- `aplicar_a()`

## Modulo: `convivencia.py`

### TipoRegistro
**Herencia**: str, Enum

### ObservacionPeriodo
**Herencia**: BaseModel

Observación narrativa de un docente sobre un estudiante en un periodo.

`es_publica=True` indica que el texto aparecerá en el boletín.
`es_publica=False` es para notas internas del docente.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `texto`: str
- `es_publica`: bool
- `fecha_registro`: datetime
- `usuario_id`: int | None

**Field Validators:**
- `validar_texto()`

**Métodos de Dominio:**
- `hacer_publica()`
- `hacer_privada()`

### RegistroComportamiento
**Herencia**: BaseModel

Evento puntual de convivencia registrado por un docente o directivo.

La secuencia típica de un registro negativo:
  1. Se crea con tipo=DIFICULTAD, requiere_firma=True.
  2. Se llama a `registrar_notificacion()` cuando el acudiente es contactado.
  3. Se llama a `agregar_seguimiento(texto)` cuando hay acciones posteriores.

DESCARGO es la respuesta formal del estudiante ante una falta grave.
COMPROMISO es un acuerdo entre el estudiante/acudiente y la institución.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `grupo_id`: int
- `periodo_id`: int
- `fecha`: date
- `tipo`: TipoRegistro
- `descripcion`: str
- `seguimiento`: str | None
- `requiere_firma`: bool
- `acudiente_notificado`: bool
- `usuario_registro_id`: int | None

**Field Validators:**
- `validar_descripcion()`
- `limpiar_seguimiento()`
- `validar_fecha()`

**Model Validators:**
- `validar_notificacion()`

**Propiedades:**
- `es_negativo`
- `es_positivo`
- `pendiente_notificacion`
- `tiene_seguimiento`

**Métodos de Dominio:**
- `registrar_notificacion()`
- `agregar_seguimiento()`

### NotaComportamiento
**Herencia**: BaseModel

Calificación cuantitativa de convivencia por periodo.

No todas las instituciones la usan. Cuando existe, es independiente
de las notas académicas y puede tener su propio nivel de desempeño.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `grupo_id`: int
- `periodo_id`: int
- `valor`: float
- `desempeno_id`: int | None
- `observacion`: str | None
- `usuario_id`: int | None

**Field Validators:**
- `validar_valor()`
- `limpiar_observacion()`

**Propiedades:**
- `aprobado`

### NuevaObservacionDTO
**Herencia**: BaseModel

Datos para registrar una observación de periodo.

**Atributos:**
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `texto`: str
- `es_publica`: bool

**Field Validators:**
- `validar_texto()`

**Métodos de Dominio:**
- `to_observacion()`

### NuevoRegistroComportamientoDTO
**Herencia**: BaseModel

Datos para crear un registro de comportamiento.

**Atributos:**
- `estudiante_id`: int
- `grupo_id`: int
- `periodo_id`: int
- `tipo`: TipoRegistro
- `descripcion`: str
- `requiere_firma`: bool
- `fecha`: date

**Field Validators:**
- `validar_descripcion()`

**Métodos de Dominio:**
- `to_registro()`

### NuevaNotaComportamientoDTO
**Herencia**: BaseModel

Datos para registrar la nota de comportamiento de un periodo.

**Atributos:**
- `estudiante_id`: int
- `grupo_id`: int
- `periodo_id`: int
- `valor`: float
- `observacion`: str | None

**Field Validators:**
- `validar_valor()`

**Métodos de Dominio:**
- `to_nota()`

### FiltroConvivenciaDTO
**Herencia**: BaseModel

Parámetros para consultar registros de comportamiento.

**Atributos:**
- `estudiante_id`: int | None
- `grupo_id`: int | None
- `periodo_id`: int | None
- `tipo`: TipoRegistro | None
- `solo_negativos`: bool
- `pagina`: int
- `por_pagina`: int

## Modulo: `dtos.py`

### FormatoInforme
**Herencia**: str, Enum

### ContextoAcademicoDTO
**Herencia**: BaseModel

Captura el contexto de trabajo activo en la sesión: usuario, periodo,
grupo y asignación seleccionados. Es inmutable — cada cambio en la UI
crea un nuevo DTO.

En v1.0, este contexto vivía en AppState (estado global mutable).
En v2.0, el IContextService construye este DTO y los servicios lo
reciben como parámetro. Esto hace que las operaciones sean
explícitas y testeables sin estado global.

**Atributos:**
- `usuario_id`: int
- `anio_id`: int
- `periodo_id`: int
- `grupo_id`: int | None
- `asignacion_id`: int | None

**Field Validators:**
- `validar_id_requerido()`

**Propiedades:**
- `tiene_grupo`
- `tiene_asignacion`
- `contexto_completo`

### InformeNotasDTO
**Herencia**: BaseModel

Parámetros para generar un informe de calificaciones.
Consumido por InformeService.generar_notas() y por los exportadores.

**Atributos:**
- `grupo_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `fecha_desde`: date
- `fecha_hasta`: date
- `formato`: FormatoInforme
- `incluir_piar`: bool

**Field Validators:**
- `validar_id()`
- `validar_rango_fechas()`

### InformeAsistenciaDTO
**Herencia**: BaseModel

Parámetros para generar un informe de asistencia.

**Atributos:**
- `grupo_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `fecha_desde`: date
- `fecha_hasta`: date
- `formato`: FormatoInforme

**Field Validators:**
- `validar_id()`
- `validar_rango_fechas()`

### DashboardMetricsDTO
**Herencia**: BaseModel

Métricas agregadas para el panel principal.
El DashboardService las calcula con queries GROUP BY;
la página las muestra directamente sin lógica adicional.

**Atributos:**
- `grupo_id`: int
- `total_estudiantes`: int
- `promedio_general`: float
- `porcentaje_asistencia`: float
- `estudiantes_en_riesgo`: int
- `actividades_publicadas`: int
- `alertas_pendientes`: int

**Field Validators:**
- `validar_porcentaje()`
- `validar_no_negativo()`

**Propiedades:**
- `pct_en_riesgo`

### MatriculaMasivaDTO
**Herencia**: BaseModel

Entrada para carga masiva de estudiantes desde un archivo Excel/CSV.
El servicio itera sobre `filas` y crea un Estudiante por cada una.

**Atributos:**
- `grupo_id`: int | None
- `filas`: list[dict]
- `omitir_errores`: bool

**Field Validators:**
- `validar_filas()`

**Propiedades:**
- `total_filas`

### MatriculaMasivaResultadoDTO
**Herencia**: BaseModel

Resultado de una operación de carga masiva.

**Atributos:**
- `total_procesadas`: int
- `exitosas`: int
- `fallidas`: int
- `errores`: list[dict]

**Propiedades:**
- `tasa_exito`
- `fue_exitosa`

**Métodos de Dominio:**
- `agregar_error()`

### RespuestaOperacionDTO
**Herencia**: BaseModel

Envuelve el resultado de una operación con metadatos de éxito/error.
Los servicios la retornan cuando la UI necesita feedback estructurado
más allá de una excepción.

**Atributos:**
- `exito`: bool
- `mensaje`: str
- `datos`: dict | None

**Métodos de Dominio:**
- `ok()`
- `error()`

## Modulo: `estudiante.py`

### TipoDocumento
**Herencia**: str, Enum

### Genero
**Herencia**: str, Enum

### EstadoMatricula
**Herencia**: str, Enum

### Estudiante
**Herencia**: BaseModel

Entidad de dominio que representa a un estudiante matriculado.

Invariantes garantizadas al construir el objeto:
  - numero_documento es alfanumérico, sin espacios.
  - nombre y apellido están normalizados a title-case y no están vacíos.
  - fecha_nacimiento, si existe, no es futura ni implica edad > 25 años.
  - La combinación (tipo_documento=CC, edad<17) genera un ValueError
    porque es probable que sea un error de carga de datos.

Uso típico desde un repositorio:
    row = fetch_one("SELECT * FROM estudiantes WHERE id = ?", (est_id,))
    estudiante = Estudiante(**row)   # Pydantic valida en construcción

Uso típico desde un servicio:
    dto = NuevoEstudianteDTO(
        numero_documento="1098765432",
        nombre="Ana",
        apellido="García",
    )
    estudiante = Estudiante(**dto.model_dump())
    repo.guardar(estudiante)

**Atributos:**
- `id`: int | None
- `id_publico`: str | None
- `tipo_documento`: TipoDocumento
- `numero_documento`: str
- `nombre`: str
- `apellido`: str
- `genero`: Genero | None
- `fecha_nacimiento`: date | None
- `direccion`: str | None
- `grupo_id`: int | None
- `posee_piar`: bool
- `fecha_ingreso`: date
- `estado_matricula`: EstadoMatricula

**Field Validators:**
- `validar_documento()`
- `validar_nombre()`
- `validar_fecha_nacimiento()`
- `validar_id_publico()`

**Model Validators:**
- `validar_coherencia_documento_edad()`

**Propiedades:**
- `nombre_completo`
- `edad`
- `es_activo`
- `puede_recibir_calificaciones`
- `requiere_atencion_diferencial`
- `documento_display`

**Métodos de Dominio:**
- `retirar()`
- `reactivar()`
- `asignar_grupo()`

### NuevoEstudianteDTO
**Herencia**: BaseModel

Datos necesarios para matricular un estudiante nuevo.

Solo incluye los campos que el operador debe proveer.
Los campos opcionales se inicializan con valores por defecto en Estudiante.

**Atributos:**
- `tipo_documento`: TipoDocumento
- `numero_documento`: str
- `nombre`: str
- `apellido`: str
- `genero`: Genero | None
- `fecha_nacimiento`: date | None
- `grupo_id`: int | None
- `posee_piar`: bool
- `direccion`: str | None

**Field Validators:**
- `validar_documento()`
- `validar_nombre()`

**Métodos de Dominio:**
- `to_estudiante()`

### ActualizarEstudianteDTO
**Herencia**: BaseModel

Campos actualizables de un estudiante existente.

Todos son opcionales: solo se actualiza lo que se provee.
El número de documento no es actualizable (es el identificador principal).

**Atributos:**
- `nombre`: str | None
- `apellido`: str | None
- `genero`: Genero | None
- `fecha_nacimiento`: date | None
- `grupo_id`: int | None
- `posee_piar`: bool | None
- `direccion`: str | None
- `estado_matricula`: EstadoMatricula | None

**Field Validators:**
- `validar_nombre()`

**Métodos de Dominio:**
- `aplicar_a()`

### FiltroEstudiantesDTO
**Herencia**: BaseModel

Parámetros de filtrado para listar estudiantes.
Consumido por IEstudianteRepository.listar_filtrado().

**Atributos:**
- `grupo_id`: int | None
- `estado_matricula`: EstadoMatricula | None
- `posee_piar`: bool | None
- `busqueda`: str | None
- `pagina`: int
- `por_pagina`: int

**Field Validators:**
- `limpiar_busqueda()`

### EstudianteResumenDTO
**Herencia**: BaseModel

Vista reducida de un estudiante para listados y selects.
No incluye campos de auditoría ni direcciones.

**Atributos:**
- `id`: int
- `id_publico`: str | None
- `documento_display`: str
- `nombre_completo`: str
- `genero`: Genero | None
- `grupo_id`: int | None
- `estado_matricula`: EstadoMatricula
- `posee_piar`: bool

**Métodos de Dominio:**
- `desde_estudiante()`

## Modulo: `evaluacion.py`

### EstadoActividad
**Herencia**: str, Enum

### TipoPuntosExtra
**Herencia**: str, Enum

### Categoria
**Herencia**: BaseModel

Categoría de evaluación: agrupa actividades y define su peso
en la nota definitiva del periodo.

El peso está en escala 0-1 (no 0-100):
  peso=0.40 → 40% de la nota
Esto es consistente con el schema (peso REAL NOT NULL CHECK(peso > 0 AND peso <= 1)).

La suma de pesos de todas las categorías de una asignación+periodo
debe ser <= 1.0. Esta invariante la verifica el trigger de BD y el
método CalculadorNotas.pesos_validos(). El modelo valida solo el
rango individual (> 0 y <= 1).

**Atributos:**
- `id`: int | None
- `nombre`: str
- `peso`: float
- `asignacion_id`: int
- `periodo_id`: int

**Field Validators:**
- `validar_nombre()`
- `validar_peso()`
- `validar_id()`

**Propiedades:**
- `peso_porcentaje`

### Actividad
**Herencia**: BaseModel

Actividad evaluativa: un taller, examen, proyecto, quiz, etc.
Pertenece a una categoría y tiene notas por estudiante.

Estado:
  borrador  → solo el docente la ve; los estudiantes no
  publicada → visible para los estudiantes; se pueden ingresar notas
  cerrada   → no acepta más notas (el periodo fue cerrado)

**Atributos:**
- `id`: int | None
- `nombre`: str
- `descripcion`: str | None
- `fecha`: date | None
- `valor_maximo`: float
- `estado`: EstadoActividad
- `categoria_id`: int

**Field Validators:**
- `validar_nombre()`
- `validar_valor_maximo()`
- `limpiar_descripcion()`
- `parsear_fecha()`
- `validar_id()`

**Propiedades:**
- `esta_publicada`
- `acepta_notas`

**Métodos de Dominio:**
- `publicar()`
- `cerrar()`

### Nota
**Herencia**: BaseModel

Calificación de un estudiante en una actividad específica.

El valor se almacena en escala 0-100, independientemente del
valor_maximo de la actividad. El docente puede ingresar 7.5/10
y el sistema almacena 75.0.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `actividad_id`: int
- `valor`: float
- `usuario_registro_id`: int | None
- `fecha_registro`: datetime

**Field Validators:**
- `validar_id()`
- `validar_valor()`

**Propiedades:**
- `es_aprobatoria`

### PuntosExtra
**Herencia**: BaseModel

Puntos adicionales que afectan la nota o el comportamiento.

tipo distingue la naturaleza del ajuste:
  comportamental → afecta la nota de convivencia
  participacion  → bonificación por participación en clase
  academico      → ajuste directo sobre la nota académica

El impacto numérico de los puntos sobre la nota definitiva
lo define el servicio según la configuración institucional.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `tipo`: TipoPuntosExtra
- `positivos`: int
- `negativos`: int
- `observacion`: str | None
- `fecha_actualizacion`: datetime

**Field Validators:**
- `validar_id()`
- `limpiar_observacion()`

**Propiedades:**
- `balance`
- `tiene_impacto`

### CalculadorNotas

Lógica de cálculo de notas definitivas y promedios.
Todas sus operaciones son métodos estáticos: no guardan estado.
Reciben colecciones de entidades del dominio y retornan valores.

Responsabilidad:
  - calcular_definitiva: promedio ponderado final (para cierres)
  - calcular_promedio_ajustado: promedio con actividades evaluadas
    hasta una fecha (para seguimiento en tiempo real)
  - pesos_validos / peso_total: validación de configuración

No es responsabilidad de este calculador:
  - Consultar datos de la BD (eso es el repositorio)
  - Determinar si una nota es aprobatoria (eso usa nota_minima
    de configuracion_anio, y lo hace el servicio)

**Métodos de Dominio:**
- `calcular_definitiva()`
- `calcular_promedio_ajustado()`
- `pesos_validos()`
- `peso_total()`

### NuevaCategoriaDTO
**Herencia**: BaseModel

Datos para crear una categoría de evaluación.

**Atributos:**
- `nombre`: str
- `peso`: float
- `asignacion_id`: int
- `periodo_id`: int

**Field Validators:**
- `validar_nombre()`
- `validar_peso()`

**Métodos de Dominio:**
- `to_categoria()`

### ActualizarCategoriaDTO
**Herencia**: BaseModel

Campos actualizables de una categoría.

**Atributos:**
- `nombre`: str | None
- `peso`: float | None

**Field Validators:**
- `validar_peso()`

**Métodos de Dominio:**
- `aplicar_a()`

### NuevaActividadDTO
**Herencia**: BaseModel

Datos para crear una actividad evaluativa.

**Atributos:**
- `nombre`: str
- `categoria_id`: int
- `descripcion`: str | None
- `fecha`: date | None
- `valor_maximo`: float
- `estado`: EstadoActividad

**Field Validators:**
- `validar_nombre()`
- `validar_valor()`

**Métodos de Dominio:**
- `to_actividad()`

### ActualizarActividadDTO
**Herencia**: BaseModel

Campos actualizables de una actividad.

**Atributos:**
- `nombre`: str | None
- `descripcion`: str | None
- `fecha`: date | None
- `valor_maximo`: float | None

**Métodos de Dominio:**
- `aplicar_a()`

### RegistrarNotaDTO
**Herencia**: BaseModel

Datos para registrar la nota de un único estudiante.

**Atributos:**
- `estudiante_id`: int
- `actividad_id`: int
- `valor`: float
- `usuario_registro_id`: int | None

**Field Validators:**
- `validar_valor()`

**Métodos de Dominio:**
- `to_nota()`

### RegistrarNotasMasivasDTO
**Herencia**: BaseModel

Registra notas para múltiples estudiantes en una misma actividad.
Operación del ag-grid de la planilla de notas.

**Atributos:**
- `actividad_id`: int
- `notas`: list[RegistrarNotaDTO]
- `usuario_registro_id`: int | None

**Field Validators:**
- `validar_id()`

**Propiedades:**
- `total_notas`

### ResultadoEstudianteDTO
**Herencia**: BaseModel

Resumen de notas de un estudiante en una asignación.
Consumido por la planilla de notas y el informe de calificaciones.

**Atributos:**
- `estudiante_id`: int
- `nombre_completo`: str
- `notas`: dict[int, float]
- `definitiva`: float
- `promedio_ajustado`: float
- `posee_piar`: bool

### FiltroNotasDTO
**Herencia**: BaseModel

Parámetros para consultar notas.

**Atributos:**
- `asignacion_id`: int
- `periodo_id`: int
- `estudiante_id`: int | None
- `actividad_id`: int | None

## Modulo: `habilitacion.py`

### TipoHabilitacion
**Herencia**: str, Enum

### EstadoHabilitacion
**Herencia**: str, Enum

### EstadoPlanMejoramiento
**Herencia**: str, Enum

### Habilitacion
**Herencia**: BaseModel

Actividad de recuperación programada para un estudiante.

tipo=PERIODO: recupera la nota de un periodo específico.
              periodo_id es obligatorio.
tipo=ANUAL:   recupera la materia al final del año escolar.
              periodo_id debe ser None.

nota_antes:         nota del estudiante antes de la habilitación.
                    Útil para comparar progreso y para informes.
nota_habilitacion:  nota obtenida en la habilitación.
                    Solo puede existir en estado REALIZADA, APROBADA
                    o REPROBADA — nunca en PENDIENTE.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int | None
- `tipo`: TipoHabilitacion
- `nota_antes`: float | None
- `nota_habilitacion`: float | None
- `fecha`: date | None
- `estado`: EstadoHabilitacion
- `observacion`: str | None
- `usuario_registro_id`: int | None

**Field Validators:**
- `validar_id_positivo()`
- `validar_nota()`
- `limpiar_observacion()`

**Model Validators:**
- `validar_coherencia()`

**Propiedades:**
- `esta_pendiente`
- `fue_realizada`
- `tiene_resultado_final`
- `mejoro_nota`

**Métodos de Dominio:**
- `_validar_transicion()`
- `registrar_nota()`
- `aprobar()`
- `reprobar()`

### PlanMejoramiento
**Herencia**: BaseModel

Plan de trabajo diseñado para que el estudiante supere sus dificultades
académicas dentro del mismo periodo o entre periodos.

Decreto 1290: los planes de mejoramiento son obligatorios cuando un
estudiante tiene desempeño bajo y deben quedar documentados.

Estado terminal: CUMPLIDO o INCUMPLIDO — un plan cerrado no se modifica.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `descripcion_dificultad`: str
- `actividades_propuestas`: str
- `fecha_inicio`: date
- `fecha_seguimiento`: date | None
- `fecha_cierre`: date | None
- `estado`: EstadoPlanMejoramiento
- `observacion_cierre`: str | None
- `usuario_id`: int | None

**Field Validators:**
- `validar_id_positivo()`
- `validar_texto_requerido()`
- `limpiar_observacion_cierre()`

**Model Validators:**
- `validar_coherencia()`

**Propiedades:**
- `esta_activo`
- `esta_cerrado`
- `tiene_seguimiento_programado`
- `seguimiento_vencido`
- `dias_activo`

**Métodos de Dominio:**
- `programar_seguimiento()`
- `cerrar()`

### NuevaHabilitacionDTO
**Herencia**: BaseModel

Datos para programar una habilitación.

**Atributos:**
- `estudiante_id`: int
- `asignacion_id`: int
- `tipo`: TipoHabilitacion
- `periodo_id`: int | None
- `nota_antes`: float | None
- `fecha`: date | None

**Field Validators:**
- `validar_nota()`

**Model Validators:**
- `validar_tipo_periodo()`

**Métodos de Dominio:**
- `to_habilitacion()`

### RegistrarNotaHabilitacionDTO
**Herencia**: BaseModel

Datos para registrar la nota cuando el estudiante presenta la habilitación.

**Atributos:**
- `nota`: float
- `fecha`: date | None
- `usuario_id`: int | None
- `observacion`: str | None

**Field Validators:**
- `validar_nota()`

### NuevoPlanMejoramientoDTO
**Herencia**: BaseModel

Datos para crear un plan de mejoramiento.

**Atributos:**
- `estudiante_id`: int
- `asignacion_id`: int
- `periodo_id`: int
- `descripcion_dificultad`: str
- `actividades_propuestas`: str
- `fecha_seguimiento`: date | None

**Field Validators:**
- `validar_texto()`

**Métodos de Dominio:**
- `to_plan()`

### CerrarPlanMejoramientoDTO
**Herencia**: BaseModel

Datos para cerrar un plan de mejoramiento.

**Atributos:**
- `estado`: EstadoPlanMejoramiento
- `observacion`: str
- `fecha`: date | None

**Field Validators:**
- `validar_estado_cierre()`
- `validar_observacion()`

### FiltroHabilitacionesDTO
**Herencia**: BaseModel

Parámetros para listar habilitaciones.

**Atributos:**
- `estudiante_id`: int | None
- `asignacion_id`: int | None
- `periodo_id`: int | None
- `tipo`: TipoHabilitacion | None
- `estado`: EstadoHabilitacion | None
- `pagina`: int
- `por_pagina`: int

## Modulo: `infraestructura.py`

### Jornada
**Herencia**: str, Enum

### DiaSemana
**Herencia**: str, Enum

### AreaConocimiento
**Herencia**: BaseModel

Área del currículo colombiano (Ley 115 de 1994, Art. 23).
Ejemplos: 'Matemáticas', 'Ciencias Naturales y Educación Ambiental'.

**Atributos:**
- `id`: int | None
- `nombre`: str
- `codigo`: str | None

**Field Validators:**
- `validar_nombre()`
- `limpiar_codigo()`

### Asignatura
**Herencia**: BaseModel

Asignatura que se dicta en la institución.
Pertenece a un área de conocimiento.

**Atributos:**
- `id`: int | None
- `nombre`: str
- `codigo`: str | None
- `area_id`: int | None
- `horas_semanales`: int

**Field Validators:**
- `validar_nombre()`
- `limpiar_codigo()`
- `validar_area_id()`

### Grupo
**Herencia**: BaseModel

Grupo escolar (curso). Cada grupo tiene un grado, jornada y
capacidad máxima de estudiantes.

El código es el identificador legible: '601', '1101', 'A1', etc.

**Atributos:**
- `id`: int | None
- `codigo`: str
- `nombre`: str | None
- `grado`: int | None
- `jornada`: Jornada
- `capacidad_maxima`: int

**Field Validators:**
- `validar_codigo()`
- `limpiar_nombre()`
- `validar_grado()`

**Propiedades:**
- `descripcion_completa`
- `descripcion_corta`

**Métodos de Dominio:**
- `esta_lleno()`
- `cupos_disponibles()`

### Horario
**Herencia**: BaseModel

Franja horaria de una asignatura para un grupo en un periodo.

hora_inicio y hora_fin aceptan objetos time o strings "HH:MM".
Invariante: hora_inicio < hora_fin.

**Atributos:**
- `id`: int | None
- `grupo_id`: int
- `asignatura_id`: int
- `usuario_id`: int
- `asignacion_id`: int | None
- `periodo_id`: int
- `dia_semana`: DiaSemana
- `hora_inicio`: time
- `hora_fin`: time
- `sala`: str

**Field Validators:**
- `validar_id_positivo()`
- `parsear_hora()`
- `validar_sala()`

**Model Validators:**
- `validar_orden_horas()`

**Propiedades:**
- `duracion_minutos`
- `franja_display`

### Logro
**Herencia**: BaseModel

Logro o competencia evaluado en una asignación durante un periodo.

El logro es el enunciado del aprendizaje esperado que aparece
en el boletín junto a la nota. Ejemplo:
'Comprende y aplica los conceptos de función cuadrática.'

**Atributos:**
- `id`: int | None
- `asignacion_id`: int
- `periodo_id`: int
- `descripcion`: str
- `orden`: int

**Field Validators:**
- `validar_id_positivo()`
- `validar_descripcion()`

### NuevaAreaDTO
**Herencia**: BaseModel

**Atributos:**
- `nombre`: str
- `codigo`: str | None

**Field Validators:**
- `validar_nombre()`

**Métodos de Dominio:**
- `to_area()`

### NuevaAsignaturaDTO
**Herencia**: BaseModel

**Atributos:**
- `nombre`: str
- `codigo`: str | None
- `area_id`: int | None
- `horas_semanales`: int

**Field Validators:**
- `validar_nombre()`

**Métodos de Dominio:**
- `to_asignatura()`

### NuevoGrupoDTO
**Herencia**: BaseModel

**Atributos:**
- `codigo`: str
- `nombre`: str | None
- `grado`: int | None
- `jornada`: Jornada
- `capacidad_maxima`: int

**Field Validators:**
- `validar_codigo()`

**Métodos de Dominio:**
- `to_grupo()`

### NuevoHorarioDTO
**Herencia**: BaseModel

**Atributos:**
- `grupo_id`: int
- `asignatura_id`: int
- `usuario_id`: int
- `periodo_id`: int
- `dia_semana`: DiaSemana
- `hora_inicio`: time
- `hora_fin`: time
- `asignacion_id`: int | None
- `sala`: str

**Field Validators:**
- `parsear_hora()`

**Model Validators:**
- `validar_horas()`

**Métodos de Dominio:**
- `to_horario()`

### NuevoLogroDTO
**Herencia**: BaseModel

**Atributos:**
- `asignacion_id`: int
- `periodo_id`: int
- `descripcion`: str
- `orden`: int

**Field Validators:**
- `validar_descripcion()`

**Métodos de Dominio:**
- `to_logro()`

### HorarioInfo
**Herencia**: BaseModel

Vista enriquecida de un bloque horario con nombres resueltos por JOIN.

Equivalente a AsignacionInfo para el módulo de horarios. No se persiste:
lo construye el repositorio desde una consulta con JOINs sobre grupos,
asignaturas, usuarios y periodos.

El grid de la página de horarios consume este modelo directamente.
Los nombres de campo son los que el repositorio mapea desde las columnas
del JOIN; la página v2.0 los usa sin transformación adicional.

**Atributos:**
- `id`: int
- `grupo_id`: int
- `grupo_codigo`: str
- `asignatura_id`: int
- `asignatura_nombre`: str
- `usuario_id`: int
- `docente_nombre`: str
- `asignacion_id`: int | None
- `periodo_id`: int
- `periodo_nombre`: str
- `dia_semana`: DiaSemana
- `hora_inicio`: time
- `hora_fin`: time
- `sala`: str

**Field Validators:**
- `no_vacio()`
- `parsear_hora()`

**Propiedades:**
- `franja_display`
- `duracion_minutos`
- `display_completo`
- `display_corto`

### HorarioEstadisticasDTO
**Herencia**: BaseModel

Métricas del horario maestro para el panel de estadísticas.

El servicio calcula estos valores a partir de queries de agregación;
la página los muestra directamente sin lógica adicional.

**Atributos:**
- `total_bloques`: int
- `grupos_cubiertos`: int
- `materias_cargadas`: int
- `docentes_con_horario`: int

## Modulo: `periodo.py`

### TipoHito
**Herencia**: str, Enum

### Periodo
**Herencia**: BaseModel

Periodo académico dentro de un año lectivo.

Cada periodo tiene un peso porcentual que define cuánto contribuye
a la nota anual del estudiante. Para cuatro periodos con pesos iguales,
cada uno vale 25%.

El flag `cerrado` es el candado de evaluación: una vez cerrado,
ningún trigger de BD ni ningún servicio debería aceptar nuevas notas
para ese periodo. El modelo lo hace explícito para que los servicios
puedan verificarlo antes de llegar a la BD.

**Atributos:**
- `id`: int | None
- `anio_id`: int
- `numero`: int
- `nombre`: str
- `fecha_inicio`: date | None
- `fecha_fin`: date | None
- `peso_porcentual`: float
- `activo`: bool
- `cerrado`: bool
- `fecha_cierre_real`: datetime | None

**Field Validators:**
- `validar_anio_id()`
- `validar_numero()`
- `validar_nombre()`
- `validar_peso()`

**Model Validators:**
- `validar_coherencia_fechas()`

**Propiedades:**
- `esta_abierto`
- `esta_vigente`
- `duracion_dias`
- `en_curso`

**Métodos de Dominio:**
- `cerrar()`
- `activar()`
- `desactivar()`

### HitoPeriodo
**Herencia**: BaseModel

Fecha límite o evento importante dentro de un periodo.

Ejemplos: fecha límite de entrega de notas, inicio de habilitaciones,
entrega de boletines. Los hitos sirven para alertas automáticas
y para mostrar el cronograma en el panel de director.

**Atributos:**
- `id`: int | None
- `periodo_id`: int
- `tipo`: TipoHito
- `descripcion`: str | None
- `fecha_limite`: date | None

**Field Validators:**
- `validar_periodo_id()`
- `limpiar_descripcion()`

**Propiedades:**
- `esta_vencido`
- `dias_restantes`

### NuevoPeriodoDTO
**Herencia**: BaseModel

Datos para crear un periodo nuevo.

**Atributos:**
- `anio_id`: int
- `numero`: int
- `nombre`: str
- `peso_porcentual`: float
- `fecha_inicio`: date | None
- `fecha_fin`: date | None

**Field Validators:**
- `validar_numero()`
- `validar_peso()`

**Model Validators:**
- `validar_fechas()`

**Métodos de Dominio:**
- `to_periodo()`

### ActualizarPeriodoDTO
**Herencia**: BaseModel

Campos actualizables de un periodo. Todos opcionales.

**Atributos:**
- `nombre`: str | None
- `peso_porcentual`: float | None
- `fecha_inicio`: date | None
- `fecha_fin`: date | None
- `activo`: bool | None

**Field Validators:**
- `validar_nombre()`

**Métodos de Dominio:**
- `aplicar_a()`

### NuevoHitoPeriodoDTO
**Herencia**: BaseModel

Datos para registrar un hito dentro de un periodo.

`descripcion` es obligatoria — un hito sin descripción no tiene
significado para el usuario. `fecha_limite` es obligatoria en la
UI pero se acepta como None para hitos de tipo informativo sin
fecha límite definida.

**Atributos:**
- `periodo_id`: int
- `tipo`: TipoHito
- `descripcion`: str
- `fecha_limite`: date | None

**Field Validators:**
- `validar_descripcion()`
- `validar_periodo_id()`

**Métodos de Dominio:**
- `to_hito()`

## Modulo: `piar.py`

### PIAR
**Herencia**: BaseModel

Plan Individual de Apoyos y Ajustes Razonables de un estudiante.

El PIAR recoge las necesidades educativas específicas del estudiante
y los ajustes acordados entre el equipo docente, el estudiante y su familia.
No es un diagnóstico médico — es un instrumento pedagógico.

**Atributos:**
- `id`: int | None
- `estudiante_id`: int
- `anio_id`: int
- `descripcion_necesidad`: str
- `ajustes_evaluativos`: str | None
- `ajustes_pedagogicos`: str | None
- `profesionales_apoyo`: str | None
- `fecha_elaboracion`: date
- `fecha_revision`: date | None
- `usuario_elaboracion_id`: int | None

**Field Validators:**
- `validar_descripcion()`
- `limpiar_campo_opcional()`
- `validar_fecha_elaboracion()`
- `validar_fecha_revision()`

**Model Validators:**
- `validar_orden_fechas()`

**Propiedades:**
- `tiene_revision_programada`
- `revision_vencida`
- `dias_para_revision`
- `tiene_ajustes_evaluativos`
- `tiene_ajustes_pedagogicos`

**Métodos de Dominio:**
- `programar_revision()`
- `actualizar_ajustes()`

### NuevoPIARDTO
**Herencia**: BaseModel

Datos para registrar un PIAR nuevo.

**Atributos:**
- `estudiante_id`: int
- `anio_id`: int
- `descripcion_necesidad`: str
- `ajustes_evaluativos`: str | None
- `ajustes_pedagogicos`: str | None
- `profesionales_apoyo`: str | None
- `fecha_revision`: date | None

**Field Validators:**
- `validar_descripcion()`

**Métodos de Dominio:**
- `to_piar()`

### ActualizarPIARDTO
**Herencia**: BaseModel

Campos actualizables de un PIAR. Todos opcionales.

**Atributos:**
- `descripcion_necesidad`: str | None
- `ajustes_evaluativos`: str | None
- `ajustes_pedagogicos`: str | None
- `profesionales_apoyo`: str | None
- `fecha_revision`: date | None

**Field Validators:**
- `validar_descripcion()`

**Métodos de Dominio:**
- `aplicar_a()`

## Modulo: `usuario.py`

### Rol
**Herencia**: str, Enum

### Usuario
**Herencia**: BaseModel

Entidad que representa a cualquier usuario del sistema.

La password_hash nunca se incluye en este modelo.
El servicio de autenticación la maneja de forma independiente.

Roles y sus usos habituales:
  admin        → acceso total, gestión del sistema
  director     → configuración académica, cierre de periodos
  coordinador  → seguimiento disciplinario y académico
  profesor     → notas, asistencia, observaciones de sus grupos
  estudiante   → consulta (v3.0)
  apoderado    → portal de acudientes (v3.0)

**Atributos:**
- `id`: int | None
- `usuario`: str
- `nombre_completo`: str
- `email`: str | None
- `telefono`: str | None
- `rol`: Rol
- `activo`: bool
- `fecha_creacion`: date
- `ultima_sesion`: datetime | None

**Field Validators:**
- `validar_usuario()`
- `validar_nombre()`
- `validar_email()`
- `limpiar_telefono()`

**Propiedades:**
- `esta_activo`
- `es_docente`
- `es_directivo`
- `puede_gestionar_evaluaciones`
- `nombre_display`

**Métodos de Dominio:**
- `desactivar()`
- `reactivar()`
- `registrar_sesion()`

### DocenteInfoDTO
**Herencia**: BaseModel

Vista estadística de un docente para el grid principal de profesores.

Producida por la query de `obtener_listado_profesores()` que hace
JOIN con horarios y asignaciones para calcular la carga académica.

**Atributos:**
- `id`: int
- `usuario`: str
- `nombre_completo`: str
- `email`: str | None
- `telefono`: str | None
- `activo`: bool
- `fecha_creacion`: date | None
- `ultima_sesion`: datetime | None
- `total_asignaciones`: int
- `grupos_asignados`: int
- `asignaturas_asignadas`: int
- `horas_totales`: int
- `bloques_horarios`: int

**Propiedades:**
- `tiene_carga`
- `resumen_carga`

### AsignacionDocenteInfoDTO
**Herencia**: BaseModel

Detalle de una asignación de un docente específico.

Producida por `obtener_asignaciones_profesor()` con JOIN entre
asignaciones, grupos, asignaturas y periodos.
Incluye el comparativo entre horas teóricas y horas programadas.

**Atributos:**
- `id`: int
- `grupo_id`: int
- `grupo_codigo`: str
- `grupo_nombre`: str | None
- `asignatura_id`: int
- `asignatura_nombre`: str
- `asignatura_codigo`: str | None
- `horas_teoricas`: int
- `horas_programadas`: int
- `periodo_id`: int
- `periodo_nombre`: str
- `activo`: bool

**Propiedades:**
- `horas_pendientes`
- `horario_completo`
- `display`

### NuevoUsuarioDTO
**Herencia**: BaseModel

Datos para crear un usuario nuevo.

La contraseña se gestiona por separado en el servicio de autenticación.
Si no se provee, el servicio usa el username como contraseña inicial.

**Atributos:**
- `usuario`: str
- `nombre_completo`: str
- `rol`: Rol
- `email`: str | None
- `telefono`: str | None
- `password`: str | None

**Field Validators:**
- `validar_usuario()`
- `validar_nombre()`
- `validar_email()`

**Métodos de Dominio:**
- `to_usuario()`

### ActualizarUsuarioDTO
**Herencia**: BaseModel

Campos actualizables de un usuario. Todos opcionales.
El username y el rol no se actualizan aquí.

**Atributos:**
- `nombre_completo`: str | None
- `email`: str | None
- `telefono`: str | None

**Field Validators:**
- `validar_nombre()`
- `validar_email()`

**Métodos de Dominio:**
- `aplicar_a()`

### UsuarioResumenDTO
**Herencia**: BaseModel

Vista mínima para selects, lookups y referencias en otros módulos.

**Atributos:**
- `id`: int
- `usuario`: str
- `nombre_completo`: str
- `rol`: Rol
- `activo`: bool

**Métodos de Dominio:**
- `desde_usuario()`

### FiltroUsuariosDTO
**Herencia**: BaseModel

Parámetros para listar usuarios.

**Atributos:**
- `rol`: Rol | None
- `solo_activos`: bool
- `busqueda`: str | None
- `pagina`: int
- `por_pagina`: int

**Field Validators:**
- `limpiar_busqueda()`
