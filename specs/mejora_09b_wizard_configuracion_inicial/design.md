# Design: mejora_09b — Wizard de configuración inicial obligatoria + gate

> **Origen:** indicaciones de David (2026-08-07).
> **Fase 2 de 3** del rediseño de gestión institucional (09a ✓ → **09b** → 09c).
> **Prerrequisitos:** mejora_09a ✓ (columna `configuracion_inicial_completa`,
> aprovisionamiento de tenant, director creado con contraseña temporal).

---

## Problema

mejora_09a deja una institución nueva **aprovisionada pero sin configurar**
(`configuracion_inicial_completa = 0`) y con un usuario director recién creado
(contraseña temporal → cambio forzado). Falta el flujo que consume ese flag: una
**ruta de configuración inicial obligatoria** que el director debe completar
antes de que la institución sea usable, y un **bloqueo** para el resto de
usuarios de ese tenant mientras tanto.

## Objetivo de 09b

1. Un **wizard obligatorio** de 4 pasos en `/configuracion-inicial`, accesible
   solo al **director**, que recoge la identidad institucional, las preferencias
   académicas, los módulos activos y la apariencia, y al finalizar marca
   `configuracion_inicial_completa = 1`.
2. Un **gate en el route guard** que, mientras el tenant no esté configurado:
   - **director** → forzado al wizard en cualquier ruta no exenta.
   - **no-director** (coordinador/profesor) → forzado a una **pantalla de espera
     bloqueante** (`/espera-configuracion`).
   - **admin** → nunca bloqueado (es cross-tenant, no pertenece a ningún tenant).
3. Tras completar el wizard, **acceso normal a todos los módulos**.

> El **hub editable** post-configuración (reeditar identidad/preferencias/colores
> cuando el tenant ya está configurado) es **09c**, fuera de alcance aquí.

---

## 1. El flag: origen, propagación y coste

El flag `configuracion_inicial_completa` es **estado de la institución** (por
tenant, compartido por todos sus usuarios), no del usuario. El gate corre en
**cada petición** (`registrar_pagina`), así que un lookup a BD por request sería
caro. Estrategia (patrón de `debe_cambiar_password`, que ya vive en sesión):

- **Login** (`login.py`, donde se puebla `app.storage.user`): al resolver el
  usuario, sembrar `institucion_config_completa` en la sesión:
  - `admin` → `True` (nunca se le aplica el gate; además su `institucion_id`
    suele ser `None`).
  - resto → el valor real de `Container.institucion_service().get(inst_id)
    .configuracion_inicial_completa`, con **fail-open a `True`** ante cualquier
    error (un fallo de lectura no debe encerrar a nadie).
- **Guard (camino rápido)**: si la sesión dice `True` → **sin gate**, coste cero.
  Es el caso masivamente común (tenants ya configurados).
- **Guard (re-chequeo en vivo)**: si la sesión dice `False`, hacer **un** lookup
  vivo `Container.institucion_service().get(inst_id).configuracion_inicial_completa`.
  - Si ya es `True` (el director terminó entretanto) → actualizar la sesión a
    `True` y **proceder** (esto desbloquea a los no-directores sin re-login).
  - Si sigue `False` → **aplicar el gate**.
  - Cualquier excepción → **fail-open** (sin gate).

Así: los tenants configurados pagan cero; solo la ventana transitoria de
onboarding (rara) hace lookups.

**`SessionContext`** (`session_context.py`): añadir campo
`institucion_config_completa: bool = True` (default seguro = no gatea),
incluirlo en `desde_storage()` y en `guardar()`. Default `True` es fail-open
coherente con los toggles de módulo (mejora_08).

---

## 2. Decisión pura del gate (testeable sin NiceGUI)

Igual que `decidir_acceso`, la lógica del gate vive en una función pura en
`route_guard.py`:

