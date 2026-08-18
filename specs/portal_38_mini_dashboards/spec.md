# portal_38_mini_dashboards — Spec

## Contexto

Tras `portal_37`, `/inicio` tiene el shell del portal (topbar, saludo, resumen) y las
tarjetas de modulo derivadas del registro (`inicio.py`, `_render_card:89`, iterando
`modulos_con_pagina()`). Hoy cada tarjeta es un boton estatico: navega a la ruta principal
del modulo (`_on_card_click`, `inicio.py:50`).

Este paso convierte cada tarjeta en un **mini-dashboard**: un contenedor con **cabecera**
(titulo + boton "Ver modulo" a `ruta_principal`) y **cuerpo** con tres sub-secciones
condicionales — **Recientes**, **Alertas**, **Hitos** — donde cada item hace **deep-link**
a la ruta exacta de la accion, reduciendo clics (el usuario entra directo a la alerta, no al
modulo para luego buscarla).

Los datos se obtienen mediante una interfaz generica `PortalProvider` (una por modulo),
implementada como **pilotos** para Convivencia y Evaluacion (donde ya existen servicios que
aportan resumen/umbral y planes/habilitaciones). Los modulos sin proveedor muestran la
tarjeta sin sub-tarjetas (estado vacio), nunca un error. Se reutilizan los componentes de
dashboard ya construidos (`pending_items`, `alerts_panel`, `milestones_panel`,
`activity_feed`).

Scope: `src/domain/portal_provider.py` (nuevo, protocolo + DTOs),
`src/services/portal/__init__.py`, `src/services/portal/convivencia_provider.py`,
`src/services/portal/evaluacion_provider.py` (nuevos), `container.py`,
`src/interface/pages/inicio.py`,
`src/interface/design/styles/components/cards.css`,
`src/interface/design/styles/CLASS_CONTRACT.md`,
`tests/unit/domain/test_portal_provider.py` (nuevo),
`tests/unit/services/portal/test_pilotos.py` (nuevo).

## Requisitos (EARS)

- **R1** — DEBE existir en `domain` un protocolo `PortalProvider` con
  `recientes(ctx) -> list[SubItem]`, `alertas(ctx) -> list[SubItem]`,
  `hitos(ctx) -> list[SubItem]`, donde `SubItem` es un dataclass con `label`, `detalle`,
  `ruta_destino` y `severidad`. `domain` NO DEBE importar de `services` ni `interface`.
