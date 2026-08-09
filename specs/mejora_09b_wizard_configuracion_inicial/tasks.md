# Tasks: mejora_09b — Wizard configuración inicial + gate

**Fase 2 de 3.** Prerrequisitos: mejora_09a ✓ (columna `configuracion_inicial_completa`,
aprovisionamiento, director con contraseña temporal).

---

## T1 — Campo en el contexto de sesión

**Archivo:** `src/interface/context/session_context.py`
- Añadir campo `institucion_config_completa: bool = True` (default seguro = no
  gatea), junto a `debe_cambiar_password`.
- Incluirlo en `desde_storage()` (`storage.get("institucion_config_completa", True)`)
  y en `guardar()` (dentro del `update`).

---

## T2 — Sembrar el flag en el login

**Archivo:** `src/interface/pages/login.py`
- Tras poblar la sesión y **antes** de `ctx.guardar()` (o al construir el
  `SessionContext`), sembrar `institucion_config_completa`:
  - Si `rol_str == "admin"` → `True`.
  - Resto → `Container.institucion_service().get(inst_id).configuracion_inicial_completa`
    dentro de `try/except` con **fail-open a `True`** (un error de lectura no
    debe encerrar a nadie). Si `inst_id` es `None` → `True`.
- Persistirlo en `app.storage.user["institucion_config_completa"]` y/o en el campo
  del `SessionContext` que se guarda.
- **Regla de capas:** `login.py` ya usa `Container`; no importar `src.domain.*`.

---

## T3 — Servicio: marcar configuración completa

**Archivo:** `src/services/institucion_service.py`
- Añadir método `marcar_configuracion_inicial_completa(self, institucion_id: int)
  -> Institucion`, decorado `@requiere_escritura` (ver design.md §4).
  - `get_by_id`; si `None` → `ValueError`.
  - `self._repo.actualizar(inst.model_copy(update={"configuracion_inicial_completa": True}))`.
  - Idempotente (si ya estaba en True, no falla).
- No tocar el puerto ni el repo (reutiliza `actualizar`, que ya persiste la columna
  desde 09a).

---

## T4 — Decisión pura del gate

**Archivo:** `src/interface/auth/route_guard.py`
- Añadir constantes `GATE_OK = "ok"`, `GATE_WIZARD = "wizard"`, `GATE_ESPERA = "espera"`.
- Añadir `_RUTAS_EXENTAS_CONFIG = frozenset({"/configuracion-inicial",
  "/espera-configuracion", "/logout", "/cambiar-password"})`.
- Implementar `decidir_gate_configuracion(*, rol, config_completa, ruta) -> str`
  (función pura, ver design.md §2). Orden: admin→OK, config_completa→OK,
  ruta exenta→OK, director→WIZARD, resto→ESPERA.
- Exportar `decidir_gate_configuracion`, `GATE_OK/WIZARD/ESPERA` en `__all__`.

---

## T5 — Helper de I/O + integración en el wrapper

**Archivo:** `src/interface/auth/route_guard.py`
- Implementar `_config_inicial_completa(rol) -> bool` (ver design.md §3):
  camino rápido por `app.storage.user["institucion_config_completa"]` (default
  True); si False, re-chequeo vivo `Container.institucion_service().get(inst_id)`;
  si ya es True, actualizar la sesión y devolver True; **fail-open** en except.
- En `_pagina_protegida`, **después** del bloque `debe_cambiar_password` y
  **antes** del sync de contexto/render, insertar el gate (ver design.md §3):
  - Solo si `autenticado and rol != "admin" and ruta not in _RUTAS_EXENTAS_CONFIG`.
  - `veredicto = decidir_gate_configuracion(rol=rol,
    config_completa=_config_inicial_completa(rol), ruta=ruta)`.
  - `GATE_WIZARD` → `ui.navigate.to("/configuracion-inicial"); return`.
  - `GATE_ESPERA` → `ui.navigate.to("/espera-configuracion"); return`.
- Verificar que `_modulo_permitido` quede **después** de este gate (mover si hace
  falta; ver nota de orden en design.md §3).

---

## T6 — Página wizard `/configuracion-inicial`

**Archivo nuevo:** `src/interface/pages/configuracion_inicial.py`
- `configuracion_inicial_page()` — página **suelta** (patrón `cambiar_password.py`,
  sin `app_layout`/NAV), estética del design system, **stepper de 4 pasos**.
- **Regla de capas:** la página NO importa `src.domain.models.*`. Los DTOs que
  necesite (`ActualizarInstitucionDTO`, `ActualizarPreferenciaDTO`) se importan
  desde el **módulo de servicio** correspondiente (patrón de `usuarios.py` /
  `catalogo_instituciones.py`). Si `ActualizarInstitucionDTO` no está re-exportado
  en `institucion_service.py`, decidir: usar el servicio con primitivos o
  re-exportar el DTO en el `__all__` del servicio (documentar la decisión).
- **Prefill:** `institucion_service.get(inst_id)` + `preferencias_service.get_dto(inst_id)`.
- **Paso 1 Identidad** (obligatorios `nombre_oficial`, `rector`, `municipio`;
  resto opcional per design.md §5) → `institucion_service.actualizar(inst_id, dto)`.
  **Sin campo de logo** (gestión de imágenes diferida a un paso posterior; ver
  design.md §5 / "Fuera de alcance").