```python
GATE_OK     = "ok"        # sin bloqueo
GATE_WIZARD = "wizard"    # → /configuracion-inicial
GATE_ESPERA = "espera"    # → /espera-configuracion

# Rutas exentas del gate (no deben provocar redirect-loop):
_RUTAS_EXENTAS_CONFIG = frozenset({
    "/configuracion-inicial", "/espera-configuracion",
    "/logout", "/cambiar-password",
})

def decidir_gate_configuracion(
    *, rol: str | None, config_completa: bool, ruta: str,
) -> str:
    """
    - admin                         → OK (nunca bloqueado).
    - tenant configurado            → OK.
    - ruta exenta                   → OK (evita bucle de redirección).
    - director, tenant sin config   → WIZARD.
    - no-director, tenant sin config→ ESPERA.
    """
    if rol == "admin":
        return GATE_OK
    if config_completa:
        return GATE_OK
    if ruta in _RUTAS_EXENTAS_CONFIG:
        return GATE_OK
    if rol == "director":
        return GATE_WIZARD
    return GATE_ESPERA
```

`config_completa` que recibe la función es el valor **ya resuelto** (sesión +
re-chequeo vivo) — el wrapper hace la I/O, la función solo decide.

---

## 3. Integración en el wrapper del guard

En `registrar_pagina._pagina_protegida`, **después** del gate de
`debe_cambiar_password` (el cambio de contraseña es más fundamental: un director
con clave temporal la cambia antes de configurar) y **antes** del render:

```python
# ... tras el bloque debe_cambiar_password ...

# Gate de configuración inicial (mejora_09b): un tenant sin configurar
# bloquea a sus usuarios hasta que el director complete el wizard.
if autenticado and rol != "admin" and ruta not in _RUTAS_EXENTAS_CONFIG:
    config_completa = _config_inicial_completa(rol)   # sesión + re-chequeo vivo
    veredicto_gate = decidir_gate_configuracion(
        rol=rol, config_completa=config_completa, ruta=ruta,
    )
    if veredicto_gate == GATE_WIZARD:
        ui.navigate.to("/configuracion-inicial")
        return
    if veredicto_gate == GATE_ESPERA:
        ui.navigate.to("/espera-configuracion")
        return
```

Helper (impuro, hace la I/O y actualiza la sesión), fail-open:

```python
def _config_inicial_completa(rol: str | None) -> bool:
    """True si el tenant del usuario ya completó su configuración inicial.
    Camino rápido por sesión; re-chequeo vivo solo si la sesión dice False."""
    try:
        from nicegui import app
        if bool(app.storage.user.get("institucion_config_completa", True)):
            return True
        from container import Container
        inst_id = app.storage.user.get("institucion_id")
        if inst_id is None:
            return True   # sin tenant → no gatear
        inst = Container.institucion_service().get(inst_id)
        completa = bool(inst.configuracion_inicial_completa)
        if completa:
            app.storage.user["institucion_config_completa"] = True  # desbloqueo
        return completa
    except Exception:
        return True   # fail-open: un bug no debe encerrar al usuario
```

> Nota de orden: el gate de módulos (`_modulo_permitido`) puede quedar antes o
> después; se recomienda **después** del gate de configuración (no tiene sentido
> evaluar visibilidad de módulos de un tenant aún sin configurar). Mantener el
> orden: LOGIN → DENEGADO(rol) → debe_cambiar_password → **config_inicial** →
> módulo_permitido → sync contexto → render.

---

## 4. Servicio: marcar configuración completa

**Archivo:** `src/services/institucion_service.py` — añadir:

```python
@requiere_escritura
def marcar_configuracion_inicial_completa(self, institucion_id: int) -> Institucion:
    """Marca el tenant como configurado (fin del wizard de mejora_09b).
    Idempotente: si ya estaba en True, no falla."""
    inst = self._repo.get_by_id(institucion_id)
    if inst is None:
        raise ValueError(f"La institución con id {institucion_id} no existe.")
    return self._repo.actualizar(
        inst.model_copy(update={"configuracion_inicial_completa": True})
    )
```

Reutiliza `repo.actualizar` (que ya persiste la columna desde 09a). El director
tiene escritura (no es solo-lectura) y su scope es su propio tenant; `actualizar`
usa el id explícito. No hace falta método nuevo de repo ni tocar el puerto.

> **No** se añade un servicio orquestador nuevo: el wizard reutiliza servicios
> existentes (`institucion_service.actualizar`, `preferencias_service.set`) por
> paso, y llama a `marcar_configuracion_inicial_completa` solo al finalizar.

---

## 5. Wizard `/configuracion-inicial` (director-only)

**Archivo nuevo:** `src/interface/pages/configuracion_inicial.py`
**Ruta:** `/configuracion-inicial` — `roles = {Rol.DIRECTOR}`.

