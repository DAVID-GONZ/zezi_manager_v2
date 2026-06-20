# Capa de Modelos de Dominio (Entidades Pydantic)

Este documento describe las entidades que conforman el núcleo de la lógica de negocio en **ZECI Manager v2.0**. Estas entidades están implementadas en `src/domain/models/` y utilizan **Pydantic v2** para garantizar la validación estricta de tipos y datos en tiempo de ejecución.

## Principios de Diseño

De acuerdo con la Arquitectura Limpia adoptada por el proyecto:
1. **Agnósticos a la Infraestructura:** Los modelos son clases puras de Python y Pydantic. No heredan de ORMs (como SQLAlchemy o SQLModel) ni contienen metadatos de persistencia (como nombres de tablas o relaciones SQL).
2. **Validación Autónoma:** Las reglas de integridad intrínsecas se validan en los propios modelos (ej. validar que un correo tenga el formato correcto, o que una nota no sea negativa).
3. **Desacoplamiento:** No importan paquetes externos innecesarios. Su única dependencia fuerte es `pydantic`.

## Entidades Principales

El sistema está compuesto por **19 módulos de dominio** que definen las entidades principales, agregados y objetos de valor (Value Objects).

### 1. Acudiente (`acudiente.py`)
Maneja la información de los padres, tutores o responsables legales de los estudiantes.
- Valida la relación filial y almacena datos de contacto crítico para el envío de notificaciones y alertas.

### 2. Alerta (`alerta.py`)
Representa notificaciones generadas automáticamente o de forma manual por eventos disciplinarios, de inasistencia o riesgo académico.
- Contiene reglas de nivel de severidad (`ADVERTENCIA`, `CRITICA`).

### 3. Asignacion (`asignacion.py`)
Entidad relacional que une a un Docente con una Asignatura y un Grupo en un periodo lectivo. Es el pivote sobre el cual los docentes gestionan notas y asistencias.

### 4. Asistencia (`asistencia.py`)
Registra las faltas de asistencia y retardos.
- Diferencia entre ausencias justificadas e injustificadas. La lógica del dominio utiliza esta entidad para calcular automáticamente el porcentaje de asistencia de un estudiante.

### 5. Auditoria (`auditoria.py`)
Modelos inmutables de registro (logs). 
- Permiten trazar cambios (quién, cuándo y qué se modificó) para mantener la transparencia en la manipulación de notas y datos académicos.

### 6. Cierre (`cierre.py`)
Contiene los agregados de `CierrePeriodo` y `CierreAnio`.
- Entidades complejas que consolidan el estado académico de un estudiante en un punto del tiempo, preservando las notas definitivas calculadas para prevenir alteraciones retroactivas.

### 7. Configuracion (`configuracion.py`)
Entidad Singleton que almacena las reglas globales de la institución.
- Define el número de periodos, el sistema institucional de evaluación (ej. nota mínima aprobatoria) y configuración de la escala de desempeños (Bajo, Básico, Alto, Superior).

### 8. Convivencia (`convivencia.py`)
Registra los reportes disciplinarios y llamados de atención.
- Almacena faltas y observaciones, alimentando directamente a los modelos de alerta.

### 9. Estudiante (`estudiante.py`)
Representa el perfil completo del alumno.
- Administra el estado de la matrícula (Activo, Retirado) y actúa como raíz del agregado (Aggregate Root) para vincular calificaciones, asistencia y convivencia.

### 10. Evaluacion (`evaluacion.py`)
Incluye las categorías (ej. Ser, Saber, Hacer), actividades (exámenes, talleres) y las calificaciones puntuales.
- Valida que las calificaciones numéricas no superen la escala permitida y que las categorías evaluativas de un periodo no excedan el 100%.

### 11. Habilitacion (`habilitacion.py`)
Maneja los procesos de recuperación de fin de año o finales de periodo.
- Contiene `Habilitacion` (examen de recuperación, FSM) y `PlanMejoramiento` (plan narrativo de seguimiento obligatorio según Decreto 1290). El plan narrativo documenta dificultades, actividades propuestas y fechas de seguimiento; se diferencia del Plan de Mejoramiento cuantitativo del módulo `plan_mejoramiento.py`.

