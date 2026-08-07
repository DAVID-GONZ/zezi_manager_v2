# Design: mejora_09a — Admin crea institución + director + seed automático

> **Origen:** indicaciones de David (2026-08-07).
> **Fase 1 de 3** del rediseño de gestión institucional (09a → 09b → 09c).
> **Principios:** sin migraciones (dev → schema directo + reset de BD), single source
> of truth para los catálogos estándar, provisión de un tenant nuevo 100% aislada.

---

## Problema

Hoy `InstitucionService.crear()` solo inserta la fila en `instituciones`. NO siembra
catálogos estándar (áreas, categorías) ni preferencias — eso únicamente ocurre para la
institución #1 al arranque, dentro de `_seed_institucion()`. Resultado: una institución
creada desde la UI nace vacía y sin preferencias. Además no existe forma de crear el
usuario director de esa institución en el mismo flujo, ni un indicador de si el tenant
ya pasó su configuración inicial.

## Objetivo de 09a

Que un **admin** pueda, desde una página nueva, crear una institución con datos básicos
y su usuario director en una sola operación, dejando el tenant **aprovisionado**
(catálogos + preferencias sembrados) y marcado como **pendiente de configuración
inicial** (`configuracion_inicial_completa = 0`). El wizard obligatorio que consume ese
flag se construye en 09b.

---

## 1. Single source of truth — catálogos estándar

**Archivo nuevo:** `src/domain/catalogos_estandar.py`

Extraer las constantes hoy duplicadas en `seed.py` a un módulo de dominio puro (sin
dependencias de infraestructura):

```python
# src/domain/catalogos_estandar.py
"""Catálogos estándar colombianos para aprovisionar un tenant nuevo.
Fuente única consumida por el seed de arranque y por el aprovisionamiento en runtime."""

AREAS_ESTANDAR_CO: list[tuple[str, str]] = [
    ("Matemáticas", "MAT"),
    ("Ciencias Naturales y Educación Ambiental", "NAT"),
    ("Ciencias Sociales, Historia, Geografía y C. Económicas", "SOC"),
    ("Lenguaje", "LEN"),
    ("Educación Física, Recreación y Deportes", "EFI"),
    ("Educación Artística y Cultural", "ART"),
    ("Tecnología e Informática", "TEC"),
    ("Educación Ética y en Valores Humanos", "ETI"),
    ("Ciencias Económicas y Políticas", "CEP"),
    ("Filosofía", "FIL"),
    ("Idioma Extranjero", "IDI"),
    ("Educación Religiosa", "REL"),
]

CATEGORIAS_BASE_CO: list[tuple[str, bool]] = [
    ("Comportamiento positivo", True),
    ("Convivencia y normas", True),
    ("Académico", False),
    ("Responsabilidad y actitud", False),
]

PREF_DEFAULTS: list[tuple[str, str, str | None, str]] = [
    ("academicas",  "nota_minima_aprobacion_default", "60.0",    "float"),
    ("academicas",  "nota_minima_escala_default",     "0.0",     "float"),
    ("academicas",  "nota_maxima_escala_default",     "100.0",   "float"),
    ("academicas",  "numero_periodos_default",        "4",       "int"),
    ("convivencia", "modulo_convivencia_activo",      "true",    "bool"),
    ("convivencia", "modulo_alertas_activo",          "true",    "bool"),
    ("apariencia",  "color_primario",                 "#2E3192", "str"),
    ("apariencia",  "color_secundario",               "#8B90F0", "str"),
]
```

`seed.py` deja de declarar `_AREAS_ESTANDAR_CO`, `_CATEGORIAS_BASE_CO`, `_PREF_DEFAULTS`
localmente y los importa desde este módulo. Los cuerpos de `_seed_catalogos_institucion`
y `_seed_preferencias_institucion` se mantienen, solo cambian el origen de la constante.

---

## 2. Schema — flag de configuración inicial

**Archivo:** `src/infrastructure/db/schema.py`

Añadir columna al final del `CREATE TABLE IF NOT EXISTS instituciones` (después de
`calendario`):

```sql
        calendario             TEXT,
        configuracion_inicial_completa BOOLEAN NOT NULL DEFAULT 0
```

Sin `_migrate_*`. En dev se resetea la BD. La institución #1 (demo, ya configurada y en
uso) se marca `= 1` en el seed para no gatillar el wizard sobre el entorno existente.

---

## 3. Modelo de dominio

**Archivo:** `src/domain/models/institucion.py`

