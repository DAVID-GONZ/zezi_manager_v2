# Capa de Servicios (Application Services)

La capa de servicios (`src/services/`) representa los **Casos de Uso** de la aplicación ZECI Manager v2.0. Actúa como el orquestador principal del sistema, coordinando la lógica de negocio, validando permisos y restricciones, y sirviendo como puente absoluto entre la capa de presentación (API/Controladores) y los modelos de dominio.

> 📖 **Referencia por método (firma + docstring):**
> [`docs/api_reference/servicios.md`](api_reference/servicios.md) — generada
> desde el código con `tools/gen_api_reference.py`. Este documento describe
> **responsabilidades**; la referencia enumera los 351 métodos con su firma exacta.

## Principios de Diseño

De acuerdo con la Arquitectura Limpia adoptada por el proyecto, los servicios siguen estos principios estrictos:

1. **Agnósticos a la Infraestructura:** No contienen sentencias SQL ni conocen detalles de la base de datos subyacente. Toda persistencia se realiza a través de interfaces (puertos) inyectadas (ej. `IUsuarioRepository`).
2. **Agnósticos a la Presentación:** No manejan objetos HTTP (`Request`/`Response`) ni excepciones propias de FastAPI. Reciben Primitivos/DTOs Pydantic y retornan Modelos de Dominio.
3. **Orquestación Pura:** La lógica intrínseca, cambios de estado y transiciones (ej. aprobar una materia) le pertenece a las Entidades de Dominio. El servicio orquesta los pasos: Buscar -> Llamar Entidad -> Persistir -> Auditar.

---

## Interacción Arquitectónica

El siguiente flujo demuestra la anatomía de una operación típica dentro de cualquier servicio del sistema:

```mermaid
sequenceDiagram
    participant Ctrl as API / Router
    participant Svc as Service
    participant Dom as Entidad Dominio
    participant Repo as IRepository
    participant Aud as IAuditoriaRepo

    Ctrl->>Svc: ejecutar_caso_uso(DTO)
    activate Svc
    Svc->>Repo: get_by_id(id)
    Repo-->>Svc: Entidad
    Svc->>Dom: entidad.accion(datos)
    Dom-->>Svc: Entidad Actualizada
    Svc->>Repo: actualizar(entidad)
    Svc->>Aud: registrar_cambio(estado_ant, estado_nuevo)
    Svc-->>Ctrl: Resultado
    deactivate Svc
```

---

## Servicios Principales y sus Responsabilidades

El núcleo de la aplicación está compuesto por **~23 servicios funcionales** altamente cohesivos, más **3 mecanismos neutrales** de la capa de servicios (solo-lectura, scope de tenant y throttle de login — ver la sección final). El cableado exacto de dependencias de cada servicio vive en `container.py` (composition root); esta sección resume responsabilidades.

### 1. `CierreService`
Es el corazón académico del sistema y el servicio más complejo.
- **Cierre de Periodo:** Valida que el periodo esté formalmente abierto. Para cada estudiante, consolida sus notas de la asignatura y delega a `CalculadorNotas.calcular_definitiva()`. Determina su `NivelDesempeno` y, si la nota es baja, dispara automáticamente una alerta de riesgo hacia el `AlertaService`.
- **Cierre Anual:** Se asegura de que todos los periodos del año estén cerrados. Promedia todas las calificaciones ponderadas. Detecta si hubo un examen de habilitación y lo promedia. Determina si la materia fue definitivamente aprobada o perdida.
- **Decisiones de Promoción:** Administra el dictamen final para determinar si un estudiante cambia de grado (Pasa de `PENDIENTE` a `PROMOVIDO`, `REPROBADO` o `CONDICIONAL`).

### 2. `EvaluacionService`
Maneja el día a día de las calificaciones del docente.
- **Validaciones Críticas:**
  - Garantiza que la suma de los "pesos porcentuales" de las categorías evaluativas de un periodo no exceda nunca el **100% (1.0)**.
  - Asegura que las notas numéricas solo puedan registrarse sobre actividades cuyo estado actual sea `PUBLICADA` (rechazando las de estado `BORRADOR` o `CERRADA`).
- **Live Calculation:** Es capaz de devolver una planilla entera con los promedios calculados al vuelo sin necesidad de haber cerrado el periodo.

