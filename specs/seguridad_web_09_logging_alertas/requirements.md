# Requisitos: Logging de seguridad y alertas (seguridad_web_09)

> **Nivel:** N1 — Primer mes en producción
> **Dificultad:** Código-Bajo (nuevo módulo de logging; no toca lógica de negocio)
> **Depende de:** S01 (para tener IP real del cliente via X-Forwarded-For)
> **Relacionado con:** la cadena de auditoría SHA-256 existente (complementa, no reemplaza)

## Contexto del problema

La cadena de auditoría existente (`audit_chain.py`) registra mutaciones de negocio con
integridad verificable. Lo que falta es logging de **eventos de seguridad operacional**:
intentos de autenticación, accesos, operaciones sensibles, y anomalías que requieren
alerta inmediata. Un deploy sin este logging deja la app ciega ante ataques activos.

## Requisitos

R1: EL SISTEMA DEBE registrar en log estructurado (JSON) los siguientes eventos de
    seguridad como mínimo:
    - Login exitoso: `username`, `ip`, `timestamp`, `rol`, `institucion_id`.
    - Login fallido: `username`, `ip`, `timestamp`, `motivo` (sin exponer si el usuario existe).
    - Logout.
    - Cambio de contraseña.
    - Operaciones de gestión de usuarios (crear, modificar rol, desactivar).
    - Activación/desactivación del modo "Ver como" (impersonación).
    - Acceso denegado por route guard o por verificar_pertenencia.

R2: LOS LOGS DE SEGURIDAD NUNCA DEBEN contener: passwords, tokens, valores de cookies,
    datos personales de alumnos más allá del ID, ni ningún secreto de configuración.

R3: EL SISTEMA DEBE tener un mecanismo de alerta para los siguientes patrones:
    - Más de N logins fallidos desde la misma IP en una ventana de tiempo (diferente
      al throttle por username; este es por IP).
    - Un usuario que accede desde una IP geográficamente inusual (si aplica).
    - Operaciones de gestión de usuarios fuera del horario habitual.
    El mecanismo mínimo aceptable es un log de nivel WARNING que pueda integrarse
    con una herramienta externa (Grafana, Sentry, o email de alerta).

R4: LOS LOGS DE PRODUCCIÓN DEBEN escribirse en archivos rotados (o hacia stdout para
    captura por el gestor de procesos) con retención mínima de 90 días. La retención
    se configura en el entorno, no en el código.

R5: EL LOGGING DE SEGURIDAD DEBE ser un módulo separado (`src/infrastructure/logging/
    security_logger.py` o similar), no mezclado con el logging de aplicación general.
    Los servicios lo llaman vía inyección o función de utilidad; nunca acceden al
    logger de seguridad directamente desde la interfaz.

R6: LOS LOGS DE SEGURIDAD DEBEN ser append-only desde el punto de vista de la app:
    el proceso de la app NUNCA tiene permisos de escritura sobre logs existentes,
    solo de append. Esto previene que un atacante que comprometa la app pueda borrar
    su rastro. (Se implementa a nivel de permisos de archivo del SO.)

R7: DEBE existir un test unitario que verifique que un evento de login fallido no
    incluye el password en el log, incluso si el password es un string largo.

## Criterio de done

- Login fallido genera una línea de log JSON con los campos de R1 y sin password.
- Acceso denegado por route guard genera log de nivel WARNING.
- `grep -i password /var/log/zeci/*.log` no retorna ningún resultado.
- Los logs sobreviven un reinicio de la app (escritos en archivo, no en memoria).
