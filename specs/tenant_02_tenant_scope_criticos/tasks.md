# tenant_02_tenant_scope_criticos — TenantScope obligatorio en 10 metodos criticos

> **Fase 1B del plan de aislamiento multi-tenant.**
> Define el tipo `TenantScope` y lo aplica a los 10 metodos de repositorio
> que HOY no tienen ningun parametro de `institucion_id`. Estos son los mas
> peligrosos: siempre retornan datos cross-tenant sin importar el contexto.

## Principio: Fail Fast

El patron actual `institucion_id: int | None = None` es inseguro porque
omitir el parametro es silencioso. Con `TenantScope` obligatorio (sin default),
olvidar el parametro causa `TypeError` inmediato — el bug se descubre en
desarrollo, no en produccion.

## Scope

```
src/domain/models/tenant.py                    (NUEVO — define TenantScope)
src/domain/ports/usuario_repo.py               (firma de listar_asignaciones_docente)
src/domain/ports/alerta_repo.py                (firma + FiltroAlertasDTO)
src/domain/ports/habilitacion_repo.py          (firma + FiltroHabilitacionesDTO)
src/domain/ports/infraestructura_repo.py       (4 firmas)
src/domain/ports/estadisticos_repo.py          (firmas de metodos sin tenant)
src/infrastructure/db/repositories/sqlite_usuario_repo.py
src/infrastructure/db/repositories/sqlite_alerta_repo.py
src/infrastructure/db/repositories/sqlite_habilitacion_repo.py
src/infrastructure/db/repositories/sqlite_infraestructura_repo.py
src/infrastructure/db/repositories/sqlite_estadisticos_repo.py
src/services/  (los servicios que consumen estos metodos)
```

## Tareas

### T1 — Definir TenantScope  [ ]

Crear `src/domain/models/tenant.py`:

```python
from typing import Literal, TypeAlias

TenantScope: TypeAlias = int | Literal["*"]
"""
Scope de tenant obligatorio en metodos de repositorio.

- int  → filtra por esa institucion_id (WHERE institucion_id = ?)
- "*"  → cross-tenant explicito (admin). NO aplica filtro.

Usar "*" requiere decision consciente del caller.
Omitir el parametro es un TypeError — fail fast.
"""
```

**Verificacion:** `python -c "from src.domain.models.tenant import TenantScope"` sin error.

### T2 — Migrar listar_asignaciones_docente (usuario_repo)  [ ]

**Puerto** (`src/domain/ports/usuario_repo.py`, ~linea 149):
- Agregar parametro `institucion_id: TenantScope` (obligatorio, sin default).
- Import de `TenantScope` desde `src.domain.models.tenant`.

**Repo** (`sqlite_usuario_repo.py`, ~linea 230):
- Implementar: si `institucion_id == "*"` → sin filtro; si int → JOIN a
  `usuarios` o `grupos` para filtrar por `institucion_id`.

**Servicio** que lo consume:
- Pasar `institucion_actual() or "*"` (admin = None → `"*"`).

**Verificacion:** `python init.py` verde; tests existentes pasan.

### T3 — Migrar contar_pendientes y listar_alertas (alerta_repo)  [ ]

**Puerto** (`src/domain/ports/alerta_repo.py`):
- `contar_pendientes`: agregar `institucion_id: TenantScope`.
- Agregar `institucion_id: TenantScope` a `FiltroAlertasDTO` (obligatorio).

**Repo** (`sqlite_alerta_repo.py`):
- `contar_pendientes` (~linea 172): filtrar por institucion via JOIN a
  `estudiantes.institucion_id` o `alertas → estudiantes`.
- `listar_alertas` (~linea 148): usar `filtro.institucion_id`.

**Servicios** que consumen:
- `alerta_service` (o equivalente): pasar scope.

**Verificacion:** `python init.py` verde.

### T4 — Migrar listar_planes_por_seguimiento y listar_habilitaciones (habilitacion_repo)  [ ]

**Puerto** (`src/domain/ports/habilitacion_repo.py`):
- `listar_planes_por_seguimiento`: agregar `institucion_id: TenantScope`.
- Agregar `institucion_id: TenantScope` a `FiltroHabilitacionesDTO`.

**Repo** (`sqlite_habilitacion_repo.py`):
- `listar_planes_por_seguimiento` (~linea 232): JOIN a `estudiantes` para filtrar.
- `listar_habilitaciones` (~linea 62): usar `filtro.institucion_id`.

**Verificacion:** `python init.py` verde.

### T5 — Migrar 4 metodos de infraestructura_repo  [ ]

**Puerto** (`src/domain/ports/infraestructura_repo.py`):
- `listar_grados`: agregar `institucion_id: TenantScope`.
  NOTA: `grados` es catalogo global, pero el listado debe filtrar por
  `configuracion_grado_institucion` para mostrar solo los grados habilitados
  en la institucion. Si no aplica, documentar por que.
- `listar_ventanas_grupo`: agregar `institucion_id: TenantScope`.
- `listar_limites_docente`: agregar `institucion_id: TenantScope`.
- `listar_configs_generacion`: agregar `institucion_id: TenantScope`
  (reemplazar `periodo_id: int | None = None` por parametro obligatorio o
  combinarlo con tenant scope).

**Repo** (`sqlite_infraestructura_repo.py`):
- Implementar WHERE/JOIN correspondiente en cada metodo.

**Verificacion:** `python init.py` verde.

### T6 — Migrar metodos de estadisticos_repo  [ ]

**Puerto** (`src/domain/ports/estadisticos_repo.py`):
- Auditar TODOS los metodos. Los que operan por `grupo_id` sin validar tenant
  necesitan o bien:
  a. Agregar `institucion_id: TenantScope` y verificar que `grupo_id`
     pertenece al tenant, o
  b. Documentar que la validacion se hace en el servicio (caller responsibility)
     y agregar un comentario explicito.

**Repo** (`sqlite_estadisticos_repo.py`):
- Para los metodos que acepten `institucion_id`: agregar JOIN a `grupos` o
  `estudiantes` para filtrar.

**Verificacion:** `python init.py` verde.

### T7 — Test: ningun metodo critico sin tenant  [ ]

Crear test en `tests/unit/domain/test_tenant_scope.py`:
- Importar los 10 metodos de los puertos.
- Verificar via `inspect.signature` que NINGUN parametro `institucion_id`
  tiene default (es obligatorio).
- Este test impide que alguien vuelva a agregar `= None` a estos metodos.

**Verificacion:**
```
python -m pytest tests/unit/domain/test_tenant_scope.py -v
```

## Criterio de done
- [ ] `TenantScope` definido en `src/domain/models/tenant.py`
- [ ] 10 metodos criticos migrados (puertos + repos + servicios)
- [ ] Test guardarrail de firmas verde
- [ ] `python init.py` completamente verde
- [ ] Admin sigue operando cross-tenant (pasa `"*"`)
