# seguridad_02_config_secretos — Secretos separados + política de contraseñas + .env documentado

> Segundo paso del épico de seguridad. Cierra **M1**, **M4** y **B2** del
> análisis. NO toca schema ni modelos de dominio (entidades): añade una *policy*
> pura, dos campos de config y documentación. Sin puerta de PARAR.

## Contexto y decisión (David)

- **M1 — Un único secreto firma sesión y JWT.** `main.py` pasa
  `storage_secret=settings.JWT_SECRET`: el mismo secreto firma la cookie de
  sesión NiceGUI y (a futuro) los JWT. Si se filtra, ambos caen. Además el
  bloqueo del default inseguro solo aplica a JWT.
  → Introducir `STORAGE_SECRET` independiente, con el mismo blindaje de
  producción que `JWT_SECRET`.
- **M4 — Sin política de contraseñas.** `cambiar_password`/`resetear_password`
  aceptan cualquier cadena no vacía. El único check vive en la UI de
  `cambiar_password.py` (`_LONGITUD_MINIMA=8`), que es **bypasseable** (no es el
  servidor). → Policy de dominio pura + enforcement en `usuario_service`.
- **B2 — `.env.example` vacío (0 bytes).** No documenta las variables sensibles
  → riesgo de despliegue mal configurado. → Plantilla comentada.

## Scope (destino_v2)

```
config.py
main.py
src/domain/policies/password_policy.py        (NUEVO)
src/domain/policies/__init__.py
src/services/usuario_service.py
src/interface/pages/cambiar_password.py
.env.example
tests/unit/domain/test_password_policy.py     (NUEVO)
tests/unit/services/test_usuario_service.py
tests/unit/test_config_secrets.py             (NUEVO)
```

Baseline antes de empezar: `python init.py` → **1233 passed, 1 skipped**
(usar SIEMPRE `.venv/Scripts/python.exe`; el `python` global 3.9 está roto).

---

## Tareas

### T1 — `STORAGE_SECRET` separado en config — M1
- En `config.py`, añadir el campo `STORAGE_SECRET: str` (espejo de `JWT_SECRET`:
  `min_length=32`, default sentinel inseguro propio, p.ej.
  `"cambia-este-storage-secret-en-produccion"`).
- Extender el `model_validator` `verificar_jwt_seguro` (o uno análogo) para que
  **también** bloquee el arranque en `production` si `STORAGE_SECRET` contiene
  `"cambia-est"`, y solo advierta (log) en desarrollo. Mismo criterio que JWT.
- Exportar/dejar accesible vía `settings.STORAGE_SECRET`.
- **Verificación:** `.venv/Scripts/python.exe -c "from config import settings; print(settings.STORAGE_SECRET[:4])"` sin error; `check_imports` no aplica (raíz).

### T2 — `main.py` usa `STORAGE_SECRET` — M1
- Cambiar `storage_secret=settings.JWT_SECRET` → `storage_secret=settings.STORAGE_SECRET`.
- Comentario breve: secreto de cookie de sesión separado del de JWT (paso seguridad_02).
- **Nota a documentar en el reporte:** las sesiones activas se invalidan al
  cambiar el secreto de la cookie (los usuarios deben volver a iniciar sesión).
- **Verificación:** `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import main"` importa sin error.

### T3 — Policy de contraseñas (dominio puro) — M4
- Nuevo `src/domain/policies/password_policy.py` (mismo estilo que
  `rbac_usuarios.py`: funciones puras, sin infra/interfaz/IO). Constante
  `LONGITUD_MINIMA = 8`. Reglas:
  - longitud ≥ 8,
  - contiene al menos una letra y al menos un dígito,
  - distinta del `username` (comparación case-insensitive) cuando se provee.
  - API: `errores_password(password: str, *, username: str | None = None) -> list[str]`
    (lista de mensajes; vacía = válida) y
    `validar_password(password, *, username=None) -> None` (lanza `ValueError`
    con el primer/único mensaje si hay errores).
  - `requisitos_password() -> list[str]`: textos legibles de las reglas (para UI).
