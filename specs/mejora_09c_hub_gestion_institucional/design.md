# Design: mejora_09c — Hub editable de gestión institucional

> **Origen:** indicaciones de David (2026-08-07).
> **Fase 3 de 3** del rediseño de gestión institucional (09a ✓ → 09b ✓ → **09c**).
> **Prerrequisitos:** mejora_09a ✓ (entidad `Institucion` con identidad
> enriquecida, flag `configuracion_inicial_completa`), mejora_09b ✓ (wizard
> obligatorio, servicio `institucion_service.actualizar`,
> `preferencias_service.set/get_dto`).

---

## Problema

Tras completar el wizard obligatorio (09b), el director de un tenant configurado
**no tiene un lugar donde re-editar** identidad, preferencias académicas,
toggles de módulos ni colores. La única página existente que edita "información
institucional" (`src/interface/pages/admin/configuracion_institucion.py`, ruta
`/admin/configuracion-institucion`) fue construida antes de que existiera la
entidad `Institucion`: escribe sobre el **snapshot de `configuracion_anio`**
(histórico por año lectivo), no sobre la entidad `Institucion` (la fuente única
introducida en mejora_06). Además carece de secciones para preferencias, módulos
y apariencia.

## Objetivo de 09c

Un **hub post-configuración** para el **director**, donde puede editar en
cualquier momento:

1. Identidad institucional (todos los campos, sin logo)
2. Preferencias académicas (nota mínima, escala, nº periodos)
3. Módulos activos (convivencia, alertas)
4. Apariencia (colores primario y secundario)

Cada sección persiste **de forma atómica** (botón "Guardar" propio) y usa los
mismos servicios que el wizard, así que la reedición es simétrica con el
onboarding.

---

## 1. Alcance del refactor

**Reemplaza** completamente la página vieja
`src/interface/pages/admin/configuracion_institucion.py` (edición del snapshot
de `configuracion_anio`). El nuevo hub edita la **entidad `Institucion`** — la
fuente única desde mejora_06.

**Qué queda intacto:**
- `configuracion_service.actualizar_info_institucional(...)` — no se elimina.
  El snapshot por año sigue siendo la vista histórica correcta para años
  cerrados y se sigue rellenando desde `institucion_service.snapshot_institucional`
  al crear un año (mejora_06). Simplemente ya no se expone UI para editarlo:
  corregir un snapshot histórico es un caso raro que se puede resolver por
  SQL/admin si aparece.
- Rutas, servicios y modelo de `Institucion`/`Preferencias`.

**Qué desaparece:**
- El archivo `src/interface/pages/admin/configuracion_institucion.py`.
- Su registro en `main.py`.
- Su ítem en `NAV_ITEMS` (`layout.py`).

**Qué se añade:**
- Nueva página `src/interface/pages/institucion/hub_institucion.py` con las 4
  secciones descritas abajo.
- Ruta `/institucion/configuracion` (`roles={Rol.DIRECTOR}`).
- Ítem de NAV renombrado.

> **Rol y ruta:** el ítem NAV actual ya está limitado a `"rol": ["director"]`
> (verificado en `layout.py:188-190`), así que el consumo era exclusivamente
> del director aunque la ruta llevara prefijo `/admin/`. La nueva ruta refleja
> la realidad. El admin **no** accede al hub (usa su propia página cross-tenant
> `/admin/instituciones` de 09a para gestión).

---

## 2. Estructura del hub

**Archivo nuevo:** `src/interface/pages/institucion/hub_institucion.py`
**Ruta:** `/institucion/configuracion`
**Roles:** `{Rol.DIRECTOR}`
**Layout:** `app_layout(ctx, contenido, page_titulo="Configuración institucional",
page_subtitulo="Identidad, preferencias, módulos y apariencia",
page_icono="settings")` — con NAV normal (no es página suelta).

Contenido: 4 tabs (`ui.tabs` + `ui.tab_panels`) — evita fatiga visual del stack
gigante y recuerda la sección activa por sesión de página.

```
[ Identidad ] [ Preferencias ] [ Módulos ] [ Apariencia ]
```

Cada tab es un panel independiente con:
- Prefill desde el servicio correspondiente al abrir la página.
- Formulario con los campos de esa sección.
- Botón **"Guardar cambios"** que persiste **solo esa sección**.
- Botón "Recargar" ghost para descartar cambios sin guardar.
- `toast_success` al guardar, `toast_warning(str(exc))` en `ValueError`.

