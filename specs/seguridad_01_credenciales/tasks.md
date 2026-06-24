# seguridad_01_credenciales — Endurecimiento de credenciales (A1 + A2)

> Deriva del análisis de seguridad (2026-06-23). Cierra los dos hallazgos
> de severidad **Alta**: fuerza bruta sin freno (A1) y contraseña por defecto
> predecible = username sin cambio forzado (A2). Es el primero de 3 pasos de
> seguridad; M1/M4/B2 → seguridad_02, M3 → seguridad_03.

## Contexto y decisión (David)

Hoy:
- `login.py` autentica sin throttle ni bloqueo → fuerza bruta / credential
  stuffing ilimitado (bcrypt rounds=12 solo encarece, no frena). Los fallos
  **no se auditan** aunque `TipoEventoSesion.LOGIN_FALLIDO` y el `CHECK` de la
  tabla `auditoria` ya lo soportan.
- `usuario_service.crear_usuario` y `resetear_password` usan `dto.usuario`
  (el username) como contraseña cuando viene vacía. Como el username es único
  global y predecible, toda cuenta nueva/reseteada nace con credencial
  conocida y **no hay obligación de cambiarla** en el primer acceso.

Decisión de diseño:
1. **A1 — Throttle/lockout en memoria** (sin schema): mecanismo neutral en la
   capa de servicios (espejo de `solo_lectura.py`/`contexto_tenant.py`),
   `ContextVar`-free, dict de proceso. Tras `MAX_INTENTOS` fallos por username
   se bloquea `BLOQUEO_SEGUNDOS`. Apropiado para el despliegue mono-proceso
   NiceGUI. Los fallos se auditan con el evento ya existente.
2. **A2 — Contraseña temporal + cambio forzado** (sí toca modelo + schema):
   - `usuarios.debe_cambiar_password BOOLEAN NOT NULL DEFAULT 0` (schema).
   - `Usuario.debe_cambiar_password: bool = False` (modelo de dominio).
   - Al crear/resetear sin contraseña explícita se genera una **temporal fuerte
     aleatoria** (`secrets`) y se marca `debe_cambiar_password=True`; el servicio
     **devuelve la temporal** para que el admin la comunique (no se imprime en
     logs).
   - Tras login, si `debe_cambiar_password` está activo, el guard fuerza
     `/cambiar-password` y bloquea el resto de rutas hasta que se cambie.

