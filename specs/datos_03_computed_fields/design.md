# Diseño: datos_03_computed_fields

## Punto de partida medido

Introspección sobre `src/domain/models/`: **123 propiedades en 46 modelos**, y
**0 usos de `@computed_field`**. Ninguna aparece en `model_dump()` ni en el JSON.

Cuando la interfaz pase a Vue sobre la API, esos 123 valores desaparecen del payload y
habría que recalcularlos en TypeScript — la regla de negocio quedaría duplicada en dos
lenguajes, contra `docs/conventions.md §14`.

## Clasificación

El criterio no es el tipo de retorno sino **quién necesita el valor**: si un cliente que
solo recibe JSON tendría que reimplementar la regla, el valor viaja (grupo A); si solo
sirve para presentarlo en pantalla, no viaja (grupo B).

| Grupo | Qué es | Destino | Nº |
|---|---|---|---|
| **A** | Regla de negocio | `@computed_field` — viaja en el JSON | **88** |
| **B** | Formato de presentación | sigue `@property` — no viaja | **26** |
| **C** | Regla de negocio dependiente de la fecha actual | `@computed_field` con cautelas | **9** |

### Grupo B — presentación (26): NO viajan

Se quedan como `@property`. Satisfacen R5 y R6.

| Modelo | Propiedades |
|---|---|
| `acudiente.Acudiente` | `contacto_display`, `documento_display` |
| `asignacion.AsignacionInfo` | `display_completo`, `display_corto`, `display_docente_materia` |
| `asistencia.ResumenAsistenciaDTO` | `resumen_display` |
| `asistencia.ControlDiario` | `estado_descripcion` |
| `auditoria.EventoSesion` | `fecha_display` |
| `auditoria.RegistroCambio` | `timestamp_display` |
| `cierre.CierrePeriodo`, `cierre.CierreAnio` | `nota_display` |
| `configuracion.ConfiguracionAnio` | `anio_display`, `rango_fechas_display` |
| `estudiante.Estudiante` | `documento_display` |
| `estudiante.MovimientoEstudianteInfoDTO` | `fecha_display`, `ruta_display` |
| `infraestructura.Grupo` | `descripcion_completa`, `descripcion_corta` |
| `infraestructura.Horario` | `franja_display` |
| `infraestructura.HorarioInfo` | `franja_display`, `display_completo`, `display_corto` |
| `institucion.Institucion` | `nombre_display` |
| `usuario.Usuario` | `nombre_display` |
| `usuario.DocenteInfoDTO` | `resumen_carga` |
| `usuario.AsignacionDocenteInfoDTO` | `display` |

Señal que las identifica: construyen una cadena con `f"…"` a partir de campos que el
cliente ya recibe. Un cliente Vue compone esas cadenas con sus propias reglas de idioma y
formato; enviarlas sería imponerle las nuestras.

**Excepción deliberada:** `estudiante.Estudiante.nombre_completo` construye una cadena
pero **sí va al grupo A**. Es el identificador legible de la persona, se usa en listados,
búsquedas y selecciones, y su regla de composición (apellido y nombre, ya normalizados a
title-case por el modelo) es de negocio, no de estilo.

### Grupo C — dependientes de la fecha actual (9)

| Modelo | Propiedad |
|---|---|
| `alerta.Alerta` | `dias_pendiente` |
| `estudiante.Estudiante` | `edad` |
| `habilitacion.PlanMejoramiento` | `seguimiento_vencido`, `dias_activo` |
| `periodo.Periodo` | `en_curso` |
| `periodo.HitoPeriodo` | `esta_vencido`, `dias_restantes` |
| `piar.PIAR` | `revision_vencida`, `dias_para_revision` |

Las nueve invocan `date.today()` o `datetime.now()`. **Van a `@computed_field`** (R12): que
se recalculen al servir es justamente lo correcto — un hito vencido debe leerse como
vencido hoy, no como estaba cuando se cargó la fila.

Consecuencia que hay que asumir y documentar (R13): **la representación serializada de
estos modelos no es estable entre días.** Ningún test puede fijar un valor esperado sin
congelar la fecha (R14), y ninguna caché de respuestas puede tratarlas como inmutables.

