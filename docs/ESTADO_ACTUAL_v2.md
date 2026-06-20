# Estado Actual — ZECI Manager v2.0

**Fecha de referencia:** Junio 2026
**Stack:** Python 3.x · NiceGUI 3.x · SQLite · Pydantic v2 · Bcrypt · JWT (stdlib)
**Estado del proyecto:** Activo / En desarrollo

---

## 1. Resumen Ejecutivo

ZECI Manager v2.0 es un **fork Git** de v1.0 (en producción) que reorganiza el código bajo Clean Architecture sin reescribir lógica de negocio. La base de datos SQLite se reutiliza sin cambios de esquema. El núcleo del dominio y los servicios están implementados; la capa de interfaz está mayoritariamente completa, incluyendo el módulo de convivencia (antes "en desarrollo").

La regla de dependencia se respeta en >95% del código: el dominio no importa NiceGUI, SQLite ni bcrypt. La inyección de dependencias se centraliza en un único `container.py` con lazy init.

---

## 2. Inventario de Componentes por Capa

### 2.1 Dominio (`src/domain/`)

**19 módulos de modelos** — Pydantic v2, sin imports externos:

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
| `habilitacion.py` | `Habilitacion` (FSM) + 4 DTOs |
| `infraestructura.py` | `AreaConocimiento`, `Asignatura`, `Grupo`, `Grado`, `Horario`, `Logro`, `Franja`, `PlantillaFranja`, `EscenarioHorario`, `DisponibilidadDocente`, `ConfigGeneracion`, `PlanEstudios`, `BloqueGeneradoDTO`, `MetricasCalidadDTO`, `ResultadoGeneracionDTO`, `VentanaGrupo`, `BloqueAnclado`, `FranjaReunion`, `LimitesDocente` + muchos DTOs |
| `nivelacion.py` | `ActividadNivelacion`, `NotaNivelacion`, `CierreNivelacion`, `CalculadorNivelacion` + 2 DTOs |
| `periodo.py` | `Periodo` (flag `cerrado`), `HitoPeriodo` (`TipoHito`) + 4 DTOs |
| `piar.py` | `PIAR` + 2 DTOs |
| `plan_mejoramiento.py` | `CortePlan`, `NotaCortePlan`, `ActividadPlan`, `NotaActividadPlan`, `CalculadorPlan` + 4 DTOs |
| `usuario.py` | `Usuario` (`Rol` Enum), `DocenteInfoDTO`, `AsignacionDocenteInfoDTO` + 4 DTOs |

> `infraestructura.py` es el módulo más extenso: cubre toda la infraestructura académica (asignaturas, grupos, grados, horarios, franjas, disponibilidad docente, plan de estudios, configuración y métricas de generación automática de horarios).

> `nivelacion.py` y `plan_mejoramiento.py` son módulos nuevos (Junio 2026). `plan_mejoramiento.py` reemplazó las entidades de plan que vivían en `habilitacion.py`.

**19 módulos de puertos** — interfaces ABC en `src/domain/ports/`:

`acudiente_repo`, `alerta_repo`, `asignacion_repo`, `asistencia_repo`, `auditoria_repo`, `cierre_repo`, `configuracion_repo`, `convivencia_repo`, `estadisticos_repo`, `estudiante_repo`, `evaluacion_repo`, `habilitacion_repo`, `infraestructura_repo`, `nivelacion_repo`, `periodo_repo`, `plan_mejoramiento_repo`, `siee_repo`, `usuario_repo`, `service_ports` (+ `__init__`).

`service_ports.py` define `IAuthenticationService`, `IExporterService` e `INotificationService`.

### 2.2 Servicios (`src/services/`)

23 servicios de aplicación implementados, todos agnósticos a SQLite y NiceGUI:

| Servicio | Dependencias del Container |
|---|---|
| `ConfiguracionService` | `configuracion_repo` |
| `UsuarioService` | `usuario_repo` + `auth_service` + `auditoria_repo` |
| `EstudianteService` | `estudiante_repo` + `acudiente_repo` + `auditoria_repo` |
| `PeriodoService` | `periodo_repo` + `configuracion_repo` + `auditoria_repo` |
| `InfraestructuraService` | `infraestructura_repo` |
| `PlanEstudiosService` | `infraestructura_repo` + `asignacion_svc_provider` (lazy para evitar circular) |
| `AsignacionService` | `asignacion_repo` + `periodo_repo` + `auditoria_repo` + `usuario_repo` + `infraestructura_repo` + `plan_estudios_service` |
| `EvaluacionService` | `evaluacion_repo` + `asignacion_repo` + `periodo_repo` + `auditoria_repo` + `siee_repo` |
| `AlertaService` | `alerta_repo` + `estadisticos_repo` |
| `AsistenciaService` | `asistencia_repo` + `alerta_repo` + `config_repo` |
| `CierreService` | `cierre_repo` + `evaluacion_repo` + `periodo_repo` + `config_repo` + `estudiante_repo` + `alerta_repo` + `auditoria_repo` (**7 dependencias**) |
| `HabilitacionService` | `habilitacion_repo` + `cierre_repo` + `config_repo` |
| `NivelacionService` | `nivelacion_repo` + `cierre_repo` + `config_repo` |
| `PlanMejoramientoService` | `plan_mejoramiento_repo` + `evaluacion_repo` + `estudiante_repo` |
| `ConvivenciaService` | `convivencia_repo` + `alerta_repo` |
| `EstadisticosService` | `estadisticos_repo` + `config_repo` + `evaluacion_repo` + `asistencia_repo` + `estudiante_repo` + `infraestructura_repo` |
| `InformeService` | `estadisticos_repo` + `exporter_service` + `estudiante_repo` |
| `AuditoriaService` | `auditoria_repo` |
| `AcudienteService` | `acudiente_repo` |
| `PreparacionHorarioService` | `infraestructura_repo` + `asignacion_repo` + `config_repo` + `periodo_repo` + `usuario_repo` + `plan_estudios_service` |
| `HorarioService` | `infraestructura_repo` + `asignacion_repo` + `usuario_service` + `plan_estudios_service` |
| `GeneradorHorarioService` | `infraestructura_repo` + `asignacion_repo` + `usuario_service` + `horario_service` + `infraestructura_service` + `plan_estudios_service` |

> Los 7 servicios de horarios (`InfraestructuraService`, `PlanEstudiosService`, `PreparacionHorarioService`, `HorarioService`, `GeneradorHorarioService`) son nuevos en Junio 2026.

> `NivelacionService` y `PlanMejoramientoService` también son nuevos.

### 2.3 Infraestructura (`src/infrastructure/`)

| Submódulo | Componentes |
|---|---|
| `db/repositories/` | 20 implementaciones SQLite con paridad 1:1 respecto a los puertos |
| `db/schema.py` | DDL completo (~49 KB) |
| `db/seed.py` | Datos semilla (~40 KB) |
| `db/queries.py` | Helpers `fetch_df` / `execute` (legado, uso exclusivo de repositorios) |
| `db/connection.py` | Pool de conexiones SQLite con soporte WAL |
| `auth/` | `BcryptAuthService`, `JWTHandler` (stdlib), `bcrypt_auth.py` |
| `context/` | `ContextInitializer`, `session_context.py` |
| `exporters/` | `ExcelExporter` (stub), `NullExporter`, `ExporterFactory`, stub PDF |
| `notifications/` | `LogNotificationService`, `NullNotificationService` |

Repositorios presentes: `sqlite_acudiente_repo`, `sqlite_alerta_repo`, `sqlite_asignacion_repo`, `sqlite_asistencia_repo`, `sqlite_auditoria_repo`, `sqlite_cierre_repo`, `sqlite_configuracion_repo`, `sqlite_convivencia_repo`, `sqlite_estadisticos_repo`, `sqlite_estudiante_repo`, `sqlite_evaluacion_repo`, `sqlite_habilitacion_repo`, `sqlite_infraestructura_repo`, `sqlite_nivelacion_repo` *(nuevo)*, `sqlite_periodo_repo`, `sqlite_plan_mejoramiento_repo` *(nuevo)*, `sqlite_siee_repo` *(nuevo)*, `sqlite_usuario_repo`.

### 2.4 Interfaz (`src/interface/`)

**37 páginas/widgets NiceGUI** implementados:

