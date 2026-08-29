# tenant_01_interceptor_eventos — Interceptor global de ContextVar en event handlers

> **Fase 1A del plan de aislamiento multi-tenant.**
> Cierra la fuga cross-tenant reportada en la auditoria sin refactorizar la app.
> Es el fix de mayor impacto: una sola intervencion cubre TODAS las paginas.

## Contexto y causa raiz

NiceGUI ejecuta los event handlers (clicks, filtros, submits de formulario) en
tasks asyncio de WebSocket distintas a la del HTTP request que renderizo la pagina.
Python `contextvars.ContextVar` NO se propaga entre tasks. El ContextVar de tenant
(`_institucion_actual`, default=None) vuelve a None en cada event handler,
lo que significa "admin/cross-tenant" — todos los servicios dejan de filtrar.

El guard central (`route_guard.py:308`) sincroniza los ContextVars antes del
render, pero eso solo cubre el render inicial. Cualquier interaccion posterior
(cambiar un filtro, crear un usuario, click en refresh) opera sin scope.

Mismo problema afecta a `solo_lectura.py` (modo "Ver como" impersonacion).

## Scope

```
src/interface/context/event_context.py          (NUEVO)
main.py                                          (registro del interceptor)
tests/unit/interface/context/test_event_context.py  (NUEVO)
```

## Tareas

### T1 — Crear el interceptor global de eventos  [ ]

Crear `src/interface/context/event_context.py` con una funcion
`instalar_interceptor_tenant()` que:

1. Importe `Client` de `nicegui.client`.
2. Guarde referencia al `Client.handle_event` original.
3. Defina un wrapper async que:
   a. Llame `SessionContext.desde_storage()` (re-sincroniza ambos ContextVars:
      `_institucion_actual` y `_solo_lectura`).
   b. Llame al `handle_event` original con los mismos args/kwargs.
4. Reemplace `Client.handle_event` con el wrapper.

**Restricciones:**
- Import perezoso de `SessionContext` dentro del wrapper (no en top-level)
  para evitar circular imports.
- El wrapper debe manejar el caso de que `desde_storage()` retorne None
  (sesion no autenticada) — en ese caso, seguir sin setear scope.
- NO envolver en try/except silencioso: si `desde_storage()` falla, el error
  debe propagarse para diagnostico.

**Verificacion:** Import del modulo sin error:
```
python -c "from src.interface.context.event_context import instalar_interceptor_tenant"
```

### T2 — Registrar el interceptor en main.py  [ ]

En `main.py`, en la funcion `main()`, ANTES de `ui.run()`:

```python
from src.interface.context.event_context import instalar_interceptor_tenant
instalar_interceptor_tenant()
```

Ubicar despues de `Container.inicializar()` y antes de `ui.run()`.

**Verificacion:** La app arranca sin error. `python init.py` verde.

### T3 — Test guardarrail del interceptor  [ ]

Crear `tests/unit/interface/context/test_event_context.py`:

1. **test_interceptor_reemplaza_handle_event:** Verificar que tras llamar
   `instalar_interceptor_tenant()`, `Client.handle_event` ya no es el original
   (es el wrapper). Comparar identidades de funcion.

2. **test_interceptor_llama_desde_storage:** Mockear `SessionContext.desde_storage`
   y verificar que el wrapper lo invoca antes de llamar al handler original.
   Usar `unittest.mock.patch`.

3. **test_interceptor_es_idempotente:** Llamar `instalar_interceptor_tenant()`
   dos veces y verificar que no se apilan wrappers (el segundo call es no-op
   o reemplaza limpiamente).

**Verificacion:**
```
python -m pytest tests/unit/interface/context/test_event_context.py -v
```

### T4 — Verificacion end-to-end manual  [ ]

1. Crear 2 instituciones de prueba con profesores distintos (si no existen en el seed).
2. Login como director de institucion A → `/director/equipo`.
3. **Cambiar un filtro** (ej: "Solo activos" checkbox) → verificar que solo
   aparecen profesores de institucion A (no de B).
4. **Crear un usuario** → verificar que se asigna a institucion A (no a #1).
5. **Click en refresh** → verificar que el listado sigue scopeado.
6. Login como admin → verificar que sigue viendo TODAS las instituciones (cross-tenant intacto).
7. Admin "Ver como" director A → verificar que el modo solo lectura se mantiene
   al interactuar con la pagina (no se puede editar).

**Criterio de done:** Los 7 puntos pasan.