Página **suelta** (patrón de `cambiar_password.py`: sin `app_layout`/NAV — es una
ruta forzada, no un ítem de menú), con estética del design system (fondo
`andes-login-bg` o un contenedor centrado equivalente) y un **stepper** de 4
pasos. Colores del tema; sin hex literales nuevos.

**Persistencia por paso** (robustez): cada "Siguiente" guarda ese paso vía su
servicio. Si el director abandona, lo guardado permanece, el flag sigue en 0 y al
volver el wizard **reprellena** desde los valores actuales
(`institucion_service.get(inst_id)` + `preferencias_service.get_dto(inst_id)`).

### Paso 1 — Identidad institucional
Campos (→ `ActualizarInstitucionDTO`, vía `institucion_service.actualizar`):
- **Obligatorios**: `nombre_oficial`, `rector`, `municipio`.
- Opcionales: `codigo_dane` (12 dígitos, validado por el modelo), `direccion`,
  `telefono`, `email_institucional`, `resolucion_aprobacion`, `lema`,
  `jornada_principal` (select AM/PM/UNICA), `tipo_institucion` (publica/privada),
  `calendario` (A/B).
- **Logo: fuera de alcance.** No se pide ni se muestra carga de logo en el
  wizard. La gestión de imágenes (subida/almacenamiento/servido de archivos) aún
  no tiene una implementación adecuada en el proyecto, por lo que se difiere a un
  **paso posterior dedicado** (no 09b ni 09c). Los campos `logo_path`/`logo_url`
  del modelo existen pero quedan sin UI aquí.

### Paso 2 — Preferencias académicas
Campos (→ `preferencias_service.set` por clave; claves de `CLAVES_CONOCIDAS`):
- `nota_minima_aprobacion_default` (float)
- `nota_minima_escala_default` (float)
- `nota_maxima_escala_default` (float)
- `numero_periodos_default` (int, típ. 4)
- Prefill desde `preferencias_service.get_dto(inst_id)` (defaults heredados del
  design system / catálogos estándar sembrados en 09a).
- Validación de UI mínima: escala `min < max`, nota aprobación dentro del rango.

### Paso 3 — Módulos
Toggles (→ `preferencias_service.set`):
- `modulo_convivencia_activo` (bool)
- `modulo_alertas_activo` (bool)
- Texto explicativo: al desactivar convivencia, sus páginas/NAV se ocultan
  (mejora_08). Sin obligatoriedad de valor (ambos default `True`).

### Paso 4 — Apariencia
Campos (→ `preferencias_service.set`):
- `color_primario` (color picker; default `#2E3192`)
- `color_secundario` (color picker; default `#8B90F0`)
- Los defaults son los tokens de Aula Serena (heredados, configurables — directriz
  de David en mejora_08).

### Finalizar
Botón "Finalizar configuración" (habilitado solo si los obligatorios del Paso 1
están completos):
1. Persiste el último paso.
2. `Container.institucion_service().marcar_configuracion_inicial_completa(inst_id)`.
3. `app.storage.user["institucion_config_completa"] = True` (desbloquea el gate en
   esta sesión, igual que `cambiar_password` limpia su flag).
4. `toast_success` + `ui.navigate.to("/inicio")`.

Manejo de errores: `ValueError` de un servicio → `toast_warning(str(exc))` sin
perder el estado del wizard.

Pie: enlace "Cerrar sesión" (`/logout`) — un director que no quiere configurar
ahora puede salir; volverá al wizard en el próximo acceso.

---

## 6. Pantalla de espera `/espera-configuracion` (no-directores)

**Archivo nuevo:** `src/interface/pages/espera_configuracion.py`
**Ruta:** `/espera-configuracion` — `roles = AUTENTICADO` (cualquier sesión; el
gate solo envía aquí a no-directores de tenants sin configurar; un director que
caiga aquí ve un botón para ir al wizard).

Página suelta bloqueante (estética `andes-login-bg`):
- Icono + título: "Tu institución se está configurando".
- Texto: "El director está preparando la plataforma. Podrás acceder cuando
  termine la configuración inicial."
- Botón **"Reintentar"** → `ui.navigate.to("/inicio")`: el guard re-chequea el
  flag en vivo; si el director ya terminó, desbloquea y entra; si no, rebota aquí.