Añadir a `Institucion`:
```python
configuracion_inicial_completa: bool = False
```

**DTO nuevo** (en `institucion.py`) para el flujo combinado:
```python
class NuevaInstitucionConDirectorDTO(BaseModel):
    # Institución — datos básicos (la identidad completa la llena el director en 09b)
    nombre:          str
    nombre_oficial:  str | None = None
    codigo_dane:     str | None = None
    municipio:       str | None = None
    # Director
    director_usuario:         str
    director_nombre_completo: str
    director_email:           str | None = None
    # password del director: si None, el servicio genera una temporal fuerte

    @field_validator("nombre", ...)  # reutiliza normalización de nombre
```

**DTO de resultado** (en el servicio o en institucion.py):
```python
class ResultadoAprovisionamientoDTO(BaseModel):
    institucion:        Institucion
    director_usuario:   str
    password_temporal:  str | None   # para que el admin la comunique una sola vez
```

---

## 4. Repositorio — provisión aislada del tenant

El aprovisionamiento de catálogos/preferencias debe escribir en un tenant que NO es el
scope del admin (el admin es cross-tenant, scope=None). Por eso NO se reutilizan los
servicios scopeados por sesión (`guardar_area`, `crear_categoria`) — que inyectan
`institucion_actual()` y fallarían con scope None. Se delega a infraestructura con
`institucion_id` explícito.

**Puerto** `IInstitucionRepository` (`src/domain/ports/institucion_repo.py`) — añadir:
```python
@abstractmethod
def sembrar_defaults_tenant(self, institucion_id: int) -> None:
    """Siembra catálogos estándar + preferencias por defecto para un tenant nuevo.
    Idempotente (INSERT OR IGNORE)."""
```

**Repo** `sqlite_institucion_repo.py` — implementar reutilizando las funciones de seed
existentes (infra→infra permitido):
```python
def sembrar_defaults_tenant(self, institucion_id: int) -> None:
    from src.infrastructure.db.seed import (
        _seed_catalogos_institucion, _seed_preferencias_institucion,
    )
    with self._get_conn() as conn:   # mismo patrón de conexión del repo
        _seed_catalogos_institucion(conn, institucion_id)
        _seed_preferencias_institucion(conn, institucion_id)
        conn.commit()  # si la conexión no es inyectada
```

Además `_row_to_institucion`, `guardar` y `actualizar` deben incluir la nueva columna
`configuracion_inicial_completa` (bool ↔ int 0/1).

---

## 5. Servicio de aprovisionamiento

**Archivo nuevo:** `src/services/aprovisionamiento_institucion_service.py`

```python
class AprovisionamientoInstitucionService:
    def __init__(self, institucion_repo: IInstitucionRepository):
        self._repo = institucion_repo

    @requiere_escritura
    def crear_institucion_con_director(
        self, dto: NuevaInstitucionConDirectorDTO, actor_rol: str | None = None,
    ) -> ResultadoAprovisionamientoDTO:
        # 1. Unicidad de nombre
        if self._repo.existe_nombre(dto.nombre):
            raise ValueError(f"Ya existe una institución con el nombre '{dto.nombre}'.")
        # 2. Crear institución (flag=False)
        inst = self._repo.guardar(Institucion(
            nombre=dto.nombre, nombre_oficial=dto.nombre_oficial,
            codigo_dane=dto.codigo_dane, municipio=dto.municipio,
            configuracion_inicial_completa=False,
        ))
        # 3. Aprovisionar catálogos + preferencias del tenant
        self._repo.sembrar_defaults_tenant(inst.id)
        # 4. Crear director en ESE tenant (temp password + debe_cambiar)
        from container import Container
        director = Container.usuario_service().crear_usuario(
            NuevoUsuarioDTO(
                usuario=dto.director_usuario,
                nombre_completo=dto.director_nombre_completo,
                email=dto.director_email,
                rol=Rol.DIRECTOR,
                institucion_id=inst.id,
            ),
            actor_rol=actor_rol,   # "admin" — pasa RBAC
        )
        return ResultadoAprovisionamientoDTO(
            institucion=inst,
            director_usuario=director.usuario,
            password_temporal=director.password_temporal,
        )
```

> El servicio orquesta vía `Container.usuario_service()` (mismo patrón que
> `configuracion_service.crear_anio`). No importa `src.db` ni instancia repos.

