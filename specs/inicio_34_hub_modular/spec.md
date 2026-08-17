# inicio_34_hub_modular — Spec

## Contexto

La pagina de inicio (`src/interface/pages/inicio.py`, 921 lineas) es el punto de
entrada de todos los roles, pero hoy no participa del sistema de modulos. Sus
accesos rapidos viven en un dict hardcodeado `_ACCIONES` (L257-288) que duplica
el conocimiento de navegacion de `NAV_ITEMS` y nunca consulta `modulo_activo`.
Como consecuencia, cuatro de sus destinos apuntan a rutas que no existen en el
registro central: `/convivencia` (L264 profesor, L280 coordinador) y `/alertas`
(L282 coordinador, L667 pendientes del docente).

El concepto de modulo ya existe pero esta repartido en seis declaraciones
independientes que nadie verifica: `CLAVES_CONOCIDAS` y `_MODULO_A_CLAVE`
(`preferencias_institucion_service.py:16-35`), el campo del `PreferenciasDTO`
(`src/domain/models/preferencia_institucion.py`), `RUTAS_POR_MODULO`
(`route_guard.py:129-140`), la clave `requiere_modulo` por entrada del NAV
(`layout.py:72-88`) y los switches literales de `_panel_modulos`
(`hub_institucion.py:504-568`). El drift ya se materializo:
`/convivencia/reporte-periodo` esta en el NAV con `requiere_modulo` pero falta
en `RUTAS_POR_MODULO`, asi que al apagar convivencia desaparece del rail pero
sigue siendo accesible escribiendo la URL.

Ademas, los bloques `@ui.refreshable` del dashboard (`inicio.py:868` y `:878`)
estan construidos para reaccionar al grupo elegido — el comentario de
`_seccion_stats` (L171) dice "metricas del grupo del chip" — pero `inicio.py` no
importa ni renderiza `inline_selectors`, de modo que nada dispara `.refresh()` y
el profesor ve "Selecciona un grupo" (L191) sin que la pagina ofrezca donde
seleccionarlo.

Este paso aplica a los modulos el mismo tratamiento que `paso_35` aplico a los
roles: una fuente unica de verdad de la que derivan todos los consumidores.

Scope: `src/domain/modulos.py` (nuevo), `src/interface/auth/route_guard.py`,
`src/interface/design/layout.py`,
`src/services/preferencias_institucion_service.py`,
`src/interface/pages/inicio.py`,
`src/interface/pages/institucion/hub_institucion.py`,
`tests/unit/domain/test_modulos.py` (nuevo),
`tests/unit/interface/design/test_navitems.py`.

## Requisitos (EARS)

- **R1** — DEBE existir `src/domain/modulos.py` con un enum `Modulo` y un mapa
  `MODULOS: dict[Modulo, DefinicionModulo]` que declare por modulo: `label`,
  `descripcion`, `icono`, `ruta_principal`, `rutas` y `clave_preferencia`.
  El modulo DEBE vivir en `domain` y NO DEBE importar de `services` ni de
  `interface` (lo verifica `check_imports.py`).

- **R2** — `route_guard._modulo_permitido(ruta)` DEBE resolver el modulo via
  `modulo_de_ruta(ruta)`. La constante `RUTAS_POR_MODULO` NO DEBE seguir
  existiendo.

- **R3** — `layout._modulo_visible(item)` DEBE resolver el modulo desde
  `item["ruta"]`. La clave `"requiere_modulo"` NO DEBE aparecer en `NAV_ITEMS`.

- **R4** — `PreferenciasInstitucionService.modulo_activo()` DEBE conservar su
  firma actual y su comportamiento fail-open (`True` ante clave desconocida,
  valor ausente o excepcion), obteniendo la clave desde el registro en lugar de
  `_MODULO_A_CLAVE`.

- **R5** — Los modulos con `clave_preferencia = None` son nucleo: `modulo_activo`
  DEBE devolver `True` para ellos siempre. Solo `convivencia` y `alertas` DEBEN
  llevar `clave_preferencia`, reutilizando las claves ya presentes en
  `CLAVES_CONOCIDAS`. NO DEBEN anadirse claves nuevas ni cambios de schema.

- **R6** — El inicio DEBE construir sus accesos exclusivamente desde el registro,
  descartando los modulos que no pasen `_rol_permitido_en_ruta(ruta_principal,
  rol)` o `_modulo_visible`. Ningun destino del dashboard DEBE ser una ruta
  ausente de `roles_de_ruta`.

