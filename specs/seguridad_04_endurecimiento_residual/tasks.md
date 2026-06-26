# seguridad_04_endurecimiento_residual — Cierre de hallazgos Medio/Bajo restantes

> Cuarto y último paso del épico de seguridad. Cierra lo que quedó del análisis:
> **B1** (fragilidad del ContextVar) con código real, y **M2 / B3 / B4** con
> decisiones de seguridad documentadas (TLS es despliegue, no código de app;
> B3 no es vulnerabilidad; B4 es para la API v3 aún inexistente).
> NO toca schema ni modelos de dominio.

## Contexto y decisión (David)

Tras `seguridad_01/02/03` (A1,A2,M1,M3,M4,B2 cerrados), la auditoría de cobertura
dejó 4 hallazgos abiertos. Decisión: implementar lo accionable en código (B1) y
dejar registro formal de lo que es despliegue o diferido (M2, B3, B4).

- **B1 — Fragilidad del ContextVar (Bajo, REAL → código).** Hoy el modo
  solo-lectura ("Ver como") y el scope multi-tenant dependen de que CADA página
  llame `SessionContext.desde_storage()` (que sincroniza los `ContextVar` de
  `solo_lectura` e `institucion`). El `route_guard` NO lo hace: si una página de
  mutación futura olvida el paso, correría con el flag heredado. Fix estructural:
  **centralizar el sync en el guard** (`_pagina_protegida`), de modo que TODA
  petición protegida sincronice el contexto antes de renderizar,
  independientemente de lo que recuerde la página. Defensa en profundidad +
  test guardarraíl que impida la regresión.
- **M2 — Sin TLS a nivel app (Medio → despliegue/doc).** `ui.run` de NiceGUI no
  expone `ssl_certfile`/`ssl_keyfile`; el patrón correcto es un reverse proxy
  (nginx/Caddy) terminando TLS. Acción: documentar el requisito en una guía de
  despliegue, nota en `.env.example`, y un recordatorio de arranque en
  producción (log) de que la app debe servirse tras TLS.
- **B3 — `check_same_thread=False` (Bajo → aceptado).** Requisito de NiceGUI
  (acceso multihilo a SQLite); NO es una vulnerabilidad. Se documenta como
  decisión aceptada; sin cambio de código.
- **B4 — Revocación de JWT (Bajo → diferido v3).** `jwt_handler.py` no se usa en
  la app de escritorio (preparado para la API REST v3). Sin superficie de ataque
  hoy. Se documenta como diferido; sin cambio de código.

## Scope (destino_v2)

```
src/interface/auth/route_guard.py
tests/unit/interface/auth/test_route_guard.py
main.py
.env.example
docs/seguridad.md                              (NUEVO — registro de decisiones + guía despliegue)
```

Baseline antes de empezar: `python init.py` → **1281 passed, 1 skipped**
(usar SIEMPRE `.venv/Scripts/python.exe`; árbol limpio en HEAD 96e476b).

---

## Tareas

### T1 — B1: centralizar el sync de contexto en el guard  [x]
- En `route_guard.py`, dentro de `_pagina_protegida` (el wrapper que crea
  `registrar_pagina`), invocar `SessionContext.desde_storage()` (import perezoso
  de `src.interface.context.session_context`) ANTES de `page_fn(**kwargs)`, para
  que el sync de los `ContextVar` (`solo_lectura` + `institucion`) ocurra de
  forma central en cada render protegido. La llamada corre dentro del contexto de
  petición de `@ui.page` (igual que hoy en cada página), así que es segura;
  mantener el resto de la decisión (`decidir_acceso`) intacto.
- No cambiar la firma pública de `registrar_pagina`/`decidir_acceso` ni el
  comportamiento de autorización (solo añadir el efecto de sync).
- **Verificación:** `.venv/Scripts/python.exe scripts/check_imports.py --layer interface` exit 0.

### T2 — B1: test guardarraíl  [x]
- En `tests/unit/interface/auth/test_route_guard.py`, añadir un test que impida
  la regresión: verificar (a nivel de fuente/AST del módulo `route_guard`, sin
  requerir servidor NiceGUI) que el wrapper de página invoca
  `SessionContext.desde_storage` — de modo que el sync central no pueda
  eliminarse sin romper el test. (Leer primero el estilo de los tests existentes
  del archivo.)
- **Verificación:** `.venv/Scripts/python.exe -m pytest tests/unit/interface/auth/test_route_guard.py -q`.

### T3 — M2: recordatorio de TLS en producción (arranque)  [x]
- En `main.py`, en `main()` cuando `settings.is_production`, emitir un
  `logging.warning` claro recordando que la app DEBE servirse tras un reverse
  proxy con TLS (la cookie de sesión viaja en claro si se expone sin HTTPS).
  Una sola línea de log; no cambiar el arranque ni añadir flags nuevos.
- **Verificación:** `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import main"` importa sin error; `init.py` sigue verde.

### T4 — M2/B3/B4: documento de seguridad y despliegue  [x]
- Crear `docs/seguridad.md` con:
  - **Despliegue con TLS (M2):** producción detrás de reverse proxy (nginx/Caddy)
    terminando TLS; `HOST=127.0.0.1` para que solo el proxy alcance la app;
    nunca exponer `0.0.0.0` sin HTTPS. Generar secretos con
    `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
  - **Decisiones aceptadas / diferidas:** B3 (`check_same_thread=False` es
    requisito de NiceGUI, aceptado), B4 (revocación de JWT diferida a la API v3,
    `jwt_handler` hoy sin uso).
  - **Estado del épico de seguridad:** tabla con A1,A2,M1,M3,M4,B2,B1 cerrados y
    M2/B3/B4 con su tratamiento.
- **Verificación:** archivo existe y no vacío.

### T5 — M2: nota de despliegue en `.env.example`  [x]
- Añadir un bloque comentado en `.env.example` indicando que en producción
  `HOST` debe quedar tras un reverse proxy con TLS (ver `docs/seguridad.md`), sin
  introducir variables nuevas.
- **Verificación:** `grep -ci "tls\|proxy\|https" .env.example` ≥ 1.

### T6 — Verificación integral  [x]
- `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py` **VERDE** (≥1281 passed).
- `.venv/Scripts/python.exe scripts/check_tasks.py`.
- `progress/impl_seguridad_04_endurecimiento_residual.md` (formato implementer.md).

## criterio_done
El `route_guard` sincroniza el contexto (solo-lectura + tenant) de forma central
en cada render protegido, con test que impide su eliminación (B1); `docs/seguridad.md`
documenta el despliegue con TLS (M2) y las decisiones aceptadas/diferidas (B3, B4);
`main.py` avisa en producción del requisito de TLS y `.env.example` lo refleja;
`python init.py` verde sin regresiones.
