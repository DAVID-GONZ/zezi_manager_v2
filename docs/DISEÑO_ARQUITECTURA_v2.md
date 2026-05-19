# Diseño de Arquitectura — ZECI Manager v2.0

**Versión:** Mayo 2026  
**Stack:** Python 3.x · NiceGUI 3.x · SQLite · Pydantic v2 · Bcrypt · JWT (stdlib)

---

## 1. Estrategia de Construcción

v2.0 es un **fork Git** de v1.0. No reescribe lógica — la reorganiza. Cada función SQL, cada cálculo de negocio y cada componente UI ya existe en v1.0; el trabajo consiste en mover, envolver o sustituir tipos.

| Operación | Volumen | Descripción |
|---|---|---|
| **MOVER** | ~70% | Cortar código de `pages/` o `modules/` y pegarlo en el repositorio o servicio correcto sin modificar la lógica. |
| **ENVOLVER** | ~20% | Crear una clase que implementa una interfaz y delega internamente al código legacy (`AppStateContextAdapter`, `AuthenticationService`). |
| **SUSTITUIR** | ~8% | Cambiar el tipo que viaja entre capas: donde había `dict` o `DataFrame`, ahora viaja una entidad Pydantic. Solo cambia la firma y los accesos por clave. |
| **CREAR** | ~2% | Código genuinamente nuevo: interfaces ABC, `container.py`, `FakeRepository` para tests, `NullExporter`. |

La base de datos SQLite se reutiliza sin cambios de esquema.

---

## 2. Principio de Dependencias

```
Interfaz → Servicios → Dominio ← Infraestructura
```

- El dominio no importa NiceGUI, SQLite ni pandas.
- La infraestructura implementa los contratos del dominio.
- La interfaz consume servicios a través del Container; nunca accede a repositorios directamente.
- `container.py` es el único lugar donde se instancian repositorios y servicios.

NiceGUI gestiona su propia instancia FastAPI. No se crea un `FastAPI()` adicional en v2.0 — eso queda para v3.0.

---

## 3. Capa de Dominio (`src/domain/`)

Pure Python. Sin imports externos.

### 3.1 Modelos

16 módulos de entidades Pydantic v2. Características generales:

- Los modelos de entidad tienen `field_validator` para invariantes (documentos, fechas, rangos de nota).
- Los modelos que representan máquinas de estado (`Estudiante`, `Habilitacion`, `PlanMejoramiento`, `PromocionAnual`, `Periodo`) exponen métodos de dominio que realizan la transición y validan la coherencia antes de persistir.
- Los modelos "Info" (`AsignacionInfo`, `HorarioInfo`) no se persisten: los construye el repositorio con JOINs para evitar que las páginas hagan queries adicionales.
- Los DTOs de creación (`NuevoXDTO`) tienen un método `to_entidad()` que construye el modelo de dominio correspondiente.
- Los DTOs de actualización (`ActualizarXDTO`) tienen un método `aplicar_a(entidad)` que aplica solo los campos no-`None`.

**Módulos de modelos:**

| Módulo | Entidades clave | Notas |
|---|---|---|
| `estudiante.py` | `Estudiante`, `EstadoMatricula` | FSM: ACTIVO → RETIRADO → REACTIVADO |
| `evaluacion.py` | `Categoria`, `Actividad`, `Nota`, `PuntosExtra`, `CalculadorNotas` | Pesos en escala 0–1; `CalculadorNotas` es stateless |
| `cierre.py` | `CierrePeriodo`, `CierreAnio`, `PromocionAnual` | Registro de libro mayor — inmutable post-creación |
| `asistencia.py` | `ControlDiario`, `EstadoAsistencia` | `ResumenAsistenciaDTO` calculado por repositorio con `GROUP BY` |
| `periodo.py` | `Periodo`, `HitoPeriodo` | Flag `cerrado` como candado de evaluación; `TipoHito` enum |
| `configuracion.py` | `ConfiguracionAnio`, `NivelDesempeno`, `CriterioPromocion` | `NivelDesempeno.clasifica(nota)` resuelve el nivel sin consultar BD |
| `habilitacion.py` | `Habilitacion`, `PlanMejoramiento` | FSM con `_validar_transicion()` interno |
| `auditoria.py` | `EventoSesion`, `RegistroCambio` | `RegistroCambio.desde_legacy()` compatibiliza v1.0 |
| `convivencia.py` | `ObservacionPeriodo`, `RegistroComportamiento` | `es_publica` controla visibilidad en boletín |
| `dtos.py` | `ContextoAcademicoDTO`, `DashboardMetricsDTO` | `ContextoAcademicoDTO` reemplaza `AppState` global de v1.0 |
| `infraestructura.py` | `Grupo`, `Asignatura`, `Horario`, `Logro`, `HorarioInfo` | Invariante: `hora_inicio < hora_fin` en `model_validator` |
| `asignacion.py` | `Asignacion`, `AsignacionInfo` | `display_completo` para UI sin queries adicionales |
| `usuario.py` | `Usuario`, `Rol`, `DocenteInfoDTO` | La `password_hash` nunca entra al modelo |
| `acudiente.py` | `Acudiente`, `EstudianteAcudiente` | Un acudiente puede estar vinculado a varios estudiantes |
| `alerta.py` | `ConfiguracionAlerta`, `Alerta` | `resolver()` es el único método que muta estado; inmutable tras resolución |
| `piar.py` | `PIAR` | Instrumento pedagógico, no diagnóstico médico |

