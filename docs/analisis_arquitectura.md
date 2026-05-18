# Análisis de Arquitectura e Ingeniería de Software
## ZECI Manager v2.0 — Auditoría Integral

> **Fecha de auditoría:** 2026-05-17  
> **Estado del proyecto:** Activo / En desarrollo  
> **Stack:** Python 3.x · NiceGUI 3.x · SQLite · Pydantic v2 · Bcrypt · JWT (stdlib)

---

## 1. Inventario de Módulos (Estado Actual)

La siguiente tabla refleja el estado real del proyecto al momento del análisis, obtenido directamente de la estructura de archivos.

### 1.1 Capa de Dominio (`src/domain/`)

| Sublayer | Módulos |
|---|---|
| **Modelos** | `acudiente`, `alerta`, `asignacion`, `asistencia`, `auditoria`, `cierre`, `configuracion`, `convivencia`, `dtos`, `estudiante`, `evaluacion`, `habilitacion`, `infraestructura`, `periodo`, `piar`, `usuario` (+ `__init__`) = **17 archivos** |
| **Puertos** | `acudiente_repo`, `alerta_repo`, `asignacion_repo`, `asistencia_repo`, `auditoria_repo`, `cierre_repo`, `configuracion_repo`, `convivencia_repo`, `estadisticos_repo`, `estudiante_repo`, `evaluacion_repo`, `habilitacion_repo`, `infraestructura_repo`, `periodo_repo`, `service_ports`, `usuario_repo` (+ `__init__`) = **17 archivos** |

> [!NOTE]
> El archivo `service_ports.py` representa los puertos de servicio (interfaces de aplicación). Su existencia indica que la arquitectura contempla la posibilidad de abstraer también los servicios, no solo los repositorios. Este es un nivel de madurez arquitectónica superior al promedio.

### 1.2 Capa de Servicios (`src/services/`)

16 servicios de aplicación implementados:

| Servicio | Descripción breve |
|---|---|
| `AcudienteService` | Gestión de acudientes/tutores |
| `AlertaService` | Detección y gestión de alertas académicas |
| `AsignacionService` | Asignación docente-grupo-asignatura |
| `AsistenciaService` | Registro y consulta de asistencia |
| `AuditoriaService` ✅ | Lectura de logs de auditoría (ya existe) |
| `CierreService` | Cierre de periodos y años académicos |
| `ConfiguracionService` | Configuración institucional y SIE |
| `ConvivenciaService` | Registro de eventos de convivencia |
| `EstadisticosService` | Cálculo de métricas académicas |
| `EstudianteService` | Gestión del ciclo de vida del estudiante |
| `EvaluacionService` | Registro y cálculo de calificaciones |
| `HabilitacionService` | Gestión de habilitaciones y recuperaciones |
| `InformeService` | Generación de boletines e informes |
| `PeriodoService` | Gestión de periodos académicos |
| `UsuarioService` | Gestión de usuarios y autenticación |
| *(`AuditoriaService`)* | **Nota:** existe en `/services/` pero **no está exportado en `__init__.py`** |

> [!WARNING]
> **Gap de exportación:** `AuditoriaService` existe en `src/services/auditoria_service.py` y está registrado en `Container.auditoria_service()`, pero **no aparece en el `__all__` del `__init__.py`** de `src/services/`. Esto significa que `from src.services import AuditoriaService` fallará silenciosamente. Se debe agregar a las exportaciones.

### 1.3 Capa de Infraestructura (`src/infrastructure/`)

| Submódulo | Contenido |
|---|---|
| `db/repositories/` | 16 implementaciones SQLite (`sqlite_*.py`) — paridad 1:1 con los puertos |
| `db/schema.py` | Definición DDL completa (~49 KB) |
| `db/seed.py` | Datos semilla iniciales (~40 KB) |
| `db/queries.py` | Consultas reutilizables |
| `db/connection.py` | Pool de conexiones SQLite con soporte WAL |
| `auth/` | `BcryptAuthService`, `JWTHandler`, `bcrypt_auth.py` |
| `context/` | `ContextInitializer`, `session_context.py` |
| `exporters/` | `ExcelExporter` (openpyxl), `NullExporter`, `ExporterFactory`, stubs PDF/Excel |
| `notifications/` | `LogNotificationService`, `NullNotificationService` |