**Persistencia atómica por sección** (no un "Guardar todo"): reduce riesgo,
facilita el manejo de errores por sección, y encaja con cómo el modelo/servicio
ya funcionan.

---

## 3. Contenido de cada sección

### 3.1 Identidad institucional
Prefill: `Container.institucion_service().get(ctx.institucion_id)`.
Campos (todos editables; los mismos que el Paso 1 del wizard):
- **Obligatorios**: `nombre` (que es el corto), `nombre_oficial`, `rector`,
  `municipio`.
- Opcionales: `codigo_dane` (12 dígitos), `nit`, `direccion`, `telefono`,
  `email_institucional`, `resolucion_aprobacion`, `lema`, `jornada_principal`
  (select AM/PM/UNICA), `tipo_institucion` (publica/privada), `calendario` (A/B).
- **Sin campo de logo** (gestión de imágenes diferida a paso posterior; ver
  memoria [[logo-gestion-imagenes-diferida]]).
Servicio: `institucion_service.actualizar(inst_id, ActualizarInstitucionDTO(...))`.

### 3.2 Preferencias académicas
Prefill: `Container.preferencias_service().get_dto(ctx.institucion_id)`.
Campos:
- `nota_minima_aprobacion_default` (float)
- `nota_minima_escala_default` (float)
- `nota_maxima_escala_default` (float)
- `numero_periodos_default` (int)
- Validación UI mínima: `min_escala < max_escala`, aprobación en rango.
Servicio: por clave, `preferencias_service.set(inst_id,
ActualizarPreferenciaDTO(clave=..., valor=str(...)))`.

### 3.3 Módulos activos
Prefill: `PreferenciasDTO.modulo_convivencia_activo` /
`.modulo_alertas_activo` desde `get_dto`.
Campos:
- Toggle `modulo_convivencia_activo` (bool)
- Toggle `modulo_alertas_activo` (bool)
- Texto explicativo (mismo del wizard): al desactivar convivencia, sus páginas
  y su ítem de NAV se ocultan (mejora_08).
Servicio: `preferencias_service.set(inst_id, ActualizarPreferenciaDTO(...,
valor="true"/"false"))`.

### 3.4 Apariencia
Prefill: `PreferenciasDTO.color_primario` / `.color_secundario` desde `get_dto`.
Campos:
- `color_primario` (`ui.color_input`, default token de Aula Serena
  `#2E3192` — heredado del `PreferenciasDTO`)
- `color_secundario` (`ui.color_input`, default `#8B90F0`)
Servicio: dos `preferencias_service.set(...)`.

**Fix del bug UX anotado en el review de 09b:** `PreferenciasDTO` ya expone los
defaults `#2E3192`/`#8B90F0` cuando no hay valor en BD; el `ui.color_input` del
hub debe inicializarse pasando `value=prefs.color_primario` (el DTO garantiza
que nunca es None para las claves conocidas). Verificar en runtime que el
picker abre con el color prefijado.

**Aplicación en vivo (nota UX, no bloqueante):** los colores nuevos se aplican
en el próximo render/recarga completa; el aplicado inmediato (sin `ui.navigate
.reload()`) requeriría integrar con `ThemeManager` en runtime, fuera de alcance
aquí. Añadir un texto ligero: "Los cambios de color se aplican al recargar."

---

## 4. Servicios y capas

**Sin cambios** en dominio, puertos, repos ni servicios. 09c reutiliza al 100%
lo que ya existe:
- `institucion_service.get`, `institucion_service.actualizar`
- `preferencias_service.get_dto`, `preferencias_service.set`

Regla de capas: la página NO importa `src.domain.models.*`. Los DTOs
(`ActualizarInstitucionDTO`, `ActualizarPreferenciaDTO`, `PreferenciasDTO`,
enums `JornadaPrincipal`/`TipoInstitucion`/`Calendario`) se importan desde los
módulos de servicio (patrón ya usado en `catalogo_instituciones.py`,
`configuracion_inicial.py`). Verificar `__all__`:
- `institucion_service.py` re-exporta `ActualizarInstitucionDTO`,
  `NuevaInstitucionDTO`, `InstitucionResumenDTO`. **Añadir**
  `JornadaPrincipal`, `TipoInstitucion`, `Calendario` al `__all__` si no
  están, o resolver los selects con strings crudos + validación por el DTO.
