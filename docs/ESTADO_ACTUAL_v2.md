# Estado Actual — ZECI Manager v2.0

**Fecha de referencia:** Mayo 2026  
**Stack:** Python 3.x · NiceGUI 3.x · SQLite · Pydantic v2 · Bcrypt · JWT (stdlib)  
**Estado del proyecto:** Activo / En desarrollo

---

## 1. Resumen Ejecutivo

ZECI Manager v2.0 es un **fork Git** de v1.0 (en producción) que reorganiza el código bajo Clean Architecture sin reescribir lógica de negocio. La base de datos SQLite se reutiliza sin cambios de esquema. El nucleo del dominio y los servicios están implementados; la capa de interfaz está parcialmente completada.

La regla de dependencia se respeta en >95% del código: el dominio no importa NiceGUI, SQLite ni bcrypt. La inyección de dependencias se centraliza en un único `container.py` con lazy init.

---

## 2. Inventario de Componentes por Capa

### 2.1 Dominio (`src/domain/`)

**17 módulos de modelos** — Pydantic v2, sin imports externos:

| Módulo | Entidades principales |
|---|---|
| `acudiente.py` | `Acudiente`, `EstudianteAcudiente` + 4 DTOs |
| `alerta.py` | `ConfiguracionAlerta`, `Alerta` + 3 DTOs |
| `asignacion.py` | `Asignacion`, `AsignacionInfo` + 3 DTOs |
| `asistencia.py` | `EstadoAsistencia` (Enum), `ControlDiario`, `ResumenAsistenciaDTO` + 4 DTOs |
| `auditoria.py` | `EventoSesion`, `RegistroCambio`, `AccionCambio` (Enum) + 3 DTOs |
| `cierre.py` | `CierrePeriodo`, `CierreAnio`, `PromocionAnual` (`EstadoPromocion` FSM) + 5 DTOs |
| `configuracion.py` | `ConfiguracionAnio`, `NivelDesempeno`, `CriterioPromocion` + 5 DTOs |
| `convivencia.py` | `ObservacionPeriodo`, `RegistroComportamiento`, `NotaComportamiento` + 5 DTOs |
| `dtos.py` | `ContextoAcademicoDTO`, `DashboardMetricsDTO`, `MatriculaMasivaDTO`, `RespuestaOperacionDTO` + 3 DTOs |
| `estudiante.py` | `Estudiante` (FSM matrícula), `EstudianteResumenDTO` + 4 DTOs |
| `evaluacion.py` | `Categoria`, `Actividad`, `Nota`, `PuntosExtra`, `CalculadorNotas` + 7 DTOs |
| `habilitacion.py` | `Habilitacion` (FSM), `PlanMejoramiento` (FSM) + 6 DTOs |
| `infraestructura.py` | `Grupo`, `Asignatura`, `AreaConocimiento`, `Horario`, `Logro`, `HorarioInfo` + 7 DTOs |
| `periodo.py` | `Periodo` (flag `cerrado`), `HitoPeriodo` (`TipoHito`) + 4 DTOs |
| `piar.py` | `PIAR` + 2 DTOs |
| `usuario.py` | `Usuario` (`Rol` Enum), `DocenteInfoDTO`, `AsignacionDocenteInfoDTO` + 4 DTOs |

**17 módulos de puertos** — interfaces ABC en `src/domain/ports/`:

`acudiente_repo`, `alerta_repo`, `asignacion_repo`, `asistencia_repo`, `auditoria_repo`, `cierre_repo`, `configuracion_repo`, `convivencia_repo`, `estadisticos_repo`, `estudiante_repo`, `evaluacion_repo`, `habilitacion_repo`, `infraestructura_repo`, `periodo_repo`, `usuario_repo`, `service_ports` (+ `__init__`).

`service_ports.py` define `IAuthenticationService`, `IExporterService` e `INotificationService`.

### 2.2 Servicios (`src/services/`)

16 servicios de aplicación implementados, todos agnósticos a SQLite y NiceGUI:

| Servicio | Dependencias del Container |
|---|---|
| `ConfiguracionService` | `configuracion_repo` |
| `UsuarioService` | `usuario_repo` + `auth_service` + `auditoria_repo` |
| `EstudianteService` | `estudiante_repo` + `acudiente_repo` + `auditoria_repo` |
| `PeriodoService` | `periodo_repo` + `configuracion_repo` + `auditoria_repo` |
| `AsignacionService` | `asignacion_repo` + `periodo_repo` + `auditoria_repo` |
| `EvaluacionService` | `evaluacion_repo` + `asignacion_repo` + `periodo_repo` + `auditoria_repo` |
| `AlertaService` | `alerta_repo` + `estadisticos_repo` |
| `AsistenciaService` | `asistencia_repo` + `alerta_repo` + `config_repo` |
| `CierreService` | `cierre_repo` + `evaluacion_repo` + `periodo_repo` + `config_repo` + `estudiante_repo` + `alerta_repo` + `auditoria_repo` (**7 dependencias**) |
| `HabilitacionService` | `habilitacion_repo` + `cierre_repo` + `config_repo` |
| `ConvivenciaService` | `convivencia_repo` + `alerta_repo` |
| `EstadisticosService` | `estadisticos_repo` + `config_repo` |
| `InformeService` | `estadisticos_repo` + `exporter_service` |
| `AuditoriaService` | `auditoria_repo` |
| `AcudienteService` | `acudiente_repo` |
| *(convivencia)* | *(en desarrollo)* |

> `AuditoriaService` existe y está registrado en el Container pero **no está exportado en `src/services/__init__.py`** (gap pendiente — ver §5).

### 2.3 Infraestructura (`src/infrastructure/`)