| Sección | Páginas |
|---|---|
| Raíz | `login.py`, `inicio.py` (dashboard global, ~29 KB) |
| `pages/admin/` | `asignaciones`, `asignaturas`, `configuracion_institucion`, `configuracion_sie`, `disponibilidad_docente` *(nuevo)*, `grupos`, `plan_estudios` *(nuevo)*, `salas` *(nuevo)*, `usuarios` |
| `pages/academico/` | `estudiantes`, `horarios_hub` *(nuevo)*, `parrilla_widget` *(nuevo, widget)*, `plantilla_editor_widget` *(nuevo, widget)*, `registro_asistencia`, `tablero_estadisticos` |
| `pages/convivencia/` | `comportamiento` *(nuevo)*, `notas_convivencia` *(nuevo)*, `observaciones` *(nuevo)* |
| `pages/evaluacion/` | `cierre_anio`, `cierre_periodo`, `configuracion_evaluacion`, `habilitaciones`, `planes_mejoramiento`, `planilla_notas` |
| `pages/informes/` | `boletin_anual`, `boletin_periodo`, `consolidado_asistencia`, `consolidado_notas`, `estadisticos` |

> El módulo de convivencia pasó de "en desarrollo" a completamente implementado con 3 páginas.

**Design system "Andes Minimal v2"** (`src/interface/design/`):

- `tokens.py`, `theme.py`, `layout.py`
- `styles/reset.css` — reset y variables CSS base
- `components/` — **16 componentes** (antes 6):
  - Originales: `context_bar`, `data_table`, `page_header`, `stat_card`, `status_badge`, `confirm_dialog`
  - Nuevos: `base_form`, `buttons`, `confirmation_card`, `context_selector`, `empty_state`, `form_dialog`, `performance_indicator`, `pipeline`, `skeleton_loader`, `toast`

---

## 3. Composition Root (`container.py`)

Singleton lazy por clave de caché con:

- `_cache: dict[str, Any] = {}` — garantía de singleton por proceso.
- `Container.reset()` — limpia el caché para tests de integración.
- `Container.diagnostico()` — ejecuta en arranque (`is_development`) intentando instanciar todos los servicios (22 métodos) y reportando errores antes del primer request.
- Imports lazy dentro de cada método factory — sin carga anticipada de módulos.

> `PlanEstudiosService` usa un `asignacion_svc_provider` como callable lazy para romper la dependencia circular `plan_estudios ↔ asignacion`.

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
| **R5** | 🟡 Media | Clases CSS de tablero (`tablero-badge-*`, `tablero-row-riesgo`) referenciadas en Python pero no definidas en `styles/reset.css` | `reset.css` |
| **R6** | 🟡 Media | `DesempenoColors.para_nota()` en `tokens.py` contiene umbrales de calificación (regla de negocio) en capa de presentación | `tokens.py` → `domain/models/evaluacion.py` |
| **R7** | 🟡 Media | `app.storage.user` sin atomicidad — posible race condition en callbacks NiceGUI concurrentes | `SessionContext.guardar()` |
| **R8** | 🟡 Media | Tests unitarios para los servicios están incompletos (`tests/unit/services/`) | `tests/unit/services/` |
| **R9** | 🟢 Baja | Exportadores Excel y PDF son stubs vacíos | `src/infrastructure/exporters/` |

---

## 6. Historial de Correcciones Aplicadas

| ID | Fecha | Acción |
|---|---|---|
| ~~C1~~ | 2026-05 | `TypeError: 'bool' object is not callable` en `tablero_estadisticos.py` (propiedad `contexto_completo` llamada con `()`) |
| ~~C2~~ | 2026-05 | Paleta ECharts refactorizada a bloque `_EC_*` centralizado en `tablero_estadisticos.py` |
| ~~C3~~ | 2026-05 | `cellStyle` con colores inline migrado a `cellClass`/`rowClassRules` en ag-Grid |
| ~~C4~~ | 2026-05 | Clases de estado vacío estandarizadas a `tablero-empty-hint` |
| ~~C5~~ | 2026-06 | Módulo convivencia implementado completo (3 páginas) |
| ~~C6~~ | 2026-06 | `plan_mejoramiento.py` separado de `habilitacion.py` como módulo independiente |
| ~~C7~~ | 2026-06 | Sistema de horarios implementado: 5 servicios nuevos + módulo de preparación y generación automática |
| ~~C8~~ | 2026-06 | Design system expandido: 10 componentes nuevos en `src/interface/design/components/` |
| ~~C9~~ | 2026-06 | `reset.css` separado del CSS principal |

---

## 7. Cobertura de Tests

| Tipo | Ubicación | Estado |
|---|---|---|
| Integración repositorios | `tests/integration/test_repositories.py` (41.8 KB) | Cobertura significativa |
| Smoke tests Container | `tests/test_container.py` | Existente |
| Unitarios servicios | `tests/unit/services/` | Incompleto (pendiente R8) |
| Generación de schema | `tests/integration/generate_schema.py` | Existente |
