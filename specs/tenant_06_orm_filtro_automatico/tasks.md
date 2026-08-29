# tenant_06_orm_filtro_automatico — Filtro automatico de tenant via SQLAlchemy ORM

> **Fase 2B del plan de aislamiento multi-tenant.**
> Implementa la inyeccion automatica de `WHERE institucion_id = X` en toda
> query SELECT usando el evento `do_orm_execute` o `with_loader_criteria`
> de SQLAlchemy. Los repositorios quedan ciegos a la logica de aislamiento.
>
> **Alineacion con roadmap:** Extiende `backend_05_engine_factory` y
> `backend_07_repos_migracion`. Se ejecuta DURANTE la migracion a SQLAlchemy.

## Principio

Hoy el aislamiento depende de que cada repo agregue manualmente el WHERE.
Con el filtro automatico del ORM, el aislamiento es responsabilidad de la
infraestructura — no del desarrollador. Un repo que olvida el filtro sigue
siendo seguro porque el ORM lo inyecta.

Esto elimina la CLASE COMPLETA de bugs de fuga cross-tenant.

## Scope

```
src/infrastructure/db/tenant_filter.py          (NUEVO — hook do_orm_execute)
src/infrastructure/db/session_factory.py        (NUEVO o extension de engine_factory)
src/infrastructure/db/repositories/sqla_*.py    (repos reescritos — sin WHERE tenant manual)
tests/integration/test_tenant_orm_filter.py     (NUEVO)
```

## Tareas

### T1 — Definir el provider de tenant configurable  [ ]

Crear un callable que abstraiga la fuente del tenant:

```python
# src/infrastructure/db/tenant_provider.py
from typing import Callable, Optional

TenantProvider = Callable[[], Optional[int]]

def nicegui_tenant_provider() -> int | None:
    """Lee el tenant de app.storage.user (NiceGUI)."""
    from src.interface.context.session_context import SessionContext
    ctx = SessionContext.desde_storage()
    return ctx.institucion_id if ctx else None

def api_tenant_provider(request) -> int | None:
    """Lee el tenant de request.state.tenant (FastAPI)."""
    return getattr(request.state, "tenant", None)
```

El factory de session recibe el provider al configurarse.
- NiceGUI: usa `nicegui_tenant_provider`.
- API REST (Fase 3): usa `api_tenant_provider`.
- Tests: usa un provider fijo (`lambda: 1` o `lambda: None`).

**Verificacion:** Import sin error; unit test del provider.

### T2 — Implementar hook do_orm_execute  [ ]

```python
# src/infrastructure/db/tenant_filter.py
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

def instalar_filtro_tenant(session_factory, tenant_provider: TenantProvider):
    @event.listens_for(session_factory, "do_orm_execute")
    def _filtrar(orm_execute_state):
        if not orm_execute_state.is_select:
            return
        tenant_id = tenant_provider()
        if tenant_id is None:
            return  # admin cross-tenant — sin filtro
        # Inyectar WHERE institucion_id = tenant_id en todas las
        # entidades que hereden de TenantMixin
        orm_execute_state.statement = orm_execute_state.statement.options(
            with_loader_criteria(
                TenantMixin,
                TenantMixin.institucion_id == tenant_id,
                include_aliases=True,
            )
        )
```

**Alternativa con SQLAlchemy Core (si no se usa ORM completo):**
Si el roadmap decide SQLAlchemy Core en vez de ORM Declarative, el filtro
se implementa como un wrapper de `session.execute()` que inspecciona la
query y agrega la clausula WHERE. Mas manual pero igualmente viable.

**Decision:** Depende de si `backend_04` elige Core o Declarative. Este spec
documenta ambas opciones; la implementacion concreta se define en ese paso.

**Verificacion:** Test unitario que verifica que un SELECT sin WHERE devuelve
solo filas del tenant activo.

### T3 — Configurar en session factory  [ ]

En el factory de engine/session (`backend_05_engine_factory`):

```python
def create_session_factory(engine, tenant_provider):
    Session = sessionmaker(bind=engine)
    instalar_filtro_tenant(Session, tenant_provider)
    return Session
```

En `container.py`:
```python
# NiceGUI
session = create_session_factory(engine, nicegui_tenant_provider)
# API (Fase 3)
session = create_session_factory(engine, api_tenant_provider)
```

**Verificacion:** La app arranca y las queries estan filtradas.

### T4 — Filtro en INSERT/UPDATE (proteccion de escritura)  [ ]

El `do_orm_execute` tambien puede interceptar INSERT y UPDATE para:
- En INSERT: inyectar `institucion_id` automaticamente si no se especifico.
- En UPDATE/DELETE: agregar `AND institucion_id = ?` para evitar que un
  tenant modifique registros de otro.

```python
if orm_execute_state.is_insert:
    # Verificar que institucion_id esta seteado y coincide con el tenant
    ...
```

**NOTA:** Esto es defensa en profundidad. Los servicios ya validan con
`verificar_pertenencia()`. El filtro de ORM es la segunda barrera.

**Verificacion:** Test que intenta UPDATE de un registro de otro tenant → falla.

### T5 — Eliminar logica manual de tenant en repos  [ ]

Al reescribir los repos como `sqla_*` (roadmap `backend_07`):
- NO agregar `WHERE institucion_id = ?` manual en los SELECTs.
- El ORM lo inyecta automaticamente.
- Los repos se simplifican significativamente.

**Excepcion:** Metodos que operan cross-tenant por diseno (admin dashboards,
reportes globales) deben usar `session.execute(..., execution_options={"skip_tenant_filter": True})`.

**Verificacion:** Diff muestra que los repos nuevos no tienen logica de tenant
en sus queries.

### T6 — Tests de integracion del filtro automatico  [ ]

En `tests/integration/test_tenant_orm_filter.py`:

1. **test_select_filtrado_automaticamente:** Insertar filas en 2 instituciones.
   Con tenant_provider=1, hacer SELECT → solo filas de inst 1.

2. **test_admin_sin_filtro:** Con tenant_provider=None, SELECT → todas las filas.

3. **test_insert_inyecta_tenant:** Insertar sin especificar institucion_id →
   el hook lo inyecta del provider.

4. **test_update_no_cruza_tenant:** Con tenant_provider=1, UPDATE de fila de
   inst 2 → afecta 0 filas (o lanza error).

5. **test_skip_tenant_filter:** Con execution_option, el filtro no se aplica.

**Verificacion:** `python -m pytest tests/integration/test_tenant_orm_filter.py -v`

## Criterio de done
- [ ] TenantProvider configurable (NiceGUI / API / tests)
- [ ] Hook do_orm_execute inyecta WHERE automaticamente
- [ ] Session factory registra el hook
- [ ] Repos SQLAlchemy sin logica manual de tenant
- [ ] Tests de integracion verdes (5 scenarios)
- [ ] Admin cross-tenant intacto (provider=None → sin filtro)
- [ ] `python init.py` verde en ambos backends (SQLite + Postgres)