### 3. `AsistenciaService` y `ConvivenciaService`
Servicios gemelos enfocados en la disciplina y la asistencia, con integraciones reactivas.
- **Alertas Automáticas:** Al procesar inasistencias o llamados de atención, consultan la configuración institucional. Si las faltas `INJUSTIFICADAS` o los llamados de atención superan el umbral permitido (ej. más de 5 faltas), instancian un objeto de la entidad `Alerta` de nivel `ADVERTENCIA` o `CRITICA` y lo insertan sin intervención del docente.
- **Trazabilidad:** `ConvivenciaService` permite hacer seguimiento narrativo a cada evento disciplinario y dejar constancia de la notificación al acudiente.

### 4. `AlertaService`
Central de gestión de alertas institucionales.
- Define dinámicamente las configuraciones anuales de umbrales.
- Expone el método `detectar_riesgo_academico()` que realiza un barrido masivo identificando estudiantes con múltiples materias perdidas simultáneamente.

### 5. `EstadisticosService` e `InformeService`
La dupla dedicada a extraer y presentar información (Business Intelligence interno).
- **`EstadisticosService`:** Es de Solo Lectura. Delega las agrupaciones pesadas a queries optimizadas en su repositorio. Calcula promedios generales por grupo, distribución de estudiantes por desempeños, rankings y promedios por área de conocimiento.
- **`InformeService`:** No accede directamente a BD. Toma los consolidados del `EstadisticosService` y se los inyecta a un `IExporterService` (exportadores Excel/PDF desconectados del framework) para entregar un archivo binario descargable (boletines, actas).

### 6. `HabilitacionService`
Control de procesos de recuperación.
- Permite programar exámenes de nivelación para estudiantes que reprobaron asignaturas anuales.
- Determina autónomamente la aprobación del examen evaluando la calificación frente a la configuración `nota_minima_habilitacion` de la institución.

### 14. `NivelacionService` *(Nuevo — Junio 2026)*
Gestión del proceso post-cierre de período establecido por Decreto 1290.
- Crea y valida actividades de nivelación por asignación+periodo (cada actividad tiene peso; la suma debe ser 1.0 para poder cerrar).
- Gestiona la calificación por estudiante (upsert de `NotaNivelacion`).
- Cierra la nivelación emitiendo un `CierreNivelacion` — inmutable una vez cerrado.
- Delega el cálculo de la nota definitiva al `CalculadorNivelacion`, que no almacena el valor calculado.
- Solo acepta nivelaciones para asignaciones con `CierrePeriodo` existente.

### 15. `PlanMejoramientoService` *(Nuevo — Junio 2026)*
Gestión del plan de mejoramiento cuantitativo (distinto del plan narrativo de `HabilitacionService`).
- **Ejecutar corte:** Calcula la nota al corte de cada estudiante de la asignación usando las notas existentes en `EvaluacionService`. Determina quién va al plan (nota < umbral proporcional).
- **Actividades del plan:** CRUD de `ActividadPlan` con validación de suma de pesos ≤ 1.0.
- **Notas del plan:** Calificación por estudiante en cada actividad.
- **Cierre por estudiante:** Marca `APROBADO` o `REPROBADO` y congela la `nota_definitiva_plan`.

### 16. `InfraestructuraService` *(fachada — descompuesto en `mejora_01`)*
Históricamente el "objeto-Dios" de la infraestructura académica (~75 métodos). En
`mejora_01` (fase 1, import-safe) su **lógica se movió a 5 sub-servicios cohesivos**
y quedó como **fachada por delegación**: conserva sus métodos públicos (y sus
re-exports de dominio) delegando en los sub-servicios vía `self._repo`, de modo que
la capa de interfaz no cambió. El re-apuntado de consumidores y el retiro de la
fachada son la fase 2 (`mejora_05`).

#### Sub-servicios resultantes (`mejora_01`)

| Servicio | Subdominio | Métodos |
|---|---|---|
| `SalaService` | Salas (CRUD + asignar sala a grupo) | 6 |
| `FranjaService` | Plantillas de franja y franjas | 7 |
| `EscenarioHorarioService` | Escenarios de horario + horario por escenario | 12 |
| `CatalogoAcademicoService` | Áreas, asignaturas, grupos | 14 |
| `RestriccionGeneracionService` | Config de generación, ventanas, bloques anclados, franjas de reunión, límites y disponibilidad docente | 30 |