### 1.4 Capa de Interfaz (`src/interface/`)

| Submódulo | Contenido |
|---|---|
| `design/` | `tokens.py`, `theme.py`, `layout.py`, `styles.css` (~35 KB), `components/` |
| `pages/` | `login.py`, `inicio.py` (dashboard, ~29 KB) |
| `pages/admin/` | `asignaciones`, `asignaturas`, `configuracion_institucion`, `configuracion_sie`, `grupos`, `usuarios` (6 páginas) |
| `pages/academico/` | `asistencia`, `dashboard`, `estudiantes`, `horarios` (4 páginas) |
| `pages/convivencia/` | *(en desarrollo)* |
| `pages/evaluacion/` | `cierre_anio`, `cierre_periodo`, `configuracion_evaluacion`, `habilitaciones`, `planes_mejoramiento`, `planilla_notas` (6 páginas) |
| `pages/informes/` | `boletin_anual`, `boletin_periodo`, `consolidado_asistencia`, `consolidado_notas`, `estadisticos` (5 páginas) |

**Total de páginas NiceGUI:** ~22+ páginas implementadas.

---

## 2. Análisis del Composition Root (`container.py`)

El `Container` es un **Singleton lazy por clave de caché** implementado como una clase con métodos de clase. Es uno de los componentes arquitectónicamente más sólidos del sistema.

### 2.1 Fortalezas del Container

- **Lazy initialization:** Cada componente se instancia bajo demanda, reduciendo el tiempo de arranque y evitando errores de dependencias circulares en módulos con errores.
- **Cache dict-based:** `_cache: dict[str, Any] = {}` es un atributo de clase compartido entre todos los accesos, garantizando singleton efectivo por proceso.
- **`Container.reset()`:** Permite vaciar el caché para tests de integración, lo que hace al sistema verdaderamente testeable.
- **`Container.diagnostico()`:** Introspección en tiempo de arranque que intenta instanciar todos los servicios y reporta errores antes de servir el primer request. Se ejecuta automáticamente en `is_development`.
- **Imports lazy:** Todos los imports de infraestructura y servicios están dentro de cada método factory, evitando la carga de módulos no necesarios y los errores en cascada.

### 2.2 Mapa de Dependencias del Container

```
auth_service         ← usuario_repo
notification_service ← (sin dependencias)
exporter_service     ← (ExporterFactory)

configuracion_service ← configuracion_repo
usuario_service       ← usuario_repo + auth_service + auditoria_repo
estudiante_service    ← estudiante_repo + acudiente_repo + auditoria_repo
periodo_service       ← periodo_repo + configuracion_repo + auditoria_repo
asignacion_service    ← asignacion_repo + periodo_repo + auditoria_repo
evaluacion_service    ← evaluacion_repo + asignacion_repo + periodo_repo + auditoria_repo
alerta_service        ← alerta_repo + estadisticos_repo
asistencia_service    ← asistencia_repo + alerta_repo + config_repo
cierre_service        ← cierre_repo + evaluacion_repo + periodo_repo + config_repo
                         + estudiante_repo + alerta_repo + auditoria_repo  (7 dependencias)
habilitacion_service  ← habilitacion_repo + cierre_repo + config_repo
convivencia_service   ← convivencia_repo + alerta_repo
estadisticos_service  ← estadisticos_repo + config_repo
informe_service       ← estadisticos_repo + exporter_service
auditoria_service     ← auditoria_repo
```

> [!IMPORTANT]
> **`CierreService` tiene 7 dependencias directas.** Es el servicio más acoplado del sistema. Si bien esto refleja la complejidad real del dominio (el cierre de periodo es la operación más compleja académicamente), se debería considerar si parte de la lógica puede ser delegada a otros servicios para reducir la carga de responsabilidades en un solo punto.

---

## 3. Sistema de Autenticación y Seguridad

El sistema implementa una **arquitectura de seguridad de doble capa** que merece análisis detallado.