**Container** (`container.py`) — añadir:
```python
@classmethod
def aprovisionamiento_service(cls):
    from src.services.aprovisionamiento_institucion_service import AprovisionamientoInstitucionService
    return cls._get_or_create(
        "aprovisionamiento_service",
        lambda: AprovisionamientoInstitucionService(cls.institucion_service()._repo),
    )
```
(Reutiliza el repo ya cableado del `institucion_service` para no duplicar wiring.)

---

## 6. Seed — marcar institución #1 como configurada

**Archivo:** `src/infrastructure/db/seed.py`

En `_seed_institucion()`, tras crear/asegurar la institución #1 y sembrar sus catálogos
y preferencias, marcarla como configurada:
```python
conn.execute(
    "UPDATE instituciones SET configuracion_inicial_completa = 1 WHERE id = ?",
    (institucion_id,),
)
```
(Solo #1 — la demo ya está configurada. Las creadas por admin nacen en 0.)

---

## 7. UI — página admin: catálogo de instituciones

**Archivo nuevo:** `src/interface/pages/admin/catalogo_instituciones.py`
**Ruta:** `/admin/instituciones` — solo `admin`.

Contenido (design system Aula Serena, colores del tema):
- **Encabezado** con `page_header` / `app_layout` (icono `apartment`).
- **Lista de instituciones** (tabla o tarjetas) mostrando: nombre, municipio, y un
  **badge de estado**: `Configurada` (verde) si `configuracion_inicial_completa`, o
  `Pendiente de configuración` (ámbar) si no.
- Botón primario **"Crear institución"** → abre `form_dialog` con dos secciones:
  1. *Datos de la institución*: nombre *, nombre oficial, código DANE, municipio.
  2. *Usuario director*: usuario *, nombre completo *, email. (Contraseña: se genera
     temporal automáticamente; no se pide.)
- Al enviar → `Container.aprovisionamiento_service().crear_institucion_con_director(dto, actor_rol=ctx.usuario_rol)`.
  - Éxito → `toast_success` + **diálogo de credenciales**: muestra usuario del director y
    la contraseña temporal **una sola vez** (con botón copiar), advirtiendo que no se
    volverá a mostrar. Refresca la lista.
  - `ValueError` → `toast_warning(str(exc))`.

> La página NO edita la identidad completa ni preferencias — eso es trabajo del director
> en el wizard (09b) y del hub (09c). Aquí solo datos básicos + director.

---

## 8. Navegación y ruta

**`src/interface/design/layout.py`** — en la sección admin de `NAV_ITEMS` (junto a
"Usuarios"/"Auditoría"), añadir un ítem **"Instituciones"** (icono `apartment`,
`"rol": ["admin"]`, `"ruta": "/admin/instituciones"`).

**`main.py`** — registrar:
```python
from src.interface.pages.admin.catalogo_instituciones import catalogo_instituciones_page
registrar_pagina("/admin/instituciones", catalogo_instituciones_page, roles=_ADMIN)
```

---

## 9. Tests

**Archivo nuevo:** `tests/unit/services/test_aprovisionamiento_service.py`
- `test_crear_institucion_con_director_ok` — devuelve institución con id, director con
  username correcto y password_temporal no vacía.
- `test_flag_inicial_false` — la institución creada tiene `configuracion_inicial_completa=False`.
- `test_siembra_defaults_llamada` — se invoca `sembrar_defaults_tenant(inst_id)` con el id nuevo.
- `test_nombre_duplicado_rechazado` — `ValueError` si el nombre ya existe.
- `test_director_en_tenant_correcto` — el `NuevoUsuarioDTO` pasado a usuario_service lleva
  `institucion_id` = id de la institución nueva y `rol=DIRECTOR`.

**Archivo nuevo/ampliado:** test de integración de seed que verifique que una institución
creada vía repo + `sembrar_defaults_tenant` tiene 12 áreas, 4 categorías y 8 preferencias.

---

## Alternativas descartadas

- **Reusar servicios scopeados (`guardar_area`, `crear_categoria`) para sembrar**: fallan
  porque inyectan `institucion_actual()` y el admin no tiene scope. Sembrar por
  infraestructura con id explícito es determinista.
- **Flag como preferencia (`setup_completo`)**: descartado por decisión de David — es
  estado de la institución, va como columna.
- **Crear institución y director en pasos separados**: David quiere un solo flujo.

---

## Fuera de alcance de 09a (van en 09b/09c)

- Wizard de configuración inicial obligatoria y su gate en el guard → **09b**.
- Pantalla de espera para no-directores → **09b**.
- Hub editable de identidad/preferencias/colores → **09c**.