Cada uno recibe `infraestructura_repo` por constructor y está cableado en
`Container` (`Container.sala_service()`, etc.).

**Fase 2 (`mejora_05`) — completada:** la capa de interfaz quedó **100%
re-apuntada** a los sub-servicios (0 referencias a `Container.infraestructura_service()`
en `src/interface/`), y los métodos de bloques de horario se consolidaron en
`HorarioService`. `InfraestructuraService` **se conserva como agregador del
`GeneradorHorarioService`** (le expone `construir_restricciones()` y varios
subdominios en un solo objeto); es un uso legítimo del patrón Facade, no deuda.
Los tipos que la interfaz importaba de este módulo (`DiaSemana`,
`AreaConocimiento`, `Asignatura`, `Grupo`, `Sala`) ahora se re-exportan desde el
sub-servicio dueño (la interfaz no puede importar `src.domain.models`, convención §2).

### 17. `PlanEstudiosService` *(Nuevo — Junio 2026)*
Gestiona la relación `Grado → Asignatura → horas_semanales`.
- Permite definir cuántas horas semanales tiene cada asignatura por grado.
- Usa un `asignacion_svc_provider` callable para obtener las asignaciones existentes sin crear dependencia circular.
- Valida que las horas del plan de estudios sean coherentes con las asignaciones activas.

### 18. `PreparacionHorarioService` *(Nuevo — Junio 2026)*
Construye el contexto de preparación necesario antes de generar horarios.
- Gestiona `PlantillaFranja` y `Franja` (la rejilla de franjas horarias).
- Gestiona `EscenarioHorario` (contenedor de una versión del horario maestro).
- Gestiona `DisponibilidadDocente` (restricciones de disponibilidad por docente).
- Gestiona `ConfigGeneracion` (parámetros y pesos para el algoritmo generador).
- Expone `VentanaGrupo`, `BloqueAnclado`, `FranjaReunion`, `LimitesDocente` como restricciones de generación.

### 19. `HorarioService` *(Nuevo — Junio 2026)*
CRUD de bloques horarios dentro de un escenario.
- Inserta, actualiza y elimina bloques horarios con validación de conflictos (`existe_cruce`).
- Valida que el docente no tenga otro bloque solapado en la misma franja (mismo escenario).
- Expone las vistas enriquecidas (`HorarioInfo`) para los grids de la UI.

### 20. `GeneradorHorarioService` *(Nuevo — Junio 2026)*
Genera automáticamente la grilla completa de horarios para un periodo.
- Lee la `ConfigGeneracion` activa (pesos para la función objetivo: distribución, respeto de disponibilidad, cumplimiento de horas).
- Itera por grupos y asignaturas del plan de estudios para asignar bloques a franjas disponibles.
- Respeta las restricciones: `DisponibilidadDocente`, `VentanaGrupo`, `BloqueAnclado`, `FranjaReunion`, `LimitesDocente`.
- Escribe los bloques generados en el `EscenarioHorario` destino indicado en la config.
- Retorna `ResultadoGeneracionDTO` con los bloques y `MetricasCalidadDTO` para evaluación del resultado.

### 7. `EstudianteService` y `UsuarioService`
Manejo de Actores.
- **`EstudianteService`:** Matriculación, retiros de la institución y sincronización del flag de inclusión `posee_piar` al crear registros para estudiantes con necesidades especiales (PIAR).
- **`UsuarioService`:** Control de acceso, perfiles de roles, y comunicación con el puerto `IAuthenticationService` (que oculta los detalles de encriptación y hashes `bcrypt` al dominio principal).

### 8. `AcudienteService`
Vinculación de responsables legales (padres, madres o tutores) a los estudiantes.
- Gestiona la información de contacto esencial para notificaciones.
- Permite designar un acudiente principal para las comunicaciones críticas e informes.

### 9. `AsignacionService`
Core de la relación Docente-Asignatura-Grupo. 
- Determina qué profesor dicta qué materia y a quién. Es el pivote de validación cuando un docente intenta registrar notas o asistencia (solo puede hacerlo para sus asignaciones activas).