- Botón **"Cerrar sesión"** (`/logout`).
- Si `usuario_rol == "director"` (caso borde): mostrar en su lugar un botón "Ir a
  la configuración" → `/configuracion-inicial`.

> No hay polling automático (evita complejidad/carga); el botón Reintentar cubre
> el desbloqueo manual. El re-login también funciona (login re-siembra el flag).

---

## 7. Registro de rutas y navegación

**`main.py`** — registrar ambas rutas con `registrar_pagina`:
```python
from src.interface.pages.configuracion_inicial import configuracion_inicial_page
from src.interface.pages.espera_configuracion import espera_configuracion_page
registrar_pagina("/configuracion-inicial", configuracion_inicial_page, roles={Rol.DIRECTOR})
registrar_pagina("/espera-configuracion", espera_configuracion_page, roles=AUTENTICADO)
```
(Usar el sentinel/roles según los imports ya presentes en `main.py`.)

**`layout.py`** — **sin cambios de NAV**: son rutas forzadas por el gate, no
ítems de menú. (El hub editable de 09c sí tendrá su ítem.)

**Login** (`login.py`, tras poblar la sesión y antes de `ctx.guardar()`): sembrar
`app.storage.user["institucion_config_completa"]` según §1 (True para admin;
valor real fail-open a True para el resto).

---

## 8. Tests

**`tests/unit/interface/auth/test_gate_configuracion.py`** (nuevo) — matriz de la
función pura `decidir_gate_configuracion`:
- admin + tenant sin config + ruta cualquiera → `GATE_OK`.
- director + sin config + ruta normal → `GATE_WIZARD`.
- director + sin config + `/configuracion-inicial` (exenta) → `GATE_OK`.
- profesor + sin config + ruta normal → `GATE_ESPERA`.
- coordinador + sin config + `/espera-configuracion` (exenta) → `GATE_OK`.
- cualquier rol + tenant **configurado** → `GATE_OK`.
- ruta `/logout` y `/cambiar-password` exentas para todos → `GATE_OK`.

**`tests/unit/services/test_institucion_service.py`** (o el existente que aplique)
— `marcar_configuracion_inicial_completa`:
- marca `True` y persiste (repo mock recibe `actualizar` con el flag en True).
- idempotente si ya estaba en True.
- `ValueError` si la institución no existe.

> El wrapper con NiceGUI (`_pagina_protegida`, `_config_inicial_completa`) no se
> testea end-to-end (dependencia de servidor), coherente con cómo `test_route_guard.py`
> testea solo `decidir_acceso`. La cobertura vive en la función pura + el servicio.

---

## 9. Verificación

```
$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q --tb=short
$env:PYTHONIOENCODING="utf-8"; python init.py
```
0 failed; `init.py` verde salvo el falso positivo preexistente `login.py:16`
(no introducir nuevos). Escribir `progress/impl_mejora_09b.md`.

---

## Alternativas descartadas

- **Lookup del flag en cada request sin caché de sesión**: coste de BD por
  petición para todos los usuarios; descartado a favor del camino rápido por
  sesión + re-chequeo solo cuando dice `False`.
- **Flag en sesión sin re-chequeo vivo**: los no-directores quedarían atrapados
  en la pantalla de espera hasta re-login aunque el director ya hubiera
  terminado. El re-chequeo vivo (solo mientras `False`) los desbloquea sin fricción.
- **Servicio orquestador `configurar_institucion_inicial(...)`**: acopla identidad
  + preferencias en un método; se prefiere reutilizar los servicios existentes por
  paso (persistencia incremental, validación por dominio ya existente).
- **Wizard como ítem de NAV**: es una ruta obligatoria forzada por el guard, no
  navegación libre; no va en el menú.
- **Polling automático en la pantalla de espera**: complejidad/carga innecesaria;
  el botón Reintentar + re-login cubren el desbloqueo.

---

## Fuera de alcance de 09b

**Van en 09c:**
- Hub editable de identidad/preferencias/colores con el tenant ya configurado.
- Reabrir/re-lanzar el wizard manualmente desde el hub.

**Paso posterior dedicado (gestión de imágenes):**
- Carga/almacenamiento/servido de logo institucional. Diferido por no existir aún
  una implementación adecuada de gestión de imágenes; no se aborda en 09b ni en 09c.
