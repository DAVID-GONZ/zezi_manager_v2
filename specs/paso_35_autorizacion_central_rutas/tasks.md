# paso_35 — Autorización central de rutas (denegar por defecto + fuente única)

## Contexto y decisión (David)

Hoy el enrutado (`main.py`) solo comprueba **autenticación**; la **autorización (rol)** vive opt-in dentro de cada página (27 guardas duplicadas con tuplas de strings), y hay **tres fuentes de verdad** (guarda de ruta, `NAV_ITEMS`, guarda de página) que pueden divergir (ya divergieron: `configuracion_evaluacion`). Objetivo: **denegar por defecto en la ruta**, con **una sola fuente de verdad** y el enum `Rol`.

Hallazgos a cerrar: A (autorización opt-in en página, no en ruta), B (`horarios_hub` sin guarda de rechazo), C (mismatch NAV ↔ guarda en `configuracion_evaluacion`/Configuración SIE), D (literales de rol duplicados, enum `Rol` ignorado).

**Fuera de alcance:** autorización a nivel de objeto por institución (id que pertenece a otra institución) = paso_36.

## Tareas

### T1 — Registro de rutas con guard central (deny-by-default)
- Crear un módulo de interfaz, p.ej. `src/interface/auth/route_guard.py`:
  - Un helper `registrar_pagina(ruta: str, page_fn, *, roles)` que registra el `@ui.page(ruta)` envolviendo `page_fn` con el guard. `roles` es **obligatorio** (sin default) → es imposible registrar una ruta sin declarar su acceso. Aceptar un sentinel `PUBLICO` para rutas públicas (`/`, `/login`, `/logout`) y otro `AUTENTICADO` para "cualquier usuario autenticado" (`/inicio`).
  - Guard del wrapper: `PUBLICO` → render directo; si no → `SessionContext.desde_storage()`; sin sesión → `/login`; con sesión pero rol no permitido → toast "Acceso no autorizado" + `/inicio`; OK → `page_fn()`.
  - `roles` se expresa con el enum **`Rol`** (no strings). Mantener un **registro** interno `{ruta: roles}` poblado por cada `registrar_pagina`, expuesto vía `roles_de_ruta(ruta) -> set[Rol] | PUBLICO/AUTENTICADO` para que el NAV lo consuma.
- Refactor de `main.py`: **todas** las páginas se registran vía `registrar_pagina(..., roles=...)` con la matriz de roles actual (ver más abajo). Quitar el `if not autenticado` repetido (lo hace el wrapper). Los page-fn internos ya no necesitan re-chequear (T3).

### T2 — NAV_ITEMS derivado del mismo registro (fuente única)
- En `layout.py`, `_usuario_puede_ver` consulta `roles_de_ruta(item["ruta"])` en vez de la lista `"rol"` embebida en cada item; para grupos (con `children`) el grupo es visible si algún hijo lo es. Quitar (o dejar de usar para autorización) las listas `"rol"` duplicadas del `NAV_ITEMS`. **Un solo sitio define quién ve/accede cada ruta.**
- Test: para cada `ruta` del NAV existe entrada en el registro y los roles coinciden (no drift).

### T3 — Simplificar guardas de página (sin magic strings)
- En las 27 páginas, eliminar la guarda de **rechazo** por rol redundante (ahora la aplica el wrapper de ruta). Conservar `ctx = SessionContext.desde_storage()` y las derivaciones que la página usa (`es_admin`, `es_directivo`, `puede_crear`…), pero esas derivaciones deben usar helpers basados en `Rol` (p.ej. `ctx.es_admin`/`ctx.es_directivo` ya existen) — **sin tuplas de strings de control de acceso**. Si una página necesita el conjunto de roles de su ruta, que lo lea de `roles_de_ruta`.
- Mantener el `if not ctx → /login` mínimo en páginas que se invoquen también fuera del wrapper (o confiar en el wrapper; decisión del implementer, pero sin dejar una página accesible sin sesión).

### T4 — Reconciliar B y C con la matriz correcta
- **horarios_hub (B):** registrar `/horarios` (y `/academico/horarios`, `/academico/generar-horario`) con `roles = {director, coordinador, profesor}` (los que hoy lo usan). El gateo interno de secciones se mantiene.
- **configuracion_evaluacion (C):** decidir y unificar: la ruta `/evaluacion/configuracion` es **solo profesor** (es la config del docente). Por tanto, en el NAV el ítem "Configuración SIE" debe apuntar/condicionarse correctamente: o se muestra solo a profesor, o se separa del de directivos (que van a `/admin/configuracion`). Eliminar la redirección oculta hacia `/admin/configuracion` salvo que se mantenga como conveniencia explícita; lo importante es que NAV y ruta coincidan (sin rebote sorpresa).

### Matriz de roles por ruta (fuente única — usar enum `Rol`)
- Públicas: `/`, `/login`, `/logout`.
- Autenticado (cualquiera): `/inicio`.
- `admin`: `/admin/auditoria`. (y `/diagnostico` → admin, o mantener interna)
- `admin, director`: `/admin/usuarios`.
- `director`: `/admin/grupos`, `/admin/asignaturas`, `/admin/salas`, `/admin/configuracion-institucion`, `/admin/configuracion` (SIE institucional).
- `director, coordinador`: `/admin/plan-estudios`, `/admin/disponibilidad-docente`, `/evaluacion/cierre-periodo`, `/evaluacion/cierre-anio`, `/informes/consolidado-notas`, `/informes/consolidado-asistencia`.
- `director, coordinador, profesor`: `/estudiantes`, `/admin/asignaciones`, `/horarios` (+variantes), `/evaluacion/planilla`, `/evaluacion/habilitaciones`, `/evaluacion/planes`, `/asistencia`, `/convivencia/*`, `/informes/boletin-*`, `/informes/estadisticos`, `/academico/tablero`.
- `profesor`: `/evaluacion/configuracion`.
(Verificar contra las guardas actuales y ajustar; esta matriz refleja el estado post paso_20–34. Si alguna ruta hoy tiene una guarda distinta, gana la guarda actual salvo el caso C.)

### T5 — Verificación y cierre
- `python init.py` VERDE (baseline ~1134 passed, 1 skipped; corregir fallout). check_imports + check_design en verde. `test_navitems` y demás siguen verdes/ajustados.
- **Tests de autorización (clave):** una tabla `(ruta, rol) → permitido/denegado` que recorra TODAS las rutas registradas y verifique el wrapper (rol no permitido → redirige; público → sin sesión OK; autenticado-sin-rol → /inicio). Debe cazar B y C.
- `progress/impl_paso_35.md`.

## criterio_done
Existe un registro único `ruta → roles` (enum `Rol`) y un guard de ruta que **deniega por defecto** (auth + rol) aplicado a todas las páginas vía `registrar_pagina`; `NAV_ITEMS` deriva su visibilidad del mismo registro (sin listas de rol duplicadas); las páginas ya no repiten la guarda de rechazo ni usan tuplas de strings para control de acceso; `horarios_hub` queda protegida por la ruta y el mismatch de `configuracion_evaluacion`/NAV se reconcilia; hay tests `(ruta,rol)` de autorización; `python init.py` verde.
