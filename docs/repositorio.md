# Capa de Repositorios (ZECI Manager v2.0)

Este documento describe la arquitectura y los detalles de implementación de la capa de repositorios en el proyecto **ZECI Manager v2.0**. La capa de repositorios actúa como un puente entre la lógica de dominio (casos de uso) y la infraestructura de almacenamiento (base de datos SQLite), siguiendo los principios de la **Arquitectura Limpia (Clean Architecture)**.

## 1. Arquitectura y Patrón Repositorio

El sistema implementa el **Patrón Repositorio** utilizando el concepto de Puertos y Adaptadores:
- **Puertos (Interfaces):** Definidos en la capa de dominio (`src/domain/ports/`). Son interfaces abstractas que establecen los contratos que deben cumplir las implementaciones de los repositorios. Esto garantiza que la lógica de negocio no dependa de los detalles de la base de datos.
- **Adaptadores (Implementaciones):** Definidos en la capa de infraestructura (`src/infrastructure/db/repositories/`). Son implementaciones concretas de los puertos que interactúan con la base de datos SQLite.

## 2. Puertos de Dominio (Interfaces)

Los puertos se encuentran en el directorio `src/domain/ports/` y definen las operaciones CRUD y consultas específicas para cada entidad del dominio.

| Puerto (Interfaz) | Entidad Asociada | Responsabilidad Principal |
| :--- | :--- | :--- |
| `IAcudienteRepository` | Acudiente | Gestión de familiares o tutores de los estudiantes. |
| `IAlertaRepository` | Alerta | Manejo de alertas generadas en el sistema (asistencia, convivencia, etc.). |
| `IAsignacionRepository` | Asignacion | Gestión de las relaciones entre docentes, asignaturas y grupos. |
| `IAsistenciaRepository` | Asistencia / AsistenciaDetalle | Registro y control de las inasistencias y retardos de los estudiantes. |
| `IAuditoriaRepository` | Auditoria | Registro de eventos, acciones y cambios importantes en el sistema (logs de auditoría). |
| `ICierreRepository` | CierrePeriodo | Manejo del historial y estado del cierre de periodos académicos. |
| `IConfiguracionRepository`| Configuracion | Lectura y actualización de los parámetros globales de la institución. |
| `IConvivenciaRepository` | Convivencia | Registro de incidentes disciplinarios y llamados de atención. |
| `IEstadisticosRepository` | Estadísticas | Generación de reportes y consultas agregadas (dashboard, promedios, etc.). |
| `IEstudianteRepository` | Estudiante | Operaciones CRUD y consultas sobre el listado de estudiantes. |
| `IEvaluacionRepository` | Evaluacion | Manejo de calificaciones, notas parciales y definitivas. |
| `IHabilitacionRepository` | Habilitacion | Registro de procesos de recuperación académica. |
| `IInfraestructuraRepository`| Grado, Grupo, Asignatura | Gestión de la estructura académica de la institución. |
| `IPeriodoRepository` | PeriodoAcademico | Administración de los periodos escolares (trimestres, semestres, etc.). |
| `IUsuarioRepository` | Usuario | Manejo de la información de docentes y administradores. |

*(Nota: Adicionalmente, el archivo `service_ports.py` define interfaces para servicios externos como `IAuthenticationService`, `IExporterService` e `INotificationService`, los cuales también siguen el patrón de puertos pero no son repositorios de base de datos directamente).*

## 3. Implementaciones SQLite (Adaptadores)

Las implementaciones concretas se ubican en `src/infrastructure/db/repositories/` y todas utilizan el motor de base de datos SQLite.

Cada repositorio implementa su interfaz correspondiente y se encarga de:
- Construir y ejecutar las consultas SQL.
- Mapear las tuplas obtenidas de SQLite a las entidades de dominio (modelos).
- Manejar las transacciones.

### Lista de Repositorios Implementados

- `SqliteAcudienteRepository`
- `SqliteAlertaRepository`
- `SqliteAsignacionRepository`
- `SqliteAsistenciaRepository`
- `SqliteAuditoriaRepository`
- `SqliteCierreRepository`
- `SqliteConfiguracionRepository`
- `SqliteConvivenciaRepository`
- `SqliteEstadisticosRepository`
- `SqliteEstudianteRepository`
- `SqliteEvaluacionRepository`
- `SqliteHabilitacionRepository`
- `SqliteInfraestructuraRepository`
- `SqlitePeriodoRepository`
- `SqliteUsuarioRepository`

## 4. Inyección de Dependencias

Para mantener el desacoplamiento, los repositorios no instancian sus propias conexiones a la base de datos. En su lugar, reciben un manejador de conexión o la conexión directamente a través de su constructor o mediante un contenedor de inyección de dependencias.

**Ejemplo teórico de inyección:**
```python
# En la capa de infraestructura/servicios
db_connection = DatabaseConnection("ruta/a/base_datos.sqlite")
estudiante_repo = SqliteEstudianteRepository(connection=db_connection)

# El servicio de dominio solo conoce la interfaz
estudiante_service = EstudianteService(repo=estudiante_repo)
```

## 5. Mapeo de Datos (SQL Raw vs ORM)

En ZECI Manager v2.0, los repositorios SQLite utilizan **SQL crudo (Raw SQL)** a través de la librería estándar de Python (`sqlite3`) en lugar de un ORM pesado. Esto ofrece:
- Mayor control sobre las consultas y optimizaciones precisas.
- Un mejor rendimiento general.
- Menos dependencias externas.

Los repositorios se encargan manualmente de mapear los resultados (filas) devueltos por la base de datos hacia las entidades o modelos de dominio (como DataClasses o Pydantic models).

## 6. Pruebas de los Repositorios

Las pruebas para la capa de repositorios (`tests/integration/`) se realizan como pruebas de integración. Utilizan una base de datos SQLite configurada en memoria (`:memory:`) para aislar el entorno, lo que permite verificar la sintaxis SQL, la correcta ejecución de las operaciones CRUD y el mapeo exacto de los datos a los modelos sin afectar los datos reales de la aplicación.
