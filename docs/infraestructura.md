# Capa de Infraestructura (Adaptadores Generales)

Este documento describe la arquitectura y los detalles de implementación de los adaptadores de la capa de infraestructura que **no están relacionados con la base de datos**. Mientras que los repositorios (`src/infrastructure/db/repositories/`) manejan la persistencia y se documentan en `repositorio.md`, esta sección cubre los adaptadores responsables de la autenticación, el contexto de la aplicación, y las exportaciones a formatos externos.

La capa de infraestructura implementa los **Puertos (Interfaces)** definidos por el dominio, interactuando con bibliotecas de terceros sin acoplar la lógica de negocio a dichas herramientas.

> 📖 **Referencia por método (firma + docstring):**
> [`docs/api_reference/infraestructura.md`](api_reference/infraestructura.md) —
> generada desde el código con `tools/gen_api_reference.py`. Nota: los repos
> SQLite muestran baja cobertura de docstring **por diseño** — el contrato (y su
> docstring) vive en el puerto del dominio, no en la implementación.

## 1. Módulo: Autenticación (`src/infrastructure/auth/`)

Proporciona implementaciones para el manejo seguro de credenciales de usuario.

### Adaptador: `BcryptAuthService` (`bcrypt_auth_service.py`)
Implementa la interfaz `IAuthenticationService`.

- **Responsabilidad:** Asegurar las contraseñas del sistema utilizando el algoritmo de hashing `bcrypt` adaptativo.
- **Detalles técnicos:**
  - Usa la librería **`bcrypt` directamente** (no `passlib`), con `ROUNDS = 12`
    (salt interno aleatorio por hash). Aumentar en producción si el hardware lo
    permite.
  - Provee `hashear_password`, `verificar_password`, `cambiar_password`
    (verifica la actual antes de persistir), `resetear_password` (flujo admin) y
    `autenticar_usuario` (existencia + verificación + estado de cuenta).
  - **Compatibilidad legacy:** `verificar_password` acepta hashes con prefijo
    `sha256:` provenientes del seed de desarrollo antiguo, migrando de forma
    transparente.
  - **No enumeración:** `autenticar_usuario` lanza siempre `ValueError`
    genéricos (`credenciales_invalidas`, `cuenta_inactiva`) y solo revela el
    estado de la cuenta tras verificar la contraseña, para no facilitar
    enumeración de usuarios (paso_37).
  - Recibe `IUsuarioRepository` inyectado para persistir hashes; sin repo, solo
    funciona la criptografía pura. Aisla por completo la criptografía del
    `UsuarioService` de la capa de dominio.
- **Relación con Frameworks:** Es agnóstico a NiceGUI/FastAPI; opera exclusivamente con strings, lo que permite su testeo unitario aislado.
- **Throttle de login:** el freno de fuerza bruta (A1) NO vive aquí sino en el
  mecanismo neutral `src/services/login_throttle.py` (bcrypt encarece cada
  intento; el throttle lo *frena*).

### Adaptador: `jwt_handler.py`
Manejo de tokens JWT (firma/verificación con `HS256` y `JWT_SECRET`). Está
**preparado para una futura API REST (v3)**. La app de escritorio actual **no**
consume JWT para autorizar peticiones: la sesión vive en la cookie firmada de
NiceGUI. La revocación/rotación de JWT se difiere a v3 (ver `docs/seguridad.md`
B4).

## 2. Módulo: Contexto de Estado (`src/infrastructure/context/`)

Resuelve el contexto académico inicial tras el login.

### `ContextInitializer` (`context_initializer.py`)
Responsable del "bootstrap": inyecta/resuelve el estado académico inicial
(año/periodo/grupo/asignación por defecto) necesario para que la sesión recién
autenticada arranque con un contexto coherente. Se invoca vía
`Container.inicializar_contexto(ctx)`.

> **Nota de ubicación (importante).** El *wrapper de la sesión activa*,
> `SessionContext`, **vive en la capa de interfaz**
> (`src/interface/context/session_context.py`), no en infraestructura: envuelve
> `app.storage.user` de NiceGUI, expone el contexto académico y es el **choke
> point** que sincroniza los `ContextVar` de servicios (`solo_lectura` +
> `institucion`) y gestiona la impersonación "Ver como". Ver
> `docs/architecture.md` §7.3–7.4.