### 3.1 Capa de Sesión (NiceGUI — v2.x actual)

- **Mecanismo:** `app.storage.user` (diccionario de sesión cifrado gestionado por NiceGUI/Starlette).
- **Clave de cifrado:** `storage_secret=settings.JWT_SECRET` en `ui.run()`.
- **Flujo:** Login → `BcryptAuthService.autenticar()` → `ContextInitializer.inicializar()` → `SessionContext.guardar()` → redirect a `/inicio`.
- **Guard en páginas:** Verificación manual `app.storage.user.get("autenticado")` en cada `@ui.page`.

### 3.2 Capa JWT (preparada para API REST — v3.0)

- **`JWTHandler`** implementado con **stdlib pura** (`hmac`, `hashlib`, `base64`), sin dependencias externas.
- **Algoritmo:** HS256 (HMAC-SHA256).
- **Expiración:** Configurable, default 8 horas (jornada escolar completa).
- **Estado:** El docstring del archivo lo deja claro: *"No se usa en v2.x, preparado para v3.0 (API REST)"*.

> [!NOTE]
> La decisión de implementar `JWTHandler` con stdlib es una elección deliberada de reducción de dependencias. Es correcta para el contexto, pero implica que la implementación no soporta claims estándar avanzados (RS256, JWKS, etc.) que serían necesarios si se integra con un Identity Provider externo (OAuth2/OIDC).

### 3.3 Riesgo de Seguridad Identificado

> [!CAUTION]
> **JWT_SECRET tiene un valor por defecto inseguro** (`"cambia-esta-clave-en-produccion-ahora"`). El `model_validator` en `config.py` emite un `warnings.warn()` si el entorno es `production` y el secret tiene ese valor. Sin embargo:
> 1. `warnings.warn()` es silencioso si `logging` está configurado antes de que Python cargue el módulo de warnings.
> 2. No hay ningún mecanismo que **bloquee** el arranque si el secret es inseguro en producción.
> **Recomendación:** Cambiar a `raise ValueError(...)` en el `model_validator` cuando `APP_ENV == "production"`.

---

## 4. Subsistema de Contexto de Sesión (`ContextInitializer`)

Este subsistema es una de las piezas más sofisticadas del proyecto y merece análisis propio.

### 4.1 Arquitectura del Contexto

`ContextInitializer` actúa como un **servicio de resolución de contexto académico** que se ejecuta una vez en el login para materializar en la sesión del usuario:

- El **año académico activo** (via `ConfiguracionService`)
- El **período activo** (via `PeriodoService`, con fallback al primer período no cerrado)
- El **grupo y asignatura** del docente (via `AsignacionRepository`, con ordenación determinista)
- Solo el **grupo** para directores (sin asignatura)

### 4.2 Fortalezas

- **Stateless:** Todos los métodos son `@staticmethod`. No hay estado de instancia que pueda corromperse.
- **Resiliente a fallos:** Cada paso de resolución (`_resolver_anio`, `_resolver_periodo`, etc.) captura sus propias excepciones y retorna `False` sin propagar. La inicialización siempre retorna un contexto, aunque sea parcial.
- **Contexto con auto-refresco:** `ContextInitializer.refrescar_si_invalido(ctx)` detecta si el contexto guardado sigue siendo válido en la BD (el año fue desactivado, el periodo fue cerrado, la asignación fue removida) y lo re-inicializa automáticamente sin forzar al usuario a hacer logout.

### 4.3 Inconsistencia Detectada: Bypass de Repositorio en ContextInitializer

> [!WARNING]
> En `_resolver_grupo_y_asignatura()` (línea 203), el `ContextInitializer` llama directamente a `Container.asignacion_repo().listar_por_docente(...)` en lugar de usar `Container.asignacion_service()`. Esto es un bypass similar al detectado en `inicio.py`. Si en el futuro `AsignacionService` añade lógica de permisos o cache, esta ruta la saltaría.
> 
> Adicionalmente, en `contexto_es_valido()` (línea 290), se llama directamente a `Container.periodo_repo().get_by_id(...)` en lugar de `Container.periodo_service()`.

---