### 10. `AuditoriaService`
El vigilante silencioso del sistema.
- Expone métodos para registrar trazas de eventos y cambios de estado profundos. 
- Actúa de forma pasiva y es consumido transversalmente por los demás servicios mediante el método protegido `_auditar()`.

### 11. `ConfiguracionService`
Maneja el estado paramétrico global e institucional.
- Gestiona el número de periodos del año.
- Define el Sistema Institucional de Evaluación (escala valorativa, umbrales de aprobación, nota mínima de habilitación), sirviendo de fuente de verdad para los cálculos matemáticos de otros servicios.

### 12. `InfraestructuraService`
Administrador de la topología escolar.
- Gestiona la creación de Áreas de Conocimiento, Asignaturas, Grados y Grupos.
- Controla y valida el módulo de horarios para evitar conflictos (ej. un docente programado en dos grupos a la vez).

### 13. `PeriodoService`
Ciclo de vida del tiempo académico.
- Controla el estado `ACTIVO`, `CERRADO` o `FUTURO` de los lapsos lectivos del año escolar.
- Sus transiciones bloquean o permiten de forma absoluta la escritura de nuevas calificaciones a nivel de todo el colegio.

### 21. `InstitucionService` *(Nuevo — multi-tenant, paso_24)*
Orquesta el catálogo de instituciones (tenants).
- `listar()`, `get()`, `get_por_defecto()` / `id_por_defecto()` (institución #1),
  y `crear()` (verifica unicidad del nombre antes de insertar).
- Es *tenant-aware*: el caso de uso de creación está protegido con
  `@requiere_escritura` (respeta el modo "Ver como"). No contiene SQL ni
  presentación. Ver `docs/architecture.md` §9.

---

## Mecanismos neutrales de la capa de servicios

Tres módulos de `src/services/` **no son servicios de casos de uso** sino
mecanismos transversales sin estado de negocio. No importan interfaz ni
infraestructura (misma regla de capas que los servicios).

- **`solo_lectura.py`** — modo solo lectura central para la impersonación
  "Ver como". Expone `verificar_escritura()` y el decorador `@requiere_escritura`
  que los métodos de **mutación** de todos los servicios usan al inicio; lanza
  `OperacionSoloLecturaError` (subclase de `PermissionError`). Estado en un
  `ContextVar` con default `False` (los métodos de lectura no se tocan).
- **`contexto_tenant.py`** — scope de institución activo de la sesión.
  `institucion_actual()` (regla admin→`None` / resto→su tenant),
  `verificar_pertenencia(id_del_objeto_leído)` para operaciones por `id`, y el
  context manager `usar_institucion(id)` para seed/scripts/tests sin sesión.
- **`login_throttle.py`** — freno de fuerza bruta del login (A1): tras
  `MAX_INTENTOS=5` fallos consecutivos por username, bloquea `BLOQUEO_SEGUNDOS=300`.
  Estado en un `dict` de **proceso** (visible a todas las peticiones). No audita;
  el fallo se audita en la capa de interfaz (`login.py`).

El choke point que activa `solo_lectura` y `contexto_tenant` desde la cookie de
sesión es `SessionContext.desde_storage()`, invocado por el guard central antes
de renderizar cada página protegida (ver `docs/architecture.md` §7.3–7.4).

---

## Trazabilidad y Auditoría (Cross-cutting concern)

Una característica vital de la capa de Servicios de ZECI Manager v2.0 es su trazabilidad invisible. Todos los métodos que causan mutaciones invocan el método protegido `_auditar()`.

```python
def _auditar(
    self,
    accion: AccionCambio, # CREATE, UPDATE, DELETE
    tabla: str,
    registro_id: int | None,
    datos_ant: dict | None,
    datos_nue: dict | None,
    usuario_id: int | None,
) -> None:
    # Registra qué campo cambió de qué valor anterior a qué valor nuevo
    ...
```

Esta inyección de la interfaz `IAuditoriaRepository` garantiza:
1. **Historial Completo:** Se pueden rastrear modificaciones de notas hechas de forma retroactiva.
2. **Desacoplamiento:** Los modelos de negocio puros no necesitan llenarse de atributos `created_at` o lógicas de log. 
3. **Facilidad de Testing:** En pruebas unitarias, se puede inyectar un repositorio simulado (Mock) sin afectar la evaluación de la regla de negocio.