- Exportar desde `src/domain/policies/__init__.py`.
- **Verificación:** `.venv/Scripts/python.exe scripts/check_imports.py --layer domain` exit 0; `.venv/Scripts/python.exe -m pytest tests/unit/domain/test_password_policy.py -q`.

### T4 — Enforcement en el servicio — M4
- En `usuario_service.py`:
  - `cambiar_password(...)`: validar `password_nuevo` con `validar_password(...)`
    (pasar el username del usuario para la regla anti-igualdad) ANTES de delegar
    al auth. Propaga `ValueError` con mensaje accionable.
  - `resetear_password(...)`: si `nueva_password` viene **explícita** (no vacía),
    validarla. Si viene vacía sigue generando temporal (paso seguridad_01) —
    la temporal debe cumplir la policy por construcción (ver T5).
  - `crear_usuario(...)`: si `dto.password` viene explícita, validarla.
  - Añadir passthrough `requisitos_password() -> list[str]` (devuelve primitivos,
    para que la UI muestre las reglas sin importar dominio).
- **Verificación:** `.venv/Scripts/python.exe -m pytest tests/unit/services/test_usuario_service.py -q`
  (casos: rechaza "1234567"/"abcdefgh"/igual-al-username; acepta "Clave2026").

### T5 — Generador temporal cumple la policy — M4 (coherencia con seguridad_01)
- Revisar `_generar_password_temporal()` (añadido en seguridad_01, en
  `usuario_service.py`): garantizar **por construcción** ≥1 letra y ≥1 dígito y
  longitud ≥ 8 (que no pueda salir solo-dígitos o solo-letras). Si ya lo
  garantiza, no tocar y documentarlo.
- **Verificación:** test que genere N temporales y todas pasen `errores_password()==[]`.

### T6 — UI de `cambiar_password.py` consistente con la policy — M4
- Reemplazar el check local `_LONGITUD_MINIMA`/longitud por las reglas de la
  policy: mostrar `Container.usuario_service().requisitos_password()` como ayuda
  bajo el campo, y en el `except ValueError` surfacing del mensaje del servidor
  (sin tragar el texto de la policy).
- Mantener la regla de capas (la página NO importa `src.domain.*`; obtiene los
  textos vía el servicio).
- **Verificación:** `.venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/cambiar_password.py` exit 0; `check_imports --layer interface` exit 0.

### T7 — `.env.example` documentado — B2
- Rellenar `.env.example` con TODAS las variables relevantes, comentadas, con
  placeholders seguros (sin secretos reales): `APP_ENV`, `DATABASE_PATH`,
  `JWT_SECRET`, `STORAGE_SECRET`, `JWT_EXPIRE_MINUTES`, `HOST`, `PORT`,
  `LOG_LEVEL`. Indicar que en producción `JWT_SECRET` y `STORAGE_SECRET` deben
  ser ≥32 chars aleatorios y distintos entre sí, y sugerir
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Verificación:** archivo no vacío; `grep -c STORAGE_SECRET .env.example` ≥ 1.

### T8 — Verificación integral
- `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py` **VERDE** (≥1233 passed + nuevos).
- `.venv/Scripts/python.exe scripts/check_tasks.py`.
- `progress/impl_seguridad_02_config_secretos.md` (formato implementer.md).

## criterio_done
`STORAGE_SECRET` es independiente de `JWT_SECRET` y `main.py` firma la cookie con
él (bloqueando el default inseguro en producción); las contraseñas elegidas por
el usuario (cambiar/resetear-explícito/crear-explícito) se validan en el
servidor contra la policy de dominio (≥8, letra+dígito, ≠ username) y la temporal
la cumple por construcción; `cambiar_password.py` muestra las reglas vía el
servicio; `.env.example` documenta todas las variables; `python init.py` verde.