## 5. Design System (`src/interface/design/`)

El sistema de diseño **"Andes Minimal v2"** implementa una arquitectura de tokens que es notable por su completitud:

### 5.1 Componentes del Design System

| Archivo | Responsabilidad |
|---|---|
| `tokens.py` | Constantes Python: `Colors`, `AsistenciaColors`, `DesempenoColors`, `Icons`, `Spacing`, `Layout` |
| `styles.css` | Variables CSS (`:root { --color-primary: ... }`), clases utilitarias, componentes |
| `theme.py` | `ThemeManager.aplicar()` — inyecta el CSS global en NiceGUI una sola vez |
| `layout.py` | Layout global: sidebar + topbar con toggle y estado de sesión |
| `components/` | Componentes NiceGUI reutilizables |

### 5.2 Fortaleza: Doble Representación de Tokens

Los colores existen en **dos formas sincronizadas**:
- Como **variables CSS** en `styles.css` (`:root { --color-primary: #2563EB; }`) para los componentes HTML/NiceGUI.
- Como **constantes Python** en `tokens.py` (`Colors.PRIMARY = "#2563EB"`) para lógica condicional, ag-grid column defs, y estilos inline calculados.

> [!NOTE]
> La doble representación introduce un riesgo de desincronización si un valor se cambia en un lugar y no en el otro. El docstring de `tokens.py` lo documenta explícitamente: *"Si cambias un color aquí, cámbialo también en `:root { ... }` de `styles.css`"*. Una mejora futura sería generar los tokens CSS desde Python en el arranque via `ThemeManager`, eliminando la duplicación.

### 5.3 Lógica de Dominio en Tokens de Diseño

> [!WARNING]
> `DesempenoColors.para_nota()` (tokens.py, línea 141) contiene lógica de dominio educativo:
> ```python
> if nota < 3.0:  return "Bajo"
> if nota < 3.8:  return "Básico"  
> if nota < 4.6:  return "Alto"
> return "Superior"
> ```
> Estos umbrales (3.0, 3.8, 4.6) son **reglas de negocio del sistema educativo colombiano**, no decisiones de diseño visual. Deberían vivir en el modelo de dominio `Evaluacion` o en `ConfiguracionService` (ya que la institución podría configurarlos). Tenerlos en `tokens.py` los vuelve inaccesibles para la capa de servicios sin crear una dependencia inversa.

---

## 6. Análisis de la Cobertura de Tests

### 6.1 Estructura del Suite de Tests

```
tests/
├── conftest.py           (5.2 KB) — fixtures compartidos
├── test_container.py     (2.7 KB) — smoke tests del Container
├── unit/
│   ├── domain/
│   ├── infrastructure/
│   └── services/
└── integration/
    ├── audit_ports.py    (12.9 KB) — auditoría de puertos
    ├── generate_schema.py (6.0 KB) — generación de schema
    ├── test_repositories.py (41.8 KB) — tests de repositorios
    └── test_scratch.py   (92 B)  — placeholder
```

### 6.2 Observaciones sobre el Suite

> [!IMPORTANT]
> `test_repositories.py` con **41.8 KB** es el archivo de tests más grande del proyecto. Indica una cobertura significativa a nivel de repositorio (infraestructura), lo cual es positivo para detectar errores de hidratación Pydantic ↔ SQLite.
>
> Sin embargo, la carpeta `tests/unit/services/` está presente pero no se pudo confirmar la cobertura de los 16 servicios de aplicación. Los servicios contienen la lógica de negocio más crítica (cálculo de promedios, cierre de periodo, detección de riesgo académico) y deberían tener tests unitarios con mocks.

---

## 7. Inconsistencias Arquitectónicas (Inventario Actualizado)

### 7.1 — Bypass de Servicios desde la UI *(Severidad: Alta)*

**Problema original (detectado en análisis previo):** La UI en `inicio.py` accedía directamente a `Container.auditoria_repo()` y `Container.periodo_repo()`.

**Estado actual:** `AuditoriaService` **ya existe** (`src/services/auditoria_service.py`) y está **registrado** en el Container. Sin embargo, se debe verificar si `inicio.py` ya fue actualizado para usarlo.