- **R7** — Los destinos rotos DEBEN quedar asi:

  | Origen | Destino hoy (roto) | Destino nuevo |
  |---|---|---|
  | Acceso rapido "Convivencia" (profesor) | `/convivencia` | `/convivencia/observaciones` |
  | Acceso rapido "Convivencia" (coordinador) | `/convivencia` | `/convivencia/observaciones` |
  | Acceso rapido "Alertas Activas" (coordinador) | `/alertas` | `/academico/tablero` |
  | Pendiente "Alertas de tus estudiantes" (`inicio.py:667`) | `/alertas` | `/academico/tablero` |

- **R8** — El modulo `alertas` DEBE declararse con `ruta_principal = None` y
  `rutas = frozenset()` (refleja que hoy no tiene pagina propia) y por tanto NO
  DEBE generar tarjeta en el hub.

- **R9** — El inicio DEBE renderizar `inline_periodo_grupo()` y su `on_change`
  DEBE invocar `stats_refreshable.refresh()` y `contexto_refreshable.refresh()`.

- **R10** — Las cuatro ramas de rol del dashboard (profesor / director /
  coordinador / admin) DEBEN conservarse. El orden de las tarjetas por rol DEBE
  declararse en un unico dict `_ORDEN_POR_ROL`; NO DEBE duplicarse rutas, iconos
  ni colores por rol.

- **R11** — `_panel_modulos()` DEBE iterar `modulos_desactivables()` en vez de
  declarar un switch literal por modulo.

- **R12** — DEBE existir un test que falle si alguna ruta de `MODULOS[*].rutas`
  no esta registrada en el guard, y otro que falle si una ruta del NAV
  pertenece a un modulo pero no figura en `MODULOS[m].rutas`. Este ultimo es el
  que habria atrapado el bug de `/convivencia/reporte-periodo`.

## Diseno

### T1 — Registro unico (`src/domain/modulos.py`, nuevo)

Datos puros, sin dependencias de runtime, para que lo importen tanto `services`
como `interface` sin romper las reglas de capa.

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Modulo(str, Enum):
    ASISTENCIA  = "asistencia"
    EVALUACION  = "evaluacion"
    ACADEMICO   = "academico"
    CONVIVENCIA = "convivencia"
    INFORMES    = "informes"
    ALERTAS     = "alertas"

@dataclass(frozen=True)
class DefinicionModulo:
    id: Modulo
    label: str
    descripcion: str
    icono: str
    ruta_principal: str | None      # None -> sin pagina propia, no genera tarjeta
    rutas: frozenset[str]           # rutas que el modulo gatea
    clave_preferencia: str | None   # None -> modulo nucleo, no desactivable