- `preferencias_institucion_service.py` ya re-exporta
  `ActualizarPreferenciaDTO` y `PreferenciasDTO` (mejora_09b T6).

---

## 5. Navegación y ruta

**`main.py`:**
- Registrar `/institucion/configuracion` → `hub_institucion_page`,
  `roles={Rol.DIRECTOR}`.
- **Eliminar** el registro de la ruta antigua
  `/admin/configuracion-institucion`.

**`src/interface/design/layout.py`:**
- **Reemplazar** el ítem actual `layout.py:188-190`:
  - `label`: `"Configuración institucional"` (más preciso que "Información…")
  - `icon`: `"settings"` (o mantener `"business"` si el diseño lo prefiere)
  - `ruta`: `/institucion/configuracion`
  - `rol`: `["director"]`
- El ítem sigue en la misma posición (sección lateral del director).

**Página vieja eliminada:**
- Borrar `src/interface/pages/admin/configuracion_institucion.py`.
- El servicio `configuracion_service.actualizar_info_institucional` NO se
  elimina (ver §1).

---

## 6. Tests

09c es principalmente UI + eliminación; no añade lógica de dominio ni servicio.
Los tests nuevos son mínimos:

**`tests/unit/interface/test_hub_institucion_smoke.py`** (nuevo) — smoke tests
sin levantar NiceGUI:
- La página se importa sin errores.
- `hub_institucion_page` es callable.
- No importa `src.domain.models.*` (regex sobre el archivo — refuerzo del linter
  general; opcional si `check_imports.py --layer interface` ya lo garantiza).

**Regresión sobre lo eliminado:**
- Confirmar que `test_route_guard.py` sigue verde tras remover la ruta antigua
  (el registro dinámico se re-arma con el conftest).
- Los tests existentes de `institucion_service.actualizar` y
  `preferencias_service.set/get_dto` ya cubren las llamadas del hub — no se
  duplican aquí.

**Verificación de linters** (obligatorio):
- `check_imports.py --layer interface` verde.
- `check_design.py` sobre `hub_institucion.py` verde (sin hex literales nuevos
  salvo los defaults de color que vienen del DTO, y aun así son valores de
  configuración, no clases inline).
- `check_scope.py` verde (declarar todos los archivos tocados en `destino_v2`
  desde el principio — lección de 09b).

---

## 7. Alternativas descartadas

- **Mantener la página vieja y solo añadir preferencias/módulos/colores**:
  seguiría escribiendo sobre `configuracion_anio` en identidad, contradiciendo
  la decisión de mejora_06 (Institucion como fuente única). Descartado.
- **Botón "Reabrir wizard" en el hub** (mencionado como posibilidad en el
  design de 09b): el hub ya permite editar todo; forzar el wizard requeriría
  desmarcar el flag `configuracion_inicial_completa`, con riesgo de encerrar al
  director en `/configuracion-inicial` sin necesidad. Descartado.
- **Un solo botón "Guardar todo"** al final del hub: acopla 4 llamadas
  independientes en una transacción implícita; complica el manejo de errores
  parciales y no aporta valor. Descartado a favor de guardado atómico por
  sección.
- **Admin puede entrar al hub para editar cualquier tenant**: rompe el modelo
  cross-tenant del admin (scope=None) y duplica funciones de la página
  `/admin/instituciones` (09a). Descartado; el hub es exclusivo del director.
- **Stack vertical con secciones (sin tabs)**: scroll gigantesco con 4
  secciones densas; tabs mantienen densidad visual controlada.

---

## Fuera de alcance de 09c

**Paso posterior dedicado (gestión de imágenes):**
- Carga/almacenamiento/servido de logo institucional (ver
  [[logo-gestion-imagenes-diferida]]).

**No se aborda aquí (pospuesto a futuros pasos si se necesita):**
- Aplicación en vivo de colores sin reload.
- Edición de snapshots históricos de `configuracion_anio` (raro; SQL/admin si
  aparece).
- Reordenar/renombrar el ítem NAV más allá del cambio literal.
- Preferencias adicionales fuera de las 8 conocidas (`CLAVES_CONOCIDAS`) —
  ampliar el catálogo es trabajo de otra mejora si surge.
- Un audit log dedicado del hub más allá del que ya genera cada `actualizar`
  (mejora_07 dejó `institucion_id` en `audit_log`).