- **Paso 2 Preferencias académicas** (4 claves float/int) → `preferencias_service.set`
  por clave. Validación UI: escala `min<max`, aprobación en rango.
- **Paso 3 Módulos** (toggles `modulo_convivencia_activo`, `modulo_alertas_activo`)
  → `preferencias_service.set`.
- **Paso 4 Apariencia** (`color_primario`, `color_secundario`, color pickers;
  defaults `#2E3192`/`#8B90F0`) → `preferencias_service.set`.
- Persistencia por paso en cada "Siguiente".
- **Finalizar** (habilitado solo con obligatorios del Paso 1): persiste último
  paso → `institucion_service.marcar_configuracion_inicial_completa(inst_id)` →
  `app.storage.user["institucion_config_completa"] = True` → `toast_success` →
  `ui.navigate.to("/inicio")`.
- `ValueError` de servicio → `toast_warning(str(exc))` sin perder estado.
- Pie: enlace "Cerrar sesión" (`/logout`).
- Componentes existentes (`btn_primary`, `btn_ghost`, inputs `andes-input`,
  `toast_*`); colores del tema, **sin hex literales nuevos** salvo los defaults de
  color ya definidos como tokens. Pasar `check_design.py`.

---

## T7 — Página de espera `/espera-configuracion`

**Archivo nuevo:** `src/interface/pages/espera_configuracion.py`
- `espera_configuracion_page()` — página suelta bloqueante (estética
  `andes-login-bg`), ver design.md §6.
- Icono + título "Tu institución se está configurando" + texto explicativo.
- Botón "Reintentar" → `ui.navigate.to("/inicio")` (el guard re-chequea en vivo).
- Botón "Cerrar sesión" → `/logout`.
- Caso borde: si `app.storage.user.get("usuario_rol") == "director"`, mostrar
  botón "Ir a la configuración" → `/configuracion-inicial`.
- Sin polling. Regla de capas idéntica a T6.

---

## T8 — Registro de rutas

**Archivo:** `main.py`
- Importar `configuracion_inicial_page` y `espera_configuracion_page`.
- `registrar_pagina("/configuracion-inicial", configuracion_inicial_page, roles={Rol.DIRECTOR})`.
- `registrar_pagina("/espera-configuracion", espera_configuracion_page, roles=AUTENTICADO)`.
  (Usar los símbolos de rol/sentinel tal como ya se importan en `main.py`.)
- **`layout.py`: sin cambios** (rutas forzadas, no ítems de NAV).

---

## T9 — Tests

**Archivo nuevo:** `tests/unit/interface/auth/test_gate_configuracion.py`
Matriz de `decidir_gate_configuracion` (ver design.md §8):
- admin + sin config → OK; cualquier rol + configurado → OK.
- director + sin config + ruta normal → WIZARD; + ruta exenta → OK.
- profesor + sin config + ruta normal → ESPERA; coordinador + `/espera-configuracion` → OK.
- `/logout` y `/cambiar-password` exentas para todos → OK.

**Archivo:** `tests/unit/services/test_institucion_service.py` (o el que aplique;
si no existe uno de `InstitucionService`, crear `test_institucion_service_marcar.py`):
- `marcar_configuracion_inicial_completa` marca True y persiste (mock repo).
- idempotente si ya True.
- `ValueError` si no existe.

---

## Verificación

Tras cada tarea y al final:
```
$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q --tb=short
```
0 failed, + los nuevos. Al finalizar:
```
$env:PYTHONIOENCODING="utf-8"; python init.py
```
Verde salvo el falso positivo preexistente `login.py:16` (no introducir nuevos).

Escribir `progress/impl_mejora_09b.md` (archivos, conteo de tests, desviaciones,
decisión sobre import de DTOs en el wizard).

---

## Riesgos / notas para el implementer

- **Redirect-loop**: las 4 rutas exentas son críticas. Si el wizard o la pantalla
  de espera no están exentos, el gate los redirige a sí mismos en bucle. Verificar
  manualmente el flujo: director sin config entra a `/inicio` → `/configuracion-inicial`
  (una sola redirección, sin bucle).
- **Orden de gates**: `debe_cambiar_password` **antes** que el gate de config (un
  director con clave temporal la cambia primero). `/cambiar-password` está en las
  rutas exentas del gate de config, así que ambos gates coexisten sin bucle.
- **Fail-open**: tanto el sembrado en login como `_config_inicial_completa` deben
  fail-open a `True` (no bloquear ante errores). El gate es onboarding/UX, no
  seguridad.
- **Desbloqueo de no-directores sin re-login**: depende del re-chequeo vivo en
  `_config_inicial_completa` cuando la sesión dice False. No omitirlo.
- **Scope del director**: al persistir (identidad/preferencias/flag), el director
  está scopeado a su tenant; `actualizar`/`set` usan `institucion_id` explícito, no
  requieren que el director sea admin. Confirmar que `preferencias_service.set` no
  exige scope admin.
- **Institución #1 (demo)**: ya está marcada `configuracion_inicial_completa = 1`
  (seed de 09a); su director/usuarios no deben ver el gate. Cubierto por el camino
  rápido de sesión (flag True).
- **Import de DTO en el wizard**: `check_imports.py --layer interface` prohíbe
  `from src.domain.models.*` en páginas. Seguir el patrón ya usado
  (`catalogo_instituciones.py` importa DTOs desde el módulo de servicio). Decidir y
  documentar.
