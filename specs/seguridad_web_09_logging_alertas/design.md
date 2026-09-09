# Diseño: Logging de seguridad y alertas (seguridad_web_09)

> **Requisitos:** `requirements.md` de esta misma carpeta (R1–R7), redactado 2026-07-29.
> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §3.
> **Depende de:** `obs_01_huella_actor` — ver §4.

## 1. Archivos a crear

| Archivo | Responsabilidad |
|---|---|
| `src/domain/ports/security_logger.py` | Puerto `ISecurityLogger`. |
| `src/infrastructure/logging/__init__.py` | Paquete nuevo. |
| `src/infrastructure/logging/security_logger.py` | Implementación JSON con rotación y lista blanca. |
| `src/domain/policies/alerta_ip.py` | Política pura de fallos por dirección de red (R3). |
| `tests/unit/infrastructure/test_security_logger.py` | Formato, rotación y R7 (sin password). |
| `tests/unit/domain/test_alerta_ip.py` | Umbral y ventana. |

## 2. Archivos a modificar

- `config.py` — `SECURITY_LOG_FILE`, `SECURITY_LOG_MAX_BYTES`, `SECURITY_LOG_BACKUP_COUNT`,
  con validador de ruta relativa→absoluta reusando el patrón de `resolver_log_path`.
- `.env.example` — documentar los tres (hoy solo trae `LOG_LEVEL`, línea 53).
- `.gitignore` — añadir `logs/`.
- `container.py` — `security_logger()` e inyección en `auditoria_service`.
- `src/services/auditoria_service.py` — emitir al logger además de a la bitácora.
- `main.py` — `/health` real y manejador global de excepciones.

## 3. Métodos de Container a usar

- `Container.auditoria_service()` → `AuditoriaService.registrar_evento(EventoSesion)`
- `Container.security_logger()` → `ISecurityLogger` (nuevo)

## 4. Dónde se engancha — resuelve la tensión de R5

R5 exige que el logger de seguridad sea un módulo separado y que **la interfaz nunca lo
toque directamente**. Pero los eventos de R1 nacen precisamente en la interfaz: login,
route guard, "Ver como". Enganchar el logger en esos puntos violaría R5; no engancharlo
allí dejaría R1 incompleto.

**Salida:** colgar el logger de `AuditoriaService`, que tras `obs_01` ya es el punto único
por donde pasan todos esos eventos. `registrar_evento()` emite a la bitácora **y** al
security logger en la misma llamada. La interfaz sigue llamando solo a
`Container.auditoria_service()`, y cada evento de R1 sale gratis.

Esto convierte `obs_01` en **prerrequisito duro**: hoy `LOGOUT`, `ACCESO_DENEGADO` e
`ip_address` no se emiten, así que R1 quedaría incompleto por construcción sin él.

## 5. Cómo se cumplen R2 y R7 — nunca un password en el log

**Lista blanca de campos.** El formatter serializa únicamente las claves declaradas en un
`frozenset` del módulo (`usuario`, `ip`, `timestamp`, `rol`, `institucion_id`,
`tipo_evento`, `motivo`, `recurso`) y descarta el resto. **No se acepta `**kwargs` libre.**

La diferencia importa: con lista negra o con confianza en quien llama, R2 depende de que
nadie se equivoque nunca; con lista blanca, un campo nuevo con datos sensibles simplemente
no se escribe. R2 pasa a ser verdadero por construcción, y R7 lo comprueba con un password
largo de prueba.

## 6. Alerta por dirección de red (R3, mínimo viable)

`src/domain/policies/alerta_ip.py` se calca de `src/domain/policies/login_throttle.py`:
misma forma, clave IP en vez de nombre de usuario, emite `WARNING` al superar el umbral en
una ventana. Dominio puro, testeable sin I/O.

Vive en memoria del proceso, igual que el throttle — y hereda su limitación, ya registrada
en el roadmap: con varios workers o tras un reinicio el estado se pierde. `S05
(seguridad_web_05_throttle_postgres)` lo persistirá; no se adelanta aquí.

Las otras dos señales de R3 quedan **fuera de alcance declarado**: la IP geográficamente
inusual exige GeoIP, que es dependencia externa; las operaciones fuera de horario habitual
requieren definir ese horario por institución, que hoy no existe como dato.

## 7. Alternativa descartada

**Inyectar el security logger directamente en `route_guard` y `login`.** Más directo y
evitaría depender de `obs_01`. Se descarta porque viola R5 —la interfaz accedería al
logger— y porque duplicaría en la capa de interfaz la decisión de qué constituye un evento
de seguridad, que ya vive modelada en `TipoEventoSesion`. Serían dos listas que se
desincronizarían.

## 8. Añadidos de observabilidad en el mismo paso

Dos arreglos baratos sobre código que ya existe y nadie usa:

- **`/health` real**: llamar a `verify_db_integrity()`
  (`src/infrastructure/db/connection.py:172-190`) y devolver 503 si falla. Hoy responde 200
  aunque la base esté corrupta.
- **Manejador global de excepciones** que registre con `logger.exception`, para que los
  fallos no capturados dejen stack trace en lugar de perderse en el log de uvicorn.

## 9. Fuera de alcance declarado

- **R6 (append-only por permisos del SO)** no es código: va como nota operacional en el
  checklist de deploy. No se puede verificar en el entorno Windows de desarrollo.
- Sentry, OpenTelemetry y Prometheus: fase de comercialización.
- Visor de logs en la UI de admin.
- Backups: spec `seguridad_web_10_backup_rollback`, ya existente.
