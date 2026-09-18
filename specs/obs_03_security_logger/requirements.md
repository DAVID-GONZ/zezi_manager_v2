# Requisitos: Logging de seguridad estructurado (obs_03_security_logger)

> **Contexto:** `specs/seguridad_web_09_logging_alertas/requirements.md` — requisitos S09 originales (2026-07-29).
> **Depende de:** `obs_01_huella_actor` (LOGOUT, ACCESO_DENEGADO e `ip_address` ya se emiten tras obs_01).
> **Habilita:** integración con Grafana/Sentry en la fase de comercialización.

## Estado actual (2026-09-09)

- El logging es texto plano sin rotación; `LOG_FILE=None` y no aparece en `.env.example`.
- `logger.exception` se usa 4 veces en todo el repo; de ~450 llamadas, la mayoría registra
  solo `str(exc)` sin traza.
- Hay 31 bloques `except Exception` seguidos de `pass`.
- Cobertura: 3 de 35 servicios y 0 de 21 repositorios.
- No hay manejador global de excepciones.
- `/health` devuelve 200 aunque la base esté corrupta.

---

R1: EL SISTEMA DEBE registrar en log estructurado (JSON) los siguientes eventos de
    seguridad, todos ya trazados por `AuditoriaService.registrar_evento` tras `obs_01`:
    - Login exitoso: `usuario`, `ip`, `timestamp`, `rol`, `institucion_id`.
    - Login fallido: `usuario`, `ip`, `timestamp`, `motivo` (sin exponer si el usuario existe).
    - Logout.
    - Acceso denegado por route guard o por `verificar_pertenencia`.
    - Activación/desactivación del modo "Ver como" (impersonación).
    - Operaciones de gestión de usuarios (crear, modificar rol, desactivar).

R2: LOS LOGS DE SEGURIDAD NUNCA DEBEN contener: passwords, tokens, valores de cookies,
    datos personales de alumnos más allá del ID, ni ningún secreto de configuración.
    El cumplimiento es estructural (lista blanca de campos), no depende de la disciplina
    del que llama.

R3: EL SISTEMA DEBE tener un mecanismo de alerta para más de N logins fallidos desde la
    misma IP en una ventana de tiempo configurable.
    Nivel mínimo: log `WARNING` que pueda integrarse con una herramienta externa.
    Fuera de alcance declarado: IP geográficamente inusual (exige GeoIP) y operaciones fuera
    de horario habitual (exige dato de horario por institución, que hoy no existe).

R4: LOS LOGS DE PRODUCCIÓN DEBEN escribirse en archivos rotados (o hacia stdout) con
    retención mínima de 90 días configurada en el entorno, no en el código.

R5: EL LOGGING DE SEGURIDAD DEBE residir en un módulo separado
    (`src/infrastructure/logging/security_logger.py`). Los servicios lo invocan vía
    inyección; la interfaz nunca lo toca directamente.

R6: LOS LOGS DE SEGURIDAD DEBEN ser append-only desde el punto de vista de la app.
    (Se implementa a nivel de permisos de archivo del SO; no es código. Va en el checklist
    de deploy. No verificable en el entorno Windows de desarrollo.)

R7: DEBE existir un test unitario que verifique que un evento de login fallido no incluye
    el password en el log, ni completo ni en fragmentos, incluso con un password largo.

R8: EL SISTEMA DEBE disponer de un endpoint `/health` que llame a
    `verify_db_integrity()` y devuelva 503 si la base está corrupta. Hoy responde 200
    en cualquier caso.

R9: EL SISTEMA DEBE instalar un manejador global de excepciones que registre con
    `logger.exception` las excepciones no capturadas, para que dejen stack trace en lugar
    de perderse en el log de uvicorn.

## Criterio de done

- Login fallido genera una línea de log JSON con los campos de R1 y sin password.
- Acceso denegado por route guard genera log de nivel WARNING.
- 6 logins fallidos desde la misma IP producen una línea WARNING del sistema de alerta.
- Los logs sobreviven un reinicio de la app (escritos en archivo, no en memoria).
- Con `SECURITY_LOG_MAX_BYTES` bajo, aparece el fichero rotado `.1`.
- `/health` devuelve 503 con una copia de `app.db` corrompida a propósito.
- `python scripts/init.py` verde.