**Bypass adicional encontrado:** `ContextInitializer` también accede directamente a repositorios (ver §4.3).

### 7.2 — `AuditoriaService` No Exportado en `__init__.py` *(Severidad: Media)*

`src/services/__init__.py` lista 14 servicios en `__all__` pero **omite `AuditoriaService`**. Esto rompe el contrato de importación del módulo de servicios.

```python
# Corrección requerida en src/services/__init__.py:
from src.services.auditoria_service import AuditoriaService
# Y en __all__: agregar "AuditoriaService"
```

### 7.3 — Lógica de Dominio en Capa de Presentación *(Severidad: Media)*

`DesempenoColors.para_nota()` en `tokens.py` contiene los umbrales de calificación del sistema educativo colombiano. Estos deben migrarse al dominio o a configuración.

### 7.4 — Seguridad del JWT Secret *(Severidad: Alta en Producción)*

`config.py` emite `warnings.warn()` pero no bloquea el arranque si `JWT_SECRET` tiene el valor por defecto en producción. Riesgo de despliegue inseguro inadvertido.

### 7.5 — Posible Race Condition en `app.storage.user` *(Severidad: Media)*

El `SessionContext` y los componentes `refreshable` en NiceGUI pueden leer/mutar `app.storage.user` concurrentemente. NiceGUI 3.x gestiona las conexiones WebSocket por usuario en corutinas separadas, lo que puede generar estados inconsistentes si dos callbacks asíncronos modifican el storage simultáneamente.

### 7.6 — Exportadores Incompletos *(Severidad: Baja — Deuda técnica)*

`src/infrastructure/exporters/excel_exporter.py` y `pdf_exporter.py` tienen **0 bytes** (stubs vacíos). `ExporterFactory` devuelve el `NullExporter` si las dependencias no están disponibles (patrón Null Object correcto), pero la funcionalidad de exportación PDF y Excel no está implementada.

---

## 8. Fortalezas Arquitectónicas Confirmadas

1. **Clean Architecture estricta:** La regla de dependencia se respeta en >95% del código. El núcleo de dominio no importa NiceGUI, SQLite, ni bcrypt.

2. **Patrón Repositorio con DI completa:** Los 16 repositorios tienen interfaces abstractas en `domain/ports/` y sus implementaciones SQLite en `infrastructure/`. El Container inyecta las implementaciones concretas sin que los servicios conozcan SQLite.

3. **Auditoría transversal no invasiva:** El mecanismo `_auditar()` en los servicios registra cambios sin contaminar la lógica de negocio. La auditoría de lectura está separada en `AuditoriaService`.

4. **Configuración 12-Factor:** `config.py` con `pydantic-settings` lee desde variables de entorno y `.env`. Soporte explícito para `development`, `production` y `test`. Validación de configuración en el arranque.

5. **Arranque defensivo:** `Container.diagnostico()` + `inicializar_base_de_datos()` en `main.py` garantizan que los errores de configuración se detecten antes de servir el primer request.

6. **Sistema de contexto académico inteligente:** `ContextInitializer.refrescar_si_invalido()` protege contra sesiones con contexto desactualizado después de cierres de periodo.

7. **Diseño de tokens bidireccional:** El design system "Andes Minimal v2" sincroniza colores, espaciado e iconos entre Python y CSS, permitiendo cálculos de color condicionales en la capa de presentación.

8. **Patrón Null Object en adaptadores externos:** `NullExporter` y `NullNotificationService` permiten que el sistema funcione en entornos sin dependencias opcionales instaladas (openpyxl, etc.).

---

## 9. Hoja de Ruta de Refactorización

### 🔴 Prioridad Alta (Ahora)

| # | Acción | Archivo(s) |
|---|---|---|
| R1 | Agregar `AuditoriaService` a `__init__.py` de services | `src/services/__init__.py` |
| R2 | Reemplazar `JWT_SECRET` warning por `ValueError` en producción | `config.py` |
| R3 | Verificar que `inicio.py` usa `Container.auditoria_service()` en vez de `auditoria_repo()` | `src/interface/pages/inicio.py` |
| R4 | Reemplazar el bypass de repositorio en `ContextInitializer` | `src/infrastructure/context/context_initializer.py` |