> ⚠️ **PUERTA DE APROBACIÓN (leader.md: "el paso requiere cambiar esquema de BD
> o modelos de dominio" → PARAR y reportar a David).** Las tareas **T3 y T4**
> cambian `Usuario` y la tabla `usuarios`. No se implementa nada hasta que
> David apruebe este spec.

## Scope (destino_v2)

```
src/services/login_throttle.py                 (NUEVO)
src/interface/pages/login.py
src/interface/pages/cambiar_password.py        (NUEVO)
main.py                                         (registrar ruta /cambiar-password)
src/domain/models/usuario.py
src/infrastructure/db/schema.py
src/infrastructure/db/repositories/sqlite_usuario_repo.py
src/domain/ports/usuario_repo.py
src/services/usuario_service.py
src/interface/auth/route_guard.py
src/interface/context/session_context.py
tests/unit/services/test_usuario_service.py
tests/unit/services/test_login_throttle.py     (NUEVO)
tests/integration/test_repositories.py
```

Baseline antes de empezar: `python init.py` → **1195 passed, 1 skipped**.

---

## Tareas

### T1 — `login_throttle.py` (mecanismo neutral en memoria) — A1
- Nuevo módulo en `src/services/` (sin importar interfaz ni infraestructura,
  igual que `solo_lectura.py`). Estado privado: `dict[str, _Estado]` por username
  en minúsculas.
- Constantes: `MAX_INTENTOS = 5`, `BLOQUEO_SEGUNDOS = 300` (5 min).
- API:
  - `registrar_fallo(usuario: str) -> None`
  - `registrar_exito(usuario: str) -> None`  (limpia el contador)
  - `estado_bloqueo(usuario: str) -> tuple[bool, int]`  → `(bloqueado, segundos_restantes)`
  - `reset_throttle()` para tests.
- **Verificación:** `python scripts/check_imports.py --layer services` exit 0.

### T2 — Login con throttle + auditoría de fallos — A1
- En `login.py`, antes de autenticar: si `estado_bloqueo(usuario)` indica
  bloqueado → mensaje "Demasiados intentos. Espera N s." y abortar (sin tocar
  el servicio de auth).
- En el `except ValueError` de credenciales inválidas → `registrar_fallo(usuario)`
  y auditar `TipoEventoSesion.LOGIN_FALLIDO` (verificar firma de
  `auditoria_service().registrar_evento` / `EventoSesion`; el `CHECK` ya admite
  el evento). En éxito → `registrar_exito(usuario)`.
- No cambiar el wording del mensaje genérico de credenciales (anti-enumeración).
- **Verificación:** `python scripts/check_design.py --file src/interface/pages/login.py` exit 0; `check_imports --layer interface` exit 0.

### T3 — Campo de dominio `debe_cambiar_password` — A2 (CAMBIO DE MODELO)
- En `Usuario` (`usuario.py`) añadir `debe_cambiar_password: bool = False`.
  Default seguro (compatibilidad: usuarios existentes = no forzado).
- **Verificación:** `python -m pytest tests/unit/domain/ -q` y `tests/unit/services/ -q` sin regresiones.

### T4 — Columna `usuarios.debe_cambiar_password` + repo — A2 (CAMBIO DE SCHEMA)
- `schema.py`: añadir `debe_cambiar_password BOOLEAN NOT NULL DEFAULT 0` a la
  tabla `usuarios` (CREATE) **y** `ALTER TABLE ... ADD COLUMN` idempotente en la
  ruta de migración de `init_db` (no perder datos de BD existentes).
- `sqlite_usuario_repo.py`: añadir la columna a `_COLS_USUARIO`, al
  `_row_to_usuario`, al INSERT de `guardar`, y nuevo método
  `marcar_debe_cambiar_password(usuario_id, valor: bool)`.
- `usuario_repo.py` (port): declarar el nuevo método.
- **Verificación:** `python scripts/check_imports.py --layer infrastructure`;
  `python -m pytest tests/integration/test_repositories.py -q` sin regresiones
  (añadir cobertura del flag).

### T5 — Servicio: temporal fuerte + ciclo del flag — A2
- En `usuario_service.py`:
  - `@staticmethod _generar_password_temporal() -> str` usando `secrets`
    (≥12 chars, alfanumérico). NO loguear el valor.
  - `crear_usuario`: si `dto.password` viene vacío → usar temporal y
    `debe_cambiar_password=True`; **retornar la temporal** (cambiar el retorno a
    una tupla/DTO o exponerla por un canal explícito; documentar la firma nueva
    y actualizar callers en `usuarios.py` — pero `usuarios.py` NO está en scope;
    si el cambio de firma lo obliga, PARAR y reportar para ampliar scope).
  - `resetear_password`: si `nueva_password` vacía → generar temporal y marcar
    `debe_cambiar_password=True`; retornar la temporal. Si viene explícita →
    marcar `True` igualmente (admin reseteó; el dueño debe re-elegir).
  - `cambiar_password` (dueño cambia la suya): al éxito → marcar
    `debe_cambiar_password=False`.
- **Verificación:** `python -m pytest tests/unit/services/test_usuario_service.py -q`
  (casos: crear sin pass → temporal + flag; reset → flag; cambiar → flag off).

### T6 — Página `/cambiar-password` + enforcement en el guard — A2
- Nueva `cambiar_password.py`: formulario (actual, nueva, confirmar) que llama
  `usuario_service().cambiar_password(...)`; al éxito limpia el flag en storage
  y navega a `/inicio`. Patrón de página estándar (sin `app_layout` completo o
  mínimo; seguir `login.py` como referencia de página suelta).
- `main.py`: `registrar_pagina("/cambiar-password", ..., roles=AUTENTICADO)`.
- `session_context.py`: propagar `debe_cambiar_password` en `app.storage.user`
  al iniciar sesión (lo setea `login.py` desde `user_db.debe_cambiar_password`).
- `route_guard.py`: en `_pagina_protegida`, si `autenticado` y el flag de
  storage está activo y la ruta NO es `/cambiar-password` ni `/logout` →
  `ui.navigate.to("/cambiar-password")`. Deny-by-default real para el cambio
  forzado.
- **Verificación:** `check_design --file` de ambas páginas exit 0;
  `check_imports --layer interface` exit 0.

### T7 — Verificación integral
- `python init.py` **VERDE** (≥1195 passed; sumar los tests nuevos).
- `python scripts/check_tasks.py`.
- Escribir `progress/impl_seguridad_01_credenciales.md` (formato implementer.md).

## criterio_done
Tras `MAX_INTENTOS` fallos el login bloquea temporalmente y audita
`LOGIN_FALLIDO`; las cuentas creadas/reseteadas sin contraseña explícita reciben
una temporal aleatoria fuerte (nunca el username) y quedan con
`debe_cambiar_password=True`; el guard fuerza `/cambiar-password` hasta que el
dueño la cambie (lo que limpia el flag); `python init.py` verde sin regresiones.