## 3. Módulo: Exportadores de Documentos (`src/infrastructure/exporters/`)

Responsable de tomar datos estructurados generados por los servicios (`DTOs`, Listas, Diccionarios) y renderizarlos en documentos binarios para su descarga final. Todos implementan la interfaz de dominio `IExporterService`.

### Selección en arranque: `exporter_factory.crear_exporter()`
El `Container` **no** instancia una clase fija: llama a `crear_exporter()`, que
elige el mejor exportador disponible según las dependencias instaladas
(degradación en cascada). El nivel activo se registra en el log al arrancar.

| Nivel | Exportador | Requiere | Capacidades |
|---|---|---|---|
| 1 | `WeasyPrintExporter` (PDF vía weasyprint) | `weasyprint` + `openpyxl` | PDF + Excel + CSV |
| 1b | `WeasyPrintExporter` (PDF vía reportlab) | `reportlab` + `openpyxl` | PDF + Excel + CSV |
| 2 | `OpenpyxlExporter` | `openpyxl` | Excel + CSV (sin PDF) |
| 3 | `NullExporter` | — (sin dependencias) | Solo CSV |

> El catch es amplio (`Exception`, no solo `ImportError`) porque `weasyprint`
> puede fallar con `OSError` al cargar libgobject/libpango en Windows sin las
> libs nativas; en ese caso cae al siguiente nivel.

### Adaptador: `OpenpyxlExporter` (`openpyxl_exporter.py`)
Genera hojas de cálculo (`.xlsx`) y CSV.
- **Responsabilidad:** Crear planillas de notas, listas de asistencia y exportaciones de configuraciones complejas hacia Excel.
- **Dependencias Ocultas:** Encapsula totalmente el uso de `openpyxl`. Estilos, anchos de columna y colores de celda viven aquí y no contaminan el `InformeService`.

### Adaptador: `WeasyPrintExporter` (`pdf_exporter.py`)
Genera documentos PDF (además de Excel + CSV).
- **Responsabilidad:** Construir boletines de periodo, actas finales y consolidados en formato listo para imprimir. La construcción específica de boletines se apoya en `boletin_pdf.py`.
- **Dependencias Ocultas:** Encapsula `weasyprint` (o `reportlab` como fallback).

### Adaptador: `NullExporter` (`null_exporter.py`)
Implementa el patrón Null Object (solo CSV).
- **Responsabilidad:** Proporcionar una implementación segura que no rompe la aplicación cuando las librerías pesadas no están instaladas. Los formatos no soportados lanzan `RuntimeError` descriptivos que la UI atrapa para mostrar mensajes claros en lugar de colapsos genéricos del servidor.

## 3.b Módulo: Notificaciones (`src/infrastructure/notifications/`)

Implementan la interfaz de dominio `INotificationService` (notificar a acudientes,
docentes y directivos). El servicio de dominio decide CUÁNDO y A QUIÉN notificar;
estos adaptadores deciden CÓMO/por qué canal.

- **`NullNotificationService`** — Null Object: no envía nada (default del
  `Container` hoy). Punto de extensión para el canal real (email/SMS/push).
- **`LogNotificationService`** — subclase que registra la notificación en el log
  (útil en desarrollo para ver qué se habría enviado).

## 4. Repositorio SIEE (`src/infrastructure/db/repositories/sqlite_siee_repo.py`)

Adaptador para el **Sistema Institucional de Evaluación** (SIEE). *(Nuevo — Junio 2026)*

- **Responsabilidad:** Persiste y lee la `ConfiguracionSIEE` (modo de evaluación y porcentaje de autonomía docente por año) y las categorías institucionales (`Categoria` con `es_institucional=True`).
- **Implementa:** `ISIEERepository` del dominio.
- **Consumido por:** `EvaluacionService` para determinar si la institución opera en modo SIEE centralizado o en modo libre por docente.

---

## Resumen de Interacciones

Ningún componente del Dominio invoca métodos de estas clases directamente. En tiempo de arranque (`container.py`), las clases de infraestructura son instanciadas e inyectadas a los Servicios como si fuesen sus respectivas interfaces (`IAuthenticationService`, `IExporterService`), adhiriendo estrictamente al Principio de Inversión de Dependencias (DIP).
