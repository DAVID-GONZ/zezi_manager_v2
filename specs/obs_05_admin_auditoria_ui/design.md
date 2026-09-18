# Diseño: Auditoría en admin — filtro institución, paginación y KPIs (obs_05)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/interface/presenters/admin/auditoria_presenter.py` | Añadir `institucion_id` al estado; `set_institucion()`; `hay_siguiente_cambios`, `hay_siguiente_sesiones`; `construir_filtro()` pasa `institucion_id`. |
| `src/interface/pages/admin/auditoria.py` | Filtro institución (solo admin); controles Anterior/Siguiente; `_POR_PAGINA = 50`. |
| `src/interface/pages/inicio.py` | Sección KPIs de uso para admin usando `stats_grid`. |

## 2. Cambios en AuditoriaPresenter

```python
def __init__(self) -> None:
    self.estado: dict = {
        "desde": None,
        "hasta": None,
        "usuario_id": None,
        "institucion_id": None,          # NUEVO (Hueco A)
        "pagina": 1,
        "tabla": None,
        "accion": None,
        "tipo_evento": None,
        "cambios": [],
        "sesiones": [],
        "integridad": None,
        "hay_siguiente_cambios": False,  # NUEVO (Hueco B)
        "hay_siguiente_sesiones": False, # NUEVO (Hueco B)
    }

# NUEVO
def set_institucion(self, valor) -> None:
    self.estado["institucion_id"] = self.a_int(valor)

# MODIFICADO: añadir institucion_id al DTO
def construir_filtro(self, por_pagina: int) -> FiltroAuditoriaDTO:
    return FiltroAuditoriaDTO(
        usuario_id=self.estado["usuario_id"],
        tabla=self.estado["tabla"] or None,
        accion=self.estado["accion"] or None,
        tipo_evento=self.estado["tipo_evento"] or None,
        desde=self.parsear_fecha(self.estado["desde"]),
        hasta=self.parsear_fecha(self.estado["hasta"], fin_de_dia=True),
        institucion_id=self.estado["institucion_id"],  # NUEVO
        pagina=self.estado["pagina"],
        por_pagina=por_pagina,
    )
```

## 3. Estrategia look-ahead (Hueco B)

No se añade `COUNT(*)` al repositorio. La página solicita `_POR_PAGINA + 1`
registros y detecta si hay siguiente:

```python
# En auditoria.py
_POR_PAGINA = 50  # reducido de 100

def _cargar_cambios() -> None:
    try:
        raw = list(
            Container.auditoria_service().listar_cambios(
                presenter.construir_filtro(_POR_PAGINA + 1)
            )
        )
        presenter.estado["hay_siguiente_cambios"] = len(raw) > _POR_PAGINA
        presenter.set_cambios(raw[:_POR_PAGINA])   # truncar el registro extra
    except Exception as exc:
        logger.error("Error al cargar cambios: %s", exc)
        presenter.set_cambios([])
        presenter.estado["hay_siguiente_cambios"] = False

def _cargar_sesiones() -> None:
    try:
        raw = list(
            Container.auditoria_service().listar_eventos_sesion(
                presenter.construir_filtro(_POR_PAGINA + 1)
            )
        )
        presenter.estado["hay_siguiente_sesiones"] = len(raw) > _POR_PAGINA
        presenter.set_sesiones(raw[:_POR_PAGINA])
    except Exception as exc:
        logger.error("Error al cargar sesiones: %s", exc)
        presenter.set_sesiones([])
        presenter.estado["hay_siguiente_sesiones"] = False
```

## 4. Controles de navegación (Hueco B)

Los controles Anterior/Siguiente se añaden al final de cada tab, dentro de
`tabla_cambios()` y `tabla_sesiones()` respectivamente. Solo se muestran si
hay algo que paginar (pagina > 1 o hay_siguiente):

```python
# Al final de tabla_cambios() (dentro del @ui.refreshable)
pagina = _s["pagina"]
hay_sig = _s["hay_siguiente_cambios"]
if pagina > 1 or hay_sig:
    with ui.row().classes("form-row-center u-mt-md"):
        btn_secondary(
            "Anterior",
            on_click=lambda: _ir_pagina(pagina - 1, "cambios"),
            icon="chevron_left",
            size="sm",
        ).props("flat" if pagina <= 1 else "").set_enabled(pagina > 1)
        ui.label(f"Página {pagina}").classes("text-sm self-center px-2")
        btn_secondary(
            "Siguiente",
            on_click=lambda: _ir_pagina(pagina + 1, "cambios"),
            icon="chevron_right",
            size="sm",
        ).props("flat" if not hay_sig else "").set_enabled(hay_sig)
```