### 3.2 Puertos

16 interfaces ABC en `src/domain/ports/` — un archivo por módulo, sin implementación.

Adicionalmente, `service_ports.py` define las interfaces de servicios externos:

```python
# src/domain/ports/service_ports.py
class IAuthenticationService(ABC):
    @abstractmethod def hashear_password(self, plain: str) -> str: ...
    @abstractmethod def verificar_password(self, plain: str, hashed: str) -> bool: ...
    @abstractmethod def cambiar_password(self, ...) -> bool: ...
    @abstractmethod def resetear_password(self, ...) -> str: ...

class IExporterService(ABC):
    @abstractmethod def exportar_excel(self, datos, tipo: str) -> bytes: ...
    @abstractmethod def exportar_pdf(self, datos, tipo: str) -> bytes: ...
    @abstractmethod def exportar_csv(self, datos, tipo: str) -> bytes: ...

class INotificationService(ABC):
    @abstractmethod def notificar_acudiente(self, ...) -> None: ...
    @abstractmethod def notificar_docente(self, ...) -> None: ...
    @abstractmethod def notificar_directivos(self, ...) -> None: ...
```

La existencia de `service_ports.py` permite abstraer también los servicios, no solo los repositorios.

---

## 4. Capa de Servicios (`src/services/`)

16 servicios de aplicación. Sin SQL, sin NiceGUI, sin pandas.

**Principios:**
- Reciben primitivos o DTOs Pydantic; retornan entidades de dominio.
- La lógica intrínseca (cambios de estado, transiciones) pertenece a las entidades.
- El servicio orquesta: Buscar → Llamar entidad → Persistir → Auditar.
- Todos los métodos mutadores invocan `_auditar()` al final.

**Patrón de auditoría transversal:**

```python
def _auditar(
    self,
    accion: AccionCambio,   # CREATE | UPDATE | DELETE
    tabla: str,
    registro_id: int | None,
    datos_ant: dict | None,
    datos_nue: dict | None,
    usuario_id: int | None,
) -> None:
    # Construye RegistroCambio y delega en IAuditoriaRepository
```

**Servicios principales:**

`CierreService` — el más complejo (7 dependencias directas). Consolida notas por estudiante, determina `NivelDesempeno`, dispara alertas de riesgo automáticas y gestiona decisiones de promoción (`PENDIENTE → PROMOVIDO | REPROBADO | CONDICIONAL`).

`EvaluacionService` — garantiza que la suma de pesos de categorías no exceda 1.0 y que notas solo se ingresen en actividades con estado `PUBLICADA`.

`AsistenciaService` y `ConvivenciaService` — detectan superación de umbrales configurados e instancian alertas automáticas sin intervención del docente.

`EstadisticosService` — solo lectura; delega agrupaciones a queries optimizadas en el repositorio. Sin DataFrames en esta capa.

`InformeService` — no accede a BD directamente; toma consolidados de `EstadisticosService` y los pasa al `IExporterService`.

---

## 5. Capa de Infraestructura (`src/infrastructure/`)

Los helpers `fetch_df` y `execute` de `src/db/queries.py` **no se reemplazan** en v2.0 — los repositorios los siguen usando internamente. Pandas vive en esta capa; no sube a servicios ni vistas.

### 5.1 Repositorios SQLite

16 implementaciones en `src/infrastructure/db/repositories/`. Patrón uniforme:

1. Implementan su interfaz de puerto correspondiente.
2. Usan `fetch_df` / `execute` de `src/db/queries.py`.
3. Mapean filas de SQLite a entidades Pydantic con `Entidad(**df.iloc[0].to_dict())` o `[Entidad(**r) for r in df.to_dict("records")]`.
4. Los modelos "Info" se construyen aquí desde consultas con JOINs.
5. Los resúmenes agregados (`ResumenAsistenciaDTO`, `DashboardMetricsDTO`) se calculan con `GROUP BY` en SQL — no con `groupby` de pandas en el servicio.

### 5.2 Autenticación

- `BcryptAuthService` implementa `IAuthenticationService`.
- `JWTHandler` (stdlib HS256, expiración 8 h) está implementado pero **inactivo** en v2.x — preparado para la API REST de v3.0.

### 5.3 Contexto de Sesión

`ContextInitializer` resuelve al momento del login:
- Año académico activo (via `ConfiguracionService`).
- Período activo (con fallback al primer período no cerrado).
- Grupo y asignación del docente; solo grupo para directores.

Todos sus métodos son `@staticmethod`. `refrescar_si_invalido(ctx)` detecta contextos desactualizados y los re-inicializa sin forzar logout.

`ContextoAcademicoDTO` es **inmutable**: cada cambio en la UI crea un nuevo DTO en lugar de mutar un estado global como lo hacía `AppState` en v1.0.

### 5.4 Exportadores

`ExporterFactory` selecciona la implementación correcta en arranque:
- `ExcelExporter` (openpyxl) — actualmente stub.
- `NullExporter` — patrón Null Object; lanza `RuntimeError` descriptivo si se invoca.
- `NullNotificationService` — análogo para notificaciones.

---

## 6. Composition Root (`container.py`)

Singleton lazy por clave de caché:

```python
class Container:
    _cache: dict[str, Any] = {}

    @classmethod
    def _get(cls, key: str, factory):
        if key not in cls._cache:
            cls._cache[key] = factory()
        return cls._cache[key]
```

Capacidades adicionales:
- `Container.reset()` — vacía el caché para tests de integración.
- `Container.diagnostico()` — ejecuta en arranque si `is_development`; intenta instanciar todos los servicios y reporta errores antes del primer request.
- Todos los imports de infraestructura y servicios están dentro de cada método factory (imports lazy).

Diagrama de dependencias del Container:

```
auth_service         ← usuario_repo
notification_service ← (sin dependencias)
exporter_service     ← ExporterFactory

configuracion_service ← configuracion_repo
usuario_service       ← usuario_repo + auth_service + auditoria_repo
estudiante_service    ← estudiante_repo + acudiente_repo + auditoria_repo
periodo_service       ← periodo_repo + configuracion_repo + auditoria_repo
asignacion_service    ← asignacion_repo + periodo_repo + auditoria_repo
evaluacion_service    ← evaluacion_repo + asignacion_repo + periodo_repo + auditoria_repo
alerta_service        ← alerta_repo + estadisticos_repo
asistencia_service    ← asistencia_repo + alerta_repo + config_repo
cierre_service        ← cierre_repo + evaluacion_repo + periodo_repo + config_repo
                         + estudiante_repo + alerta_repo + auditoria_repo
habilitacion_service  ← habilitacion_repo + cierre_repo + config_repo
convivencia_service   ← convivencia_repo + alerta_repo
estadisticos_service  ← estadisticos_repo + config_repo
informe_service       ← estadisticos_repo + exporter_service
auditoria_service     ← auditoria_repo
```

---

## 7. Capa de Interfaz (`src/interface/`)

Las páginas **solo** llaman a `Container.*`. Sin imports de `src.db`.

```python
# Patrón correcto para todas las páginas
from nicegui import ui
from container import Container

@ui.page("/ruta")
def mi_pagina():
    svc = Container.mi_service()
    ctx = SessionContext.obtener()
    # ... renderizado NiceGUI usando svc.*
```

### 7.1 Design System "Andes Minimal v2"

Implementación en `src/interface/design/`:

- **`tokens.py`** — Constantes Python: `Colors`, `AsistenciaColors`, `DesempenoColors`, `Icons`, `Spacing`, `Layout`.
- **`styles.css`** (~35 KB) — Variables CSS en `:root` con paridad 1:1 respecto a `tokens.py`; clases estructurales (`.andes-sidebar`, `.andes-card`, `.badge-*`); reset de NiceGUI.
- **`theme.py`** — `ThemeManager.aplicar()` inyecta el CSS global una sola vez en `main.py` antes de `ui.run()`.
- **`layout.py`** — Sidebar (filtrado por rol), topbar, contenido dinámico.
- **`components/`** — `context_bar.py`, `data_table.py`, `page_header.py`, `stat_card.py`, `status_badge.py`, `confirm_dialog.py`.