```

`MODULOS` declara (rutas tomadas del registro real de `main.py`):

| Modulo | ruta_principal | rutas gateadas | clave_preferencia |
|---|---|---|---|
| ASISTENCIA | `/asistencia` | `/asistencia` | `None` |
| EVALUACION | `/evaluacion/planilla` | `/evaluacion/*` (6 rutas) | `None` |
| ACADEMICO | `/estudiantes` | `/estudiantes`, `/horarios`, `/academico/*`, `/admin/grupos`, `/admin/asignaturas`, `/admin/plan-estudios`, `/admin/asignaciones`, `/admin/disponibilidad-docente`, `/admin/salas` | `None` |
| CONVIVENCIA | `/convivencia/observaciones` | las 8 rutas `/convivencia/*` **incluida `/convivencia/reporte-periodo`** | `modulo_convivencia_activo` |
| INFORMES | `/informes/estadisticos` | `/informes/*` (5 rutas) | `None` |
| ALERTAS | `None` | `frozenset()` | `modulo_alertas_activo` |

Helpers:

```python
def modulo_de_ruta(ruta: str) -> Modulo | None
def definicion(m: Modulo | str) -> DefinicionModulo | None
def clave_de_modulo(nombre: str) -> str | None
def modulos_desactivables() -> list[DefinicionModulo]
def modulos_con_pagina() -> list[DefinicionModulo]
```

`modulo_de_ruta` se apoya en un indice invertido `_RUTA_A_MODULO` construido una
sola vez al importar (no recorre `MODULOS` en cada peticion).

### T2 — Guard deriva del registro (`route_guard.py:129-155`)

Eliminar `RUTAS_POR_MODULO`. `_modulo_permitido` queda:

```python
def _modulo_permitido(ruta: str) -> bool:
    try:
        from container import Container
        from src.domain.modulos import modulo_de_ruta
        from src.services.contexto_tenant import institucion_actual
        m = modulo_de_ruta(ruta)
        if m is None:
            return True
        inst_id = institucion_actual()
        if inst_id is None:
            return True
        return Container.preferencias_service().modulo_activo(inst_id, m.value)
    except Exception:
        pass
    return True
```

Se conserva el fail-open actual. Esto cierra por si solo el agujero de
`/convivencia/reporte-periodo` (R12).

### T3 — NAV deriva del registro (`layout.py:72-88`, `:235-247`)

`_modulo_visible(item)` resuelve por `item["ruta"]` con `modulo_de_ruta()`, igual
que `_rol_permitido_en_ruta` ya hace con los roles. Se borra `"requiere_modulo"`
de las 5 entradas de convivencia (L72, L76, L80, L84, L88).

Limpieza asociada: la clave `"rol"` de los items **con ruta** es dato muerto desde
`paso_35` — `_usuario_puede_ver` (L226-227) resuelve por `roles_de_ruta` y nunca
la lee, y ya divergio del registro real (`/admin/grupos` declara `["director"]`
en L101 pero esta registrada `_DIR_COORD`). Se quita `"rol"` de los items con
ruta y se conserva solo en los `divider`, que es donde si decide (L230-232).

### T4 — Servicio deriva del registro (`preferencias_institucion_service.py:32-35, 72-80`)

`_MODULO_A_CLAVE` se sustituye por `clave_de_modulo()`. `modulo_activo` mantiene
firma y semantica; el caso `clave is None` ahora cubre tanto "modulo desconocido"
como "modulo nucleo", ambos -> `True`.

### T5 — Hub de modulos en el inicio (`inicio.py:254-304`)

`_seccion_acciones_rapidas(rol)` se sustituye por `_seccion_modulos(rol)`:

1. parte de `modulos_con_pagina()`;
2. descarta los que no pasan `_rol_permitido_en_ruta(d.ruta_principal, rol)`
   (helper de `layout.py` — misma fuente que el NAV);
3. descarta los que no pasan `_modulo_visible` para el tenant;
4. ordena segun `_ORDEN_POR_ROL: dict[str, tuple[Modulo, ...]]`, que conserva la
   intencion de las cuatro ramas (profesor: asistencia primero; coordinador:
   convivencia primero; director: informes primero) sin duplicar rutas.

Se conserva el markup existente `.panel-card` > `.quick-action-card` >
`.quick-action-icon` / `.action-label` / `.action-desc`, todas ya en
`CLASS_CONTRACT.md`: **no se anade CSS nuevo**. El color por tarjeta pasa a
derivarse del modulo (campo `icono` + una variante de token por modulo), no de
una tupla hardcodeada por rol.

### T6 — Selector de contexto (`inicio.py:899-913`)

Renderizar `inline_periodo_grupo()` en `contenido()`, entre `_seccion_saludo` y
`stats_refreshable`, con `on_change` cableado a `stats_refreshable.refresh()` y
`contexto_refreshable.refresh()`. Firma existente:

```python
inline_periodo_grupo(s: dict, on_change: Callable, institucion_id: int,
                     preselect_periodo: bool = True,
                     usuario_id: int | None = None, usuario_rol: str = "directivo")
```

No se crea componente nuevo. La rama admin (`_dashboard_admin`, L821-831) no lo
lleva: no tiene stats academicos.

### T7 — Panel de activacion iterativo (`hub_institucion.py:504-568`)

`_panel_modulos()` itera `modulos_desactivables()` construyendo un switch por
definicion y guardando en bucle con
`ActualizarPreferenciaDTO(clave=d.clave_preferencia, valor=str(bool(v)).lower())`.
Se conserva el markup `.form-row-between .form-box` y los botones
Recargar / Guardar cambios. `_estado_inicial()` (L76-116) pasa a inicializar
`_s["modulos"]` desde el registro.

### T8 — Limpiezas menores en `inicio.py`

- L481: la lambda captura `gid=g["grupo_id"]` pero navega a `/academico/tablero`
  fijo; se elimina la captura muerta.
- L219 y L462: `_seccion_stats_institucional` y `_seccion_grupos_atencion` llaman
  ambas a `metricas_institucionales(periodo_id, anio_id)` con los mismos
  argumentos. Se calcula una vez en `contexto_refreshable` y se pasa como
  parametro.

### T9 — Tests

`tests/unit/domain/test_modulos.py` (nuevo):
- `modulo_de_ruta` devuelve el modulo correcto y `None` para rutas libres.
- `clave_de_modulo` devuelve `None` para modulos nucleo.
- toda `clave_preferencia` declarada esta en `CLAVES_CONOCIDAS`.
- ninguna ruta pertenece a dos modulos.

`tests/unit/interface/design/test_navitems.py` (extender):
- `test_rutas_de_modulos_estan_registradas` — toda ruta de `MODULOS[*].rutas`
  cumple `roles_de_ruta(r) is not None`.
- `test_nav_sin_drift_de_modulo` — toda ruta del NAV cuyo modulo no sea `None`
  figura en `MODULOS[m].rutas`.
- `test_inicio_sin_rutas_muertas` — todas las rutas alcanzables desde
  `_seccion_modulos` y `_seccion_pendientes_docente` estan registradas.

## Tareas

- [ ] **T1** — Crear `src/domain/modulos.py` con `Modulo`, `DefinicionModulo`,
  `MODULOS`, indice invertido y los cinco helpers.
  Verificacion: `PYTHONIOENCODING=utf-8 python scripts/check_imports.py --layer domain`

- [ ] **T2** — Eliminar `RUTAS_POR_MODULO` y reescribir `_modulo_permitido` sobre
  `modulo_de_ruta`.
  Verificacion: `PYTHONIOENCODING=utf-8 python -c "from src.interface.auth import route_guard as r; assert not hasattr(r,'RUTAS_POR_MODULO')"`

- [ ] **T3** — `_modulo_visible` deriva por ruta; quitar `requiere_modulo` (x5) y
  `rol` de los items con ruta en `NAV_ITEMS`.
  Verificacion: `PYTHONIOENCODING=utf-8 python -m pytest tests/unit/interface/design/test_navitems.py -q`

- [ ] **T4** — Sustituir `_MODULO_A_CLAVE` por `clave_de_modulo()` conservando el
  fail-open de `modulo_activo`.
  Verificacion: `PYTHONIOENCODING=utf-8 python scripts/check_imports.py --layer services`

- [ ] **T5** — Sustituir `_seccion_acciones_rapidas` por `_seccion_modulos` con
  filtro de rol + modulo y `_ORDEN_POR_ROL`.
  Verificacion: `PYTHONIOENCODING=utf-8 python scripts/check_design.py --file src/interface/pages/inicio.py`

- [ ] **T6** — Anadir `inline_periodo_grupo` en `contenido()` cableado a los dos
  refreshables.
  Verificacion: `PYTHONIOENCODING=utf-8 python scripts/check_design.py --file src/interface/pages/inicio.py`

- [ ] **T7** — `_panel_modulos` iterativo sobre `modulos_desactivables()`.
  Verificacion: `PYTHONIOENCODING=utf-8 python scripts/check_design.py --file src/interface/pages/institucion/hub_institucion.py`

- [ ] **T8** — Limpiezas: captura muerta L481, doble consulta L219/L462.
  Verificacion: `PYTHONIOENCODING=utf-8 python -m pytest tests/unit/interface -q`

- [ ] **T9** — Tests nuevos de dominio y extension de `test_navitems.py`.
  Verificacion: `PYTHONIOENCODING=utf-8 python -m pytest tests/unit/domain/test_modulos.py tests/unit/interface/design/test_navitems.py -q`

## Verificacion final

```
PYTHONIOENCODING=utf-8 python scripts/check_imports.py --layer domain
PYTHONIOENCODING=utf-8 python scripts/check_imports.py --layer services
PYTHONIOENCODING=utf-8 python scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 python scripts/check_design.py --file src/interface/pages/inicio.py
PYTHONIOENCODING=utf-8 python scripts/check_design.py --file src/interface/pages/institucion/hub_institucion.py
PYTHONIOENCODING=utf-8 python -m pytest tests/unit -q
PYTHONIOENCODING=utf-8 python init.py
```

Criterios de aceptacion observables, con `python main.py` y smoke por rol, con el
modulo de convivencia primero activo y despues apagado desde
`/institucion/configuracion` > Modulos:

1. **profesor** — al elegir grupo y periodo en el selector, las cuatro stat cards
   pasan de "Selecciona un grupo" a valores reales; hoy no hay forma de lograrlo.
   Ninguna tarjeta del hub rebota a `/inicio`. "Alertas de tus estudiantes" abre
   `/academico/tablero`.
2. **coordinador** — la tarjeta "Convivencia" abre `/convivencia/observaciones`;
   "Alertas Activas" abre `/academico/tablero`.
3. **director** — el panel Modulos lista los desactivables leyendolos del
   registro y el toggle persiste tras recargar.
4. **admin** — `_dashboard_admin` sin cambios de comportamiento observable.
5. **Con convivencia apagada** — desaparece del rail, del hub del inicio, y
   `/convivencia/reporte-periodo` escrito a mano redirige a `/inicio`. Hoy **no**
   lo hace: esa es la regresion que cierra este paso.
6. `init.py` completamente verde.