Función auxiliar (definida antes de los refreshables):

```python
def _ir_pagina(nueva: int, tab: str) -> None:
    presenter.set_pagina(max(1, nueva))
    if tab == "cambios":
        _cargar_cambios()
        tabla_cambios.refresh()
    else:
        _cargar_sesiones()
        tabla_sesiones.refresh()
```

## 5. Filtro por institución (Hueco A)

Se añade en `_render_filtros_comunes()` condicionado al rol del actor:

```python
def _render_filtros_comunes() -> None:
    with ui.row().classes("form-row-inline u-mb-lg"):
        date_range_input(...)
        filter_input(label="Usuario ID", ...)

        # Solo para admin cross-tenant
        if ctx.usuario_rol == "admin":
            _instituciones = []
            try:
                _instituciones = Container.institucion_service().listar()
            except Exception:
                pass
            inst_opts = {None: "Todas las instituciones"}
            inst_opts.update({i.id: i.nombre for i in _instituciones})
            filter_select(
                label="Institución",
                options=inst_opts,
                value=None,
                on_change=lambda e: (
                    presenter.set_institucion(e.value),
                    _on_filtros_cambio(),
                ),
                cls_extra="w-52",
            )

        btn_icon("refresh", on_click=_on_filtros_cambio, tooltip="Recargar")
```

## 6. KPIs de uso en inicio.py (Hueco C)

Se añade una función privada `_render_kpis_admin()` y se llama desde
`contenido()` para el rol admin, antes de los `_ADMIN_CARDS`:

```python
def _render_kpis_admin() -> None:
    """KPIs de uso de la plataforma para el admin (fail-open)."""
    import contextlib
    from src.interface.design.components.stats_grid import StatItem, stats_grid

    with contextlib.suppress(Exception):
        uso = Container.auditoria_service().resumen_uso(dias=7)
        stats_grid([
            StatItem(
                titulo="Logins hoy",
                valor=str(uso.logins_hoy),
                icono="login",
                variante="primary",
            ),
            StatItem(
                titulo="Usuarios activos (7 d)",
                valor=str(uso.usuarios_activos),
                icono="group",
                variante="success",
            ),
            StatItem(
                titulo="Accesos denegados (7 d)",
                valor=str(uso.accesos_denegados),
                icono="block",
                variante="warning" if uso.accesos_denegados > 0 else "neutral",
            ),
        ])

# En contenido(), rama admin:
if rol == "admin":
    _render_kpis_admin()        # NUEVO — antes de las tarjetas
    for c in _ADMIN_CARDS:
        _render_module_card_admin(c)
```

## 7. Alternativas descartadas

**Añadir `COUNT(*)` al repo para mostrar "Página X de Y".**
Requiere modificar `IAuditoriaRepository`, su implementación SQLite y los
tests de contrato. El look-ahead (fetch N+1) logra Anterior/Siguiente sin
cambiar el contrato del repo y cumple R8. Si en el futuro se quiere el total,
se añade como una segunda consulta separada.

**Mostrar los KPIs en `auditoria.py` en lugar de `inicio.py`.**
El usuario tiene que navegar a `/admin/auditoria` para verlos. El dashboard
de inicio es el primer punto de contacto; que los KPIs aparezcan ahí
convierte el dato en una señal proactiva, no reactiva.

**Paginación dentro de `data_table`.**
`data_table` ya tiene `filas_por_pagina` (paginación del cliente, en memoria).
Eso es correcto para las filas cargadas. La paginación de servidor (este paso)
controla cuántas filas llegan del backend — son niveles distintos. Deben
coexistir: `data_table(filas_por_pagina=15)` para la vista, controles
Anterior/Siguiente para el backend.

## 8. Orden de implementación recomendado

1. `auditoria_presenter.py` — añadir `institucion_id`, `set_institucion()`,
   `hay_siguiente_*`; modificar `construir_filtro()`.
2. `auditoria.py` — `_POR_PAGINA = 50`; `_cargar_cambios`/`_cargar_sesiones`
   look-ahead; filtro institución en `_render_filtros_comunes()`; controles
   Anterior/Siguiente en `tabla_cambios()` y `tabla_sesiones()`.
3. `inicio.py` — añadir `_render_kpis_admin()` y llamarla antes de
   `_ADMIN_CARDS`.
