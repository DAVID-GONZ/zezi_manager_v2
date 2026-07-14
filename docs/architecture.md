# Arquitectura — ZECI Manager v2.0

> Referencia arquitectónica central para todos los agentes y colaboradores.
> Documento **autocontenido**: este archivo es la fuente de verdad de la
> arquitectura. Los detalles por capa se amplían en los documentos hermanos de
> `docs/` (ver §12), no en archivos externos al repositorio.

---

## 0. Panorama

ZECI Manager es un sistema de gestión académica (matrícula, evaluación,
asistencia, convivencia, horarios, informes) construido sobre **Arquitectura
Limpia / Puertos y Adaptadores**.

| Aspecto | Elección |
|---|---|
| Lenguaje | Python 3.11+ |
| UI | NiceGUI (servidor web + WebSocket) |
| Persistencia | SQLite (SQL crudo, sin ORM), modo WAL |
| Validación | Pydantic v2 (entidades de dominio + settings) |
| Autenticación | `bcrypt` (rounds=12) + cookie de sesión firmada de NiceGUI |
| Composición | `container.py` (composition root, singleton lazy) |
| Configuración | `config.py` (`pydantic-settings`, lee `.env`) |
| Arranque | `main.py`; verificación de entorno con `python init.py` |

Diagrama de alto nivel:

```
                         ┌──────────────────────────────┐
   navegador  ◀────────▶ │  NiceGUI  (src/interface/)    │
   (cookie de sesión)    │  páginas · guard · design     │
                         └───────────────┬──────────────┘
                                         │ Container.*_service()
                         ┌───────────────▼──────────────┐
                         │  Servicios (src/services/)    │  casos de uso
                         └───────────────┬──────────────┘
                                         │ puertos (ABC)
      ┌──────────────────────────────────┼──────────────────────────────────┐
      │                                   │                                   │
┌─────▼─────────────┐          ┌──────────▼──────────┐            ┌───────────▼──────────┐
│  Dominio          │          │  Infraestructura    │            │  Composition root    │
│ (src/domain/)     │◀─────────│ (src/infrastructure)│            │  container.py        │
│ models · ports ·  │ implementa│ repos SQLite · auth │            │  config.py           │
│ policies          │  puertos  │ exporters · notif.  │            │  main.py             │
└───────────────────┘          └─────────────────────┘            └──────────────────────┘
```

---

## 1. Regla de dependencias (no negociable)

```
interface → services → domain ← infrastructure
                                      ↑
                                 container.py
```

- **`domain/`** no importa nada externo (solo stdlib + `pydantic`). Contiene
  entidades, puertos (interfaces `ABC`) y **políticas** puras.
- **`infrastructure/`** implementa los contratos del dominio. Es la **única**
  capa que puede tocar `sqlite3`, `pandas`, `bcrypt`, `openpyxl`, `weasyprint`.
- **`services/`** orquesta casos de uso sin saber de SQL ni de NiceGUI. Solo
  importa de `src/domain/`.
- **`interface/`** consume servicios vía `Container`, **nunca** repositorios ni
  `fetch_df`/`execute`.
- **`container.py`** es el único que importa de todas las capas (composition root).

**Una violación de esta regla es un bug, no una decisión de diseño.** `init.py`
incluye un gate de anti-patrones que la verifica automáticamente
(ver `docs/verification.md` y `docs/conventions.md` §2).

---

## 2. Mapa de capas (estado actual del código)

| Capa | Ruta | Contenido | Nº aprox. |
|---|---|---|---|
| Dominio · modelos | `src/domain/models/` | Entidades Pydantic + DTOs | 19 módulos |
| Dominio · puertos | `src/domain/ports/` | 19 puertos de repositorio + `service_ports` (3 interfaces de servicio) | 20 módulos |
| Dominio · políticas | `src/domain/policies/` | Funciones puras de reglas transversales (RBAC, contraseñas, cadena de auditoría) | 3 módulos |
| Servicios | `src/services/` | Casos de uso + mecanismos neutrales (solo-lectura, tenant, throttle) | ~28 servicios + 3 mecanismos |
| Infraestructura · repos | `src/infrastructure/db/repositories/` | Adaptadores SQLite | 19 repos |
| Infraestructura · otros | `src/infrastructure/{auth,exporters,notifications,context}/` | bcrypt/JWT, exportadores, notificaciones, contexto | — |
| Interfaz · páginas | `src/interface/pages/` | Páginas NiceGUI (admin, académico, evaluación, convivencia, informes) | ~30 páginas |
| Interfaz · auth | `src/interface/auth/` | Guard central de rutas (`registrar_pagina`) | 2 módulos |
| Interfaz · design | `src/interface/design/` | Layout, tema, tokens, componentes reutilizables, CSS | — |