**Convención de color — cero colores en Python, excepto ECharts:**

| Componente | Color en Python | Color en CSS |
|---|---|---|
| Elementos HTML / NiceGUI | ❌ Prohibido | ✅ Clases CSS |
| ag-Grid `cellClass` / `rowClassRules` | ✅ Nombre de clase (string) | ✅ Definición en CSS |
| ag-Grid `cellRenderer` (HTML inline) | ❌ Prohibido | ✅ Clase CSS en el string |
| ECharts (opciones JSON) | ✅ Solo bloque `_EC_*` al inicio del módulo | ❌ No aplica |

ECharts renderiza en `<canvas>` y no puede leer variables CSS. El bloque `_EC_*` es la solución canónica: alias locales derivados de `tokens.py`, definidos al inicio del módulo.

---

## 8. Configuración (`config.py`)

`pydantic-settings` leyendo desde variables de entorno y `.env`. Soporta `development`, `production`, `test`. Validación de configuración en el arranque.

Riesgo pendiente: `JWT_SECRET` con valor por defecto inseguro emite `warnings.warn()` en producción. Debe cambiarse a `raise ValueError(...)`.

---

## 9. Testing

| Tipo | Ubicación | Herramienta |
|---|---|---|
| Integración repositorios | `tests/integration/test_repositories.py` | SQLite en memoria (`:memory:`) |
| Smoke tests Container | `tests/test_container.py` | pytest |
| Unitarios servicios | `tests/unit/services/` | `FakeRepository` por servicio, sin BD real |

Patrón para tests unitarios de servicios:

```python
class FakeXRepository:
    def __init__(self):
        self._store: dict[int, Entidad] = {}
        self._counter = 1

    def guardar(self, entidad):
        entidad.id = self._counter
        self._store[self._counter] = entidad
        self._counter += 1
        return entidad
    # ... resto de métodos del puerto

@pytest.fixture
def service():
    return XService(FakeXRepository())
```

---

## 10. Diagrama de Capas

```
┌─────────────────────────────────────────────────────────┐
│              INTERFAZ (src/interface/)                  │
│  NiceGUI Pages · Design System "Andes Minimal v2"       │
│  Layout · Components · 23+ páginas                      │
│                  ↓ solo llama a                         │
├─────────────────────────────────────────────────────────┤
│             SERVICIOS (src/services/)                   │
│  16 Application Services · DTOs Pydantic               │
│        ↓ implementan puertos del          ↓ usan       │
├─────────────────────────────────────────────────────────┤
│              DOMINIO (src/domain/)                      │
│  16 Módulos Pydantic · 16 Puertos de Repositorio        │
│  service_ports.py (IAuth, IExporter, INotification)     │
├─────────────────────────────────────────────────────────┤
│          INFRAESTRUCTURA (src/infrastructure/)          │
│  16 SQLite Repos · Auth (Bcrypt+JWT) · Context         │
│  ExporterFactory · NullExporter · NullNotification      │
└─────────────────────────────────────────────────────────┘
          ↑ todo gestionado por
┌─────────────────────────────────────────────────────────┐
│        COMPOSITION ROOT (container.py)                  │
│  Singleton lazy · DI · reset() · diagnostico()          │
└─────────────────────────────────────────────────────────┘
          ↑ configurado por
┌─────────────────────────────────────────────────────────┐
│           CONFIGURACIÓN (config.py)                     │
│  pydantic-settings · .env · validación en arranque      │
└─────────────────────────────────────────────────────────┘
```

---

## 11. Ruta de Escalabilidad (v3.0)

El núcleo (`domain/` + `services/`) es agnóstico a NiceGUI y SQLite.

**API RESTful (FastAPI):** crear `src/api/routers/` que deleguen en `Container.<x>_service()`. Los modelos Pydantic del dominio son reutilizables como schemas de respuesta. `JWTHandler` ya está listo.

**Apps móviles:** con la API operativa, consumir `InformeService` y `AlertaService` desde Flutter / React Native.

**Workers programados:** `AlertaService.detectar_riesgo_academico()` puede ejecutarse en CLI que usen el mismo Container. `CierreService` puede recibir trigger automatizado.

**Integraciones gubernamentales (SIMAT):** extender `src/infrastructure/exporters/` con `XmlExporter` o `SimatExporter` sin modificar ningún servicio.