### 12. Infraestructura Académica (`infraestructura.py`)
El módulo más extenso del dominio. Cubre toda la infraestructura del plantel y el subsistema de horarios:
- Entidades base: `AreaConocimiento`, `Asignatura`, `Grupo`, `Grado`, `Sala`, `Horario`, `Logro`
- Subsistema de plantillas y franjas: `PlantillaFranja`, `Franja`, `EscenarioHorario`
- Subsistema de generación automática: `DisponibilidadDocente`, `ConfigGeneracion`, `PlanEstudios`, `VentanaGrupo`, `BloqueAnclado`, `FranjaReunion`, `LimitesDocente`
- DTOs de resultado: `BloqueGeneradoDTO`, `MetricasCalidadDTO`, `ResultadoGeneracionDTO`, `HorarioInfo`, `HorarioEstadisticasDTO`

### 13. Periodo (`periodo.py`)
Define los lapsos temporales del ciclo lectivo (ej. Primer Periodo, Segundo Periodo).
- Su estado (`ACTIVO`, `CERRADO`) controla rígidamente si se pueden modificar o ingresar nuevas calificaciones.

### 14. PIAR (`piar.py`)
Plan Individual de Ajustes Razonables.
- Modelos para estudiantes con necesidades educativas especiales, documentando los ajustes curriculares requeridos y el seguimiento pedagógico.

### 15. Usuario (`usuario.py`)
Representa a los actores del sistema (Docentes, Administrativos, Directores).
- Gestiona datos de identidad, roles de acceso y credenciales (sin manejar directamente los hashes de contraseñas, que es tarea del servicio de autenticación).

### 16. DTOs (`dtos.py`)
Objetos de Transferencia de Datos.
- Aunque no son "Entidades" estables en BD, son modelos Pydantic usados puramente para transportar datos compuestos entre la UI y los Servicios, o entre Servicios, garantizando tipos seguros durante las peticiones complejas (ej. reportes, listados enriquecidos).

### 17. Nivelación (`nivelacion.py`) *(Nuevo — Junio 2026)*
Proceso post-cierre de período obligatorio según Decreto 1290. La institución debe ofrecer actividades de recuperación documentadas a estudiantes con desempeño bajo.
- `ActividadNivelacion` — columna compartida (una actividad aplica a todos los estudiantes bajo-desempeño de una asignación+periodo).
- `NotaNivelacion` — celda: nota de un estudiante en una actividad.
- `CierreNivelacion` — su existencia indica que la nivelación está cerrada (inmutable).
- `CalculadorNivelacion` — utilidad stateless para calcular nota definitiva ponderada.
- La nota definitiva se computa, no se almacena, para evitar redundancia.

### 18. Plan de Mejoramiento Cuantitativo (`plan_mejoramiento.py`) *(Nuevo — Junio 2026)*
Sistema de plan de mejoramiento basado en cortes con notas ponderadas (distinto del plan narrativo de `habilitacion.py`).
- `CortePlan` — registro del corte de un periodo para una asignación; agrupa a todos los estudiantes en-plan.
- `NotaCortePlan` — estado por estudiante (`SIN_PLAN`, `EN_PLAN`, `APROBADO`, `REPROBADO`).
- `ActividadPlan` — actividades del plan con peso (columna compartida por todos los en-plan).
- `NotaActividadPlan` — nota de un estudiante en una actividad del plan (celda).
- `CalculadorPlan` — utilidades de cálculo (nota al corte, umbral, nota definitiva).

### 19. PIAR (`piar.py`)
*(Existente, refactorizado como módulo independiente)*

Ver entrada 14 — el módulo fue renumerado al incorporar los nuevos módulos 17 y 18.

## Consideraciones de Mutabilidad

Por defecto, la mayoría de los modelos en ZECI Manager v2.0 están diseñados para ser mutables (`frozen=False` en Pydantic), lo que permite a los **Servicios de Aplicación** cambiar el estado de las entidades antes de enviarlas al repositorio para su persistencia. Sin embargo, entidades de registro histórico como `Auditoria` son tratadas semánticamente como objetos inmutables.