> Cada capa se documenta en detalle: modelos → `docs/modelos.md` y
> `docs/schema.md`; puertos → `docs/dominio.md`; repos → `docs/repositorio.md`;
> servicios → `docs/services.md`; infraestructura → `docs/infraestructura.md`;
> páginas → `docs/page_patterns.md`.

---

## 3. Principio de migración: reorganizar, no reescribir

Cada función SQL, cada cálculo de negocio, cada componente UI ya existe en v1.0.
La tarea de migración es:

| Operación | Cuándo aplicarla |
|---|---|
| **MOVER** | El código existe en `pages/` o `modules/` — cortarlo y pegarlo en el lugar correcto sin cambiar la lógica. |
| **ENVOLVER** | Existe un componente legacy — crear una clase que implementa la interfaz y delega. |
| **SUSTITUIR** | Hay un `dict` o `DataFrame` en una firma — reemplazarlo por la entidad Pydantic correspondiente. |
| **CREAR** | El código genuinamente no existe (interfaces ABC, container, políticas, FakeRepository). |

Si el agente está "reescribiendo" lógica, se equivocó de operación.

---

## 4. El Container es el único punto de instanciación

`container.py` es el composition root. Ningún módulo fuera de él crea instancias
de repositorios o servicios. Patrón: **singleton lazy por nombre** con imports
perezosos (dentro de cada método `@classmethod`) para evitar ciclos y acelerar el
arranque.

```python
from container import Container

svc = Container.estudiante_service()      # ✅
repo = SqliteEstudianteRepository()       # ❌ nunca en páginas ni servicios
```

- `Container.reset()` vacía el caché (tests de integración).
- `Container.diagnostico()` instancia todos los servicios al arrancar (en
  desarrollo) y reporta configuraciones rotas antes de servir tráfico.
- El cableado de dependencias (qué repos recibe cada servicio) vive **solo** aquí.
  Ver el árbol de dependencias real en `container.py`.

---

## 5. Pandas vive solo en infraestructura

`fetch_df` retorna un `DataFrame`. El repositorio lo mapea a entidades Pydantic y
lo devuelve. Los servicios y las páginas **nunca** ven DataFrames ni `groupby`.

Los cálculos de métricas agregadas (dashboard, promedios por grupo) van como
`GROUP BY` en SQL dentro del repositorio (`SqliteEstadisticosRepository`), no como
`groupby`/`iterrows` en Python.

---

## 6. Auditoría transversal e integridad

- Todo método mutador de servicio termina con `_auditar()`. La auditoría no
  contamina la lógica de negocio. Firma exacta en `docs/conventions.md` §4.
- Dos bitácoras **append-only**: `auditoria` (eventos de sesión/acceso) y
  `audit_log` (cambios CRUD). Modelos en `src/domain/models/auditoria.py`.
- **Cadena hash (M4).** `src/domain/policies/audit_chain.py` firma cada registro
  encadenándolo con el anterior:
  `hash_cadena = SHA256(hash_previo_or_GENESIS || payload_canónico)`. El repo
  SQLite calcula el hash al insertar y verifica la integridad reconstruyendo la
  secuencia (`primer_eslabon_roto`). Detecta edición/inserción/borrado
  intermedio; el truncado del final requiere un ancla externa (fuera de alcance).

---

## 7. Seguridad — arquitectura en código

El épico de seguridad (`seguridad_01..04`) y los frentes de roles/multi-tenant
introdujeron mecanismos transversales. Resumen de decisiones en
`docs/seguridad.md`; aquí, su ubicación arquitectónica:

### 7.1 Autorización por ruta — deny by default