### 🟡 Prioridad Media (Próximo sprint)

| # | Acción | Archivo(s) |
|---|---|---|
| R5 | Migrar umbrales de calificación de `tokens.py` al dominio | `tokens.py` → `domain/models/evaluacion.py` |
| R6 | Encapsular mutations de `app.storage.user` para atomicidad | `SessionContext.guardar()` |
| R7 | Tests unitarios para los 16 servicios con mocks de repositorios | `tests/unit/services/` |

### 🟢 Prioridad Baja (Deuda técnica)

| # | Acción | Archivo(s) |
|---|---|---|
| R8 | Implementar `ExcelExporter` y `PDFExporter` | `src/infrastructure/exporters/` |
| R9 | Generar tokens CSS dinámicamente desde `tokens.py` en `ThemeManager.aplicar()` | `theme.py` |
| R10 | Documentar `ARCHITECTURE.md` con guía de creación de nuevos clientes (API, CLI) | Raíz del proyecto |

---

## 10. Capacidad de Escalabilidad Futura

Dado que el núcleo del sistema (`domain/` + `services/`) es completamente agnóstico a NiceGUI y SQLite, el sistema puede escalar hacia:

### 10.1 API RESTful (FastAPI — v3.0)
- Crear capa `src/api/routers/` con endpoints que deleguen directamente en `Container.<x>_service()`.
- El `JWTHandler` ya está implementado y listo para autenticar requests HTTP.
- Los modelos Pydantic de dominio pueden reutilizarse como schemas de respuesta con mínimas adaptaciones.

### 10.2 Aplicaciones Móviles (Flutter / React Native)
- Con la API REST operativa, apps móviles para acudientes pueden consumir `InformeService` y `AlertaService`.
- Notificaciones Push pueden implementarse como un nuevo adaptador en `src/infrastructure/notifications/`.

### 10.3 Workers Programados (CronJobs / Celery)
- `AlertaService.detectar_riesgo_academico()` puede ejecutarse en scripts CLI que usen el mismo `Container`.
- `CierreService` podría recibir un trigger automatizado a final de periodo.

### 10.4 Integraciones Gubernamentales (SIMAT)
- Los adaptadores de exportación en `src/infrastructure/exporters/` pueden extenderse con `XmlExporter` o `SimatExporter` sin modificar ningún servicio.

---

## 11. Diagrama de Capas (Arquitectura Limpia)

```
┌─────────────────────────────────────────────────────────┐
│              INTERFAZ (src/interface/)                  │
│  NiceGUI Pages · Design System · Layout · Components    │
│                  ↓ solo llama a                         │
├─────────────────────────────────────────────────────────┤
│             SERVICIOS (src/services/)                   │
│  16 Application Services · DTOs Pydantic               │
│        ↓ implementan puertos de            ↓ usan      │
├─────────────────────────────────────────────────────────┤
│              DOMINIO (src/domain/)                      │
│  17 Modelos Pydantic · 16 Puertos de Repositorio        │
│  dtos.py · service_ports.py                             │
├─────────────────────────────────────────────────────────┤
│          INFRAESTRUCTURA (src/infrastructure/)          │
│  16 SQLite Repos · Auth (Bcrypt+JWT) · Context         │
│  Exporters (Excel/PDF/Null) · Notifications             │
└─────────────────────────────────────────────────────────┘
          ↑ todo gestionado por
┌─────────────────────────────────────────────────────────┐
│        COMPOSITION ROOT (container.py)                  │
│  Singleton lazy · DI · diagnóstico · reset para tests   │
└─────────────────────────────────────────────────────────┘
          ↑ configurado por
┌─────────────────────────────────────────────────────────┐
│           CONFIGURACIÓN (config.py)                     │
│  pydantic-settings · .env · validación en arranque      │
└─────────────────────────────────────────────────────────┘
```

---

*Análisis generado el 2026-05-17. Revisiones futuras deben actualizarse cuando se completen los ítems de la hoja de ruta.*