| Submódulo | Componentes |
|---|---|
| `db/repositories/` | 16 implementaciones SQLite con paridad 1:1 respecto a los puertos |
| `db/schema.py` | DDL completo (~49 KB) |
| `db/seed.py` | Datos semilla (~40 KB) |
| `db/queries.py` | Helpers `fetch_df` / `execute` (legado, uso exclusivo de repositorios) |
| `db/connection.py` | Pool de conexiones SQLite con soporte WAL |
| `auth/` | `BcryptAuthService`, `JWTHandler` (stdlib), `bcrypt_auth.py` |
| `context/` | `ContextInitializer`, `session_context.py` |
| `exporters/` | `ExcelExporter` (stub), `NullExporter`, `ExporterFactory`, stub PDF |
| `notifications/` | `LogNotificationService`, `NullNotificationService` |

### 2.4 Interfaz (`src/interface/`)

**23+ páginas NiceGUI** implementadas:

| Sección | Páginas |
|---|---|
| Raíz | `login.py`, `inicio.py` (dashboard, ~29 KB) |
| `pages/admin/` | `asignaciones`, `asignaturas`, `configuracion_institucion`, `configuracion_sie`, `grupos`, `usuarios` |
| `pages/academico/` | `asistencia`, `dashboard`, `estudiantes`, `horarios`, `tablero_estadisticos` |
| `pages/convivencia/` | En desarrollo |
| `pages/evaluacion/` | `cierre_anio`, `cierre_periodo`, `configuracion_evaluacion`, `habilitaciones`, `planes_mejoramiento`, `planilla_notas` |
| `pages/informes/` | `boletin_anual`, `boletin_periodo`, `consolidado_asistencia`, `consolidado_notas`, `estadisticos` |

**Design system "Andes Minimal v2"** (`src/interface/design/`): `tokens.py`, `styles.css` (~35 KB con variables CSS en `:root`), `theme.py`, `layout.py`, `components/`.

---

## 3. Composition Root (`container.py`)

Singleton lazy por clave de caché con:

- `_cache: dict[str, Any] = {}` — garantía de singleton por proceso.
- `Container.reset()` — limpia el caché para tests de integración.
- `Container.diagnostico()` — ejecuta en arranque (`is_development`) intentando instanciar todos los servicios y reportando errores antes del primer request.
- Imports lazy dentro de cada método factory — sin carga anticipada de módulos.

---

## 4. Sistema de Autenticación y Contexto

**Autenticación:** `BcryptAuthService` gestiona login. `JWTHandler` (stdlib HS256, 8 h de expiración) está implementado pero inactivo en v2.x — se activa en v3.0 con la API REST.

**Contexto de sesión:** `ContextInitializer` resuelve al login el año activo, período activo, grupo y asignación del usuario. Todos sus métodos son `@staticmethod`. `refrescar_si_invalido(ctx)` detecta contextos desactualizados (periodo cerrado, asignación removida) y los re-inicializa sin forzar logout.

---

## 5. Inconsistencias Pendientes

| ID | Severidad | Problema | Archivo |
|---|---|---|---|
| **R1** | 🔴 Alta | `AuditoriaService` no está en `__all__` de `src/services/__init__.py` | `src/services/__init__.py` |
| **R2** | 🔴 Alta | `JWT_SECRET` inseguro emite `warnings.warn()` en producción — debería ser `ValueError` | `config.py` |
| **R3** | 🔴 Alta | Verificar que `inicio.py` usa `Container.auditoria_service()` en lugar de `auditoria_repo()` directamente | `src/interface/pages/inicio.py` |
| **R4** | 🔴 Alta | `ContextInitializer` llama a `Container.asignacion_repo()` y `Container.periodo_repo()` directamente en lugar de sus servicios | `src/infrastructure/context/context_initializer.py` |
| **R5** | 🟡 Media | Clases CSS de tablero (`tablero-badge-*`, `tablero-row-riesgo`) referenciadas en Python pero no definidas en `styles.css` | `styles.css` |
| **R6** | 🟡 Media | `DesempenoColors.para_nota()` en `tokens.py` contiene umbrales de calificación (regla de negocio) en capa de presentación | `tokens.py` → `domain/models/evaluacion.py` |
| **R7** | 🟡 Media | `app.storage.user` sin atomicidad — posible race condition en callbacks NiceGUI concurrentes | `SessionContext.guardar()` |
| **R8** | 🟡 Media | Tests unitarios para los 16 servicios están incompletos (`tests/unit/services/`) | `tests/unit/services/` |
| **R9** | 🟢 Baja | Exportadores Excel y PDF son stubs vacíos (0 bytes) | `src/infrastructure/exporters/` |

---

## 6. Correcciones Aplicadas (2026-05-18)

| ID | Acción |
|---|---|
| ~~C1~~ | `TypeError: 'bool' object is not callable` en `tablero_estadisticos.py` (propiedad `contexto_completo` llamada con `()`) |
| ~~C2~~ | Paleta ECharts refactorizada a bloque `_EC_*` centralizado en `tablero_estadisticos.py` |
| ~~C3~~ | `cellStyle` con colores inline migrado a `cellClass`/`rowClassRules` en ag-Grid |
| ~~C4~~ | Clases de estado vacío estandarizadas a `tablero-empty-hint` |

---

## 7. Cobertura de Tests

| Tipo | Ubicación | Estado |
|---|---|---|
| Integración repositorios | `tests/integration/test_repositories.py` (41.8 KB) | Cobertura significativa |
| Smoke tests Container | `tests/test_container.py` | Existente |
| Unitarios servicios | `tests/unit/services/` | Incompleto (pendiente R8) |
| Generación de schema | `tests/integration/generate_schema.py` | Existente |