`src/interface/auth/route_guard.py` centraliza la autorización. **Toda** página
se registra con `registrar_pagina(ruta, page_fn, roles=...)`:

- `roles` es **obligatorio**: es imposible registrar una ruta sin declarar quién
  accede. Sentinels explícitos `PUBLICO` (sin sesión) y `AUTENTICADO` (cualquier
  rol con sesión); en otro caso, un `frozenset[Rol]`.
- El registro `{ruta: roles}` es la **única fuente de verdad**; el NAV
  (`layout.py`) deriva su visibilidad del mismo registro (sin listas duplicadas).
- `decidir_acceso(...)` es una función pura y testeable: `OK` → render,
  `LOGIN` → `/login`, `DENEGADO` → toast + `/inicio`.
- El guard también fuerza el **cambio de contraseña** (A2) y sincroniza el
  contexto central (B1) antes de renderizar (ver §7.4).
- La matriz ruta → roles vive en `main.py::registrar_rutas_ui()`.

### 7.2 Políticas de dominio (fuente de verdad, defensa en profundidad)

`src/domain/policies/` — funciones puras sin estado ni dependencias:

- **`rbac_usuarios.py`** — matriz de "quién asigna/gestiona qué rol":
  `admin → {admin, director}`, `director → {coordinador, profesor}`. Consultada
  tanto por el servicio (enforcement real) como por la vista (gating de controles)
  para no divergir.
- **`password_policy.py`** — requisitos de contraseña (≥8, letra+dígito, distinta
  del username). El servicio hace enforcement (`validar_password`); la UI muestra
  las reglas legibles (`requisitos_password`). Nunca loguea ni persiste la clave.
- **`audit_chain.py`** — algoritmo de encadenamiento por hash (ver §6).

### 7.3 Modo solo lectura ("Ver como") y scope multi-tenant

Dos mecanismos **neutrales** en `src/services/` (sin importar interfaz/infra),
ambos apoyados en `contextvars.ContextVar` (uno por task de NiceGUI):

- **`solo_lectura.py`** — bloquea mutaciones durante la impersonación "Ver como"
  del admin. Los métodos de mutación llaman `verificar_escritura()` o se decoran
  con `@requiere_escritura` (lanza `OperacionSoloLecturaError`). El bloqueo es
  central, no página por página.
- **`contexto_tenant.py`** — expone la institución activa de la sesión.
  **Regla de scope:** rol `admin` → `None` (opera cross-tenant); cualquier otro →
  su `institucion_id`. `verificar_pertenencia(id_del_objeto_leído)` cierra la
  dimensión multi-tenant en operaciones por `id`. `usar_institucion(id)` es un
  context manager para seed/scripts/tests sin sesión.

La impersonación vive en `src/interface/context/session_context.py`
(`iniciar_ver_como` / `salir_ver_como`): conserva la identidad real del admin,
asume identidad + institución del objetivo en solo lectura, y audita inicio/fin
(`VER_COMO_INICIO` / `VER_COMO_FIN`).

### 7.4 Choke point central del contexto

`SessionContext.desde_storage()` es el punto único que sincroniza los
`ContextVar` de servicios (`solo_lectura` + `institucion`) desde la cookie de
sesión. El **guard central** lo invoca antes de renderizar cualquier página
protegida (B1), de modo que toda petición sincroniza el contexto sin depender de
que la página lo recuerde (defensa en profundidad).

### 7.5 Throttle de login

`src/services/login_throttle.py` — tras `MAX_INTENTOS=5` fallos consecutivos por
username (normalizado), bloquea `BLOQUEO_SEGUNDOS=300`. Estado en un `dict` de
**proceso** (visible a todas las peticiones; apropiado para el despliegue
mono-proceso de NiceGUI). bcrypt encarece cada intento; el throttle lo *frena*.

### 7.6 Secretos y despliegue

- `config.py` exige `JWT_SECRET` y `STORAGE_SECRET` **independientes** (M1);
  bloquea el arranque en producción si conservan el valor por defecto (M3).
- La cookie de sesión de NiceGUI se firma con `STORAGE_SECRET` (separado del de
  JWT).
- TLS (M2): NiceGUI no termina TLS; en producción la app se sirve tras un reverse
  proxy con HTTPS y escucha solo en loopback (`HOST=127.0.0.1`). `main.py` emite
  un warning al arrancar en producción. Detalles en `docs/seguridad.md`.