- **R2** — Cada tarjeta del portal DEBE tener cabecera (titulo del modulo + boton "Ver
  modulo" → `ruta_principal`) y cuerpo con las tres sub-secciones. Cada `SubItem` DEBE
  navegar a su `ruta_destino`, que DEBE estar registrada en el guard.
- **R3** — DEBEN implementarse los proveedores **piloto** de Convivencia y Evaluacion,
  obtenidos via `Container`, reutilizando servicios existentes (resumen/umbral de
  convivencia; planes/habilitaciones de evaluacion). Los modulos sin proveedor DEBEN
  mostrar la tarjeta sin sub-tarjetas (estado vacio), nunca error.
- **R4** — Las sub-secciones DEBEN reutilizar los componentes ya construidos donde aplique
  (`pending_list`, `alerts_panel`, `milestones_panel`, `activity_feed`) y respetar
  `_rol_permitido_en_ruta` / `_modulo_visible` (`layout.py:161,198`) para no mostrar modulos
  ocultos por rol o tenant.
- **R5** — El registro de proveedores DEBE vivir en `container.py`
  (`Container.portal_provider(modulo) -> PortalProvider | None`), NUNCA instanciado en la
  pagina. Serializacion con `model_dump()` (nunca `.dict()`).
- **R6** — Clases nuevas (`.portal-module-card`, `.portal-card-header`, `.portal-subcard`
  y variantes `--recientes|--alertas|--hitos`) DEBEN declararse en `CLASS_CONTRACT.md` y
  usar solo tokens.
- **R7** — DEBE existir test que falle si algun `ruta_destino` emitido por un proveedor no
  esta registrado en el guard (estilo `test_inicio_sin_rutas_muertas`).

## Diseño

### T1 — Protocolo + DTOs (`src/domain/portal_provider.py`, nuevo)

```python
@dataclass(frozen=True)
class SubItem:
    label: str
    detalle: str
    ruta_destino: str
    severidad: str            # "info" | "warning" | "error" | "success"

class PortalProvider(Protocol):
    def recientes(self, ctx) -> list[SubItem]: ...
    def alertas(self, ctx) -> list[SubItem]: ...
    def hitos(self, ctx) -> list[SubItem]: ...
```

Datos puros; el `ctx` es el `SessionContext` (rol + institucion) pasado por la pagina.

### T2 — Proveedor Convivencia (`src/services/portal/convivencia_provider.py`)

Implementa `PortalProvider` reutilizando `convivencia_service` (resumen/umbral existentes):
alertas = grupos que superan umbral → `ruta_destino=/convivencia/seguimiento`;
recientes = ultimas observaciones → `/convivencia/observaciones`; hitos = metas de
convivencia si aplica. Obtiene repos via `Container`.

### T3 — Proveedor Evaluacion (`src/services/portal/evaluacion_provider.py`)

Alertas = planes de mejoramiento vencidos / habilitaciones pendientes →
`/evaluacion/planes` o `/evaluacion/habilitaciones`; recientes = ultimo grupo calificado →
`/evaluacion/planilla`; hitos = periodos con notas completas → `/informes/estadisticos`.

### T4 — Registro en `container.py`

`Container.portal_provider(modulo)` devuelve la instancia piloto o `None`. Los modulos sin
piloto → `None`.

### T5 — Render de tarjeta (`inicio.py`)

Evolucionar `_render_card` a `_render_module_card(d, ctx)`: cabecera (`.portal-card-header`
con label + `btn` "Ver modulo") + para cada seccion, si el provider devuelve items, renderiza
el componente correspondiente en un `.portal-subcard --<seccion>`; si no hay provider o no
hay items, omite la seccion (estado vacio). Conserva `_ORDEN_POR_ROL`/`_COLOR_POR_MODULO` y
los filtros de rol/modulo existentes.

### T6 — CSS + contrato (`cards.css`, `CLASS_CONTRACT.md`)

Clases nuevas con solo tokens; declararlas en el contrato.

### T7 — Tests

`test_portal_provider.py`: contrato de `SubItem`; un proveedor stub cumple el Protocol.
`test_pilotos.py`: convivencia/evaluacion devuelven `SubItem` con `ruta_destino` registrada
en el guard (`roles_de_ruta(r) is not None`); fail-open ante repo que lanza.

## Tareas

- [ ] **T1** — Crear `portal_provider.py` (Protocol + `SubItem`).
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer domain`
- [ ] **T2** — Proveedor Convivencia reutilizando `convivencia_service`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services`
- [ ] **T3** — Proveedor Evaluacion reutilizando servicios de evaluacion.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services`
- [ ] **T4** — `Container.portal_provider(modulo)` con pilotos + `None` para el resto.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from container import Container; assert Container.portal_provider('asistencia') is None"`
- [ ] **T5** — `_render_module_card` con cabecera + sub-tarjetas condicionales.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/inicio.py`
- [ ] **T6** — CSS `.portal-module-card`/`.portal-subcard` + contrato.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all`
- [ ] **T7** — Tests de dominio + pilotos + rutas vivas.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/domain/test_portal_provider.py tests/unit/services/portal -q`

## Verificacion final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer domain
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Criterios observables (`python main.py`, con sesion): la tarjeta de Convivencia y la de
Evaluacion muestran sub-tarjetas de Recientes/Alertas/Hitos; hacer clic en una alerta
lleva directo a su ruta (p.ej. `/convivencia/seguimiento`), no a la vista general; las
tarjetas de modulos sin proveedor aparecen sin sub-tarjetas, sin error. `init.py` verde.

## Dependencias

- `portal_37_portal_shell` — provee el shell y el `ctx` del portal.