### Grupo A — regla de negocio (88): viajan en el JSON

Los 89 valores de negocio puros medidos, menos `estado_descripcion` y `descripcion_corta`
(reclasificados a B), más `nombre_completo`. Cubre entre otros:

| Modelo | Propiedades representativas |
|---|---|
| `estudiante.Estudiante` | `nombre_completo`, `es_activo`, `puede_recibir_calificaciones`, `requiere_atencion_diferencial` |
| `evaluacion.Nota` | `es_aprobatoria` |
| `evaluacion.Actividad` | `esta_publicada`, `acepta_notas` |
| `evaluacion.Categoria` | `peso_porcentaje`, `es_docente` |
| `alerta.Alerta` | `esta_pendiente`, `es_critica` |
| `cierre.PromocionAnual` | `esta_pendiente`, `esta_finalizado`, `fue_promovido`, `fue_reprobado`, `es_condicional` |
| `cierre.CierreAnio` | `tiene_habilitacion`, `mejoro_con_habilitacion` |
| `habilitacion.Habilitacion` | `esta_pendiente`, `fue_realizada`, `tiene_resultado_final`, `mejoro_nota` |
| `asistencia.ResumenAsistenciaDTO` | `porcentaje_asistencia`, `total_faltas`, `en_riesgo_por_faltas` |
| `asistencia.ControlDiario` | `es_presencia_efectiva`, `requiere_justificacion` |
| `convivencia.RegistroComportamiento` | `es_negativo`, `es_positivo`, `pendiente_notificacion`, `tiene_seguimiento` |
| `usuario.Usuario` | `esta_activo`, `es_docente`, `es_directivo`, `puede_gestionar_evaluaciones`, `carga_maxima_efectiva` |
| `infraestructura.CupoDTO` | `disponibles`, `excedido` |

El inventario íntegro se genera y se fija en T1; esta tabla es la muestra representativa,
no la lista cerrada.

## Decisiones

### D1 — `@computed_field` conserva el acceso sin paréntesis

`docs/conventions.md §8` exige que las propiedades booleanas se lean sin paréntesis
(`if estudiante.es_activo:`). `@computed_field` envuelve una `property`, así que el acceso
como atributo se mantiene. Satisface R8, R9 y R16 sin tocar ni un consumidor. **T1 lo
verifica antes de convertir nada**, en lugar de darlo por hecho.

### D2 — Ningún valor derivado es de entrada

`@computed_field` es de solo lectura: Pydantic lo excluye de los campos de entrada. Con
`extra="forbid"` en los DTO (`datos_02`), enviar un valor derivado en un cuerpo de
petición se rechaza en vez de ignorarse. Satisface R17. **Depende de `datos_02`.**

### D3 — Verificación del coste (R10, R11)

Ninguna de las 123 propiedades toca repositorios ni `Container` — comprobado por
inspección del cuerpo de cada `fget`. Aun así, un `@computed_field` se evalúa **en cada
serialización**, no una vez: en un listado de 500 estudiantes, `edad` se calcula 500
veces. Todas las del grupo A son comparaciones o aritmética sobre campos propios, así que
el coste es despreciable, pero T2 lo mide en lugar de suponerlo.

### D4 — Orden respecto a `datos_02`

Este paso va **después** de `datos_02`. La base común es donde se decide la política de
serialización, y `@computed_field` interactúa con `extra` (D2) y con la clasificación
entidad/DTO. Aplicarlo antes obligaría a repasar los mismos 16 módulos dos veces.

## Alternativa descartada

**Dejar las 123 como propiedades y exponer los valores derivados en modelos de respuesta
propios de la capa API (`backend_12_endpoints_crud`).**

Es la separación más ortodoxa: el dominio no sabría nada de serialización. Se descarta
porque traslada las 123 reglas a una capa que todavía no existe y obliga a mantener en
paralelo el modelo de dominio y su modelo de respuesta —dos definiciones que divergen a
la primera regla que cambie—. `@computed_field` mantiene una sola definición, es la que
ya usa el resto del sistema al leerlas como atributo, y no impide que `backend_12`
construya después modelos de respuesta que las seleccionen.