- JWT (`src/infrastructure/auth/jwt_handler.py`) está preparado para una futura
  API REST (v3); la app de escritorio actual **no** consume JWT para autorizar
  (la sesión vive en la cookie firmada). La revocación de JWT se difiere a v3.

---

## 8. Roles del sistema

Enum `Rol` en `src/domain/models/usuario.py`:

| Rol | Uso |
|---|---|
| `admin` | Acceso total, gestión del sistema; opera cross-tenant |
| `director` | Configuración académica, cierre de periodos |
| `coordinador` | Seguimiento disciplinario y académico |
| `profesor` | Notas, asistencia, observaciones de sus grupos/asignaciones |
| `estudiante` | Consulta (reservado v3.0) |
| `apoderado` | Portal de acudientes (reservado v3.0) |

Conjuntos de roles reutilizados en la matriz de rutas (`main.py`): `_ADMIN`,
`_ADMIN_DIRECTOR`, `_DIRECTOR`, `_DIR_COORD`, `_AULA` (director+coordinador+
profesor), `_PROFESOR`.

---

## 9. Multi-tenant (instituciones)

Primer ladrillo del modelo multi-tenant (paso_24):

- Entidad `Institucion` (`src/domain/models/institucion.py`) + puerto
  `IInstitucionRepository` + `SqliteInstitucionRepository` + `InstitucionService`.
- La institución **#1** se siembra desde la configuración institucional
  existente y es el default de usuarios nuevos y del backfill.
- El aislamiento se aplica por el **scope de servicios** (§7.3): los servicios
  tenant-aware reciben `institucion_id` por parámetro; el scope se resuelve en el
  servicio a partir de `contexto_tenant.institucion_actual()`. Los repos siguen
  recibiendo `institucion_id` por parámetro (no importan de `services/`).

---

## 10. Design system — convención de color

En la capa de interfaz, los colores viven en el CSS del design system
(`src/interface/design/styles/` — subdividido en `themes/`, `layout/`,
`components/`, `domain/`) como variables y clases, **no** en Python. La única
excepción son los gráficos ECharts, que usan un bloque `_EC_*` al inicio del
módulo derivado de `tokens.py`. Componentes reutilizables en
`src/interface/design/components/` (botones, tablas, diálogos, badges, stat
cards, context bar/selector, etc.). Modo claro/oscuro vía `ThemeManager`.

Patrones canónicos de página en `docs/page_patterns.md`.

---

## 11. Arranque y verificación

`main.py` orquesta: logging → init BD (schema + seed) → aplicar design system →
`Container.diagnostico()` (dev) → registrar rutas (internas + UI vía
`registrar_pagina`) → `ui.run(...)`.

Verificación de entorno: **`python init.py`** (reemplazo cross-platform de
`init.sh`; modo fail-closed con gate de anti-patrones). Un paso **no** está
*done* si `python init.py` no está completamente verde. Criterios por paso y
guardarraíles de seguridad en `docs/verification.md`.

---

## 12. Documentos de referencia

| Documento | Contenido |
|---|---|
| `docs/conventions.md` | Reglas no negociables (Pydantic v2, imports, container, auditoría, solo-lectura, tenant) |
| `docs/modelos.md` | Catálogo de entidades de dominio |
| `docs/schema.md` | Referencia detallada campo a campo de los modelos |
| `docs/dominio.md` | Puertos (repositorios + servicios externos) |
| `docs/repositorio.md` | Adaptadores SQLite |
| `docs/services.md` | Casos de uso y responsabilidades por servicio |
| `docs/infraestructura.md` | Adaptadores no-BD (auth, exporters, notificaciones, contexto) |
| `docs/seguridad.md` | Decisiones de seguridad y guía de despliegue |
| `docs/page_patterns.md` | Patrones canónicos de la capa de interfaz |
| `docs/verification.md` | Criterios de *done* ejecutables |
| `docs/decisions.md` | Registro de decisiones de arquitectura (ADR) |
| `docs/api_reference.md` | Referencia por método (firma + docstring) de dominio, servicios e infraestructura, **generada automáticamente** desde el código |
