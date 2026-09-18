# Diseño: Logging de seguridad estructurado (obs_03_security_logger)

> **Requisitos:** `requirements.md` de esta misma carpeta (R1–R9).
> **Origen:** `specs/seguridad_web_09_logging_alertas/design.md` — diseño S09 original (2026-07-29).
> **Depende de:** `obs_01_huella_actor` — ver §4.

## 1. Archivos a crear

| Archivo | Responsabilidad |
|---|---|
| `src/domain/ports/security_logger.py` | Puerto `ISecurityLogger` — un método por familia de evento de R1. |
| `src/infrastructure/logging/__init__.py` | Paquete nuevo. |
| `src/infrastructure/logging/security_logger.py` | Implementación: logger `zeci.security`, formatter JSON, `RotatingFileHandler`, lista blanca de campos. |
| `src/domain/policies/alerta_ip.py` | Política pura de fallos por dirección de red (R3). Dominio puro, sin I/O. |
| `tests/unit/infrastructure/test_security_logger.py` | Formato, rotación y R7 (sin password). |
| `tests/unit/domain/test_alerta_ip.py` | Umbral y ventana de la política de IP. |

## 2. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `config.py` | Añadir `SECURITY_LOG_FILE`, `SECURITY_LOG_MAX_BYTES`, `SECURITY_LOG_BACKUP_COUNT` con validador de ruta relativa→absoluta reutilizando el patrón de `resolver_log_path`. |
| `.env.example` | Documentar los tres parámetros nuevos (hoy solo trae `LOG_LEVEL`, línea 53). |
| `.gitignore` | Añadir `logs/`. |
| `container.py` | `security_logger()` e inyección en `auditoria_service`. |
| `src/services/auditoria_service.py` | Emitir al logger además de a la bitácora en `registrar_evento`. |
| `main.py` | `/health` real (R8) y manejador global de excepciones (R9). |

## 3. Estructura del puerto (R5)

```python
# src/domain/ports/security_logger.py
from abc import ABC, abstractmethod

class ISecurityLogger(ABC):
    @abstractmethod
    def login_exitoso(self, usuario: str, ip: str, rol: str, institucion_id: int) -> None: ...
    @abstractmethod
    def login_fallido(self, usuario: str, ip: str, motivo: str) -> None: ...
    @abstractmethod
    def logout(self, usuario: str, ip: str) -> None: ...
    @abstractmethod
    def acceso_denegado(self, usuario: str, ip: str, recurso: str) -> None: ...
    @abstractmethod
    def ver_como(self, admin: str, objetivo: str, accion: str) -> None: ...
    @abstractmethod
    def gestion_usuario(self, actor: str, objetivo: str, operacion: str) -> None: ...
```

## 4. Dónde se engancha — resuelve la tensión de R5

R5 exige que la interfaz **nunca** toque el security logger directamente. Pero los eventos
de R1 (login, route guard, "Ver como") nacen en la interfaz.

**Solución:** colgar el logger de `AuditoriaService`, que tras `obs_01` ya es el punto
único por donde pasan todos esos eventos. `registrar_evento(EventoSesion)` emite a la
bitácora **y** al security logger en la misma llamada. La interfaz sigue llamando solo a
`Container.auditoria_service()`.

Esto convierte `obs_01` en **prerrequisito duro**: sin él, `LOGOUT`, `ACCESO_DENEGADO` e
`ip_address` no se emiten y R1 quedaría incompleto por construcción.

## 5. Cómo se cumplen R2 y R7 — nunca un password en el log

**Lista blanca de campos.** El formatter serializa únicamente las claves declaradas en un
`frozenset` del módulo:

```python
_CAMPOS_PERMITIDOS = frozenset({
    "usuario", "ip", "timestamp", "rol",
    "institucion_id", "tipo_evento", "motivo", "recurso",
})
```

No se acepta `**kwargs` libre. Con lista negra o confiando en quien llama, R2 depende de
que nadie se equivoque nunca; con lista blanca, un campo sensible nuevo simplemente no se
escribe. R2 pasa a ser verdadero por construcción. R7 lo comprueba con un password largo.

## 6. Alerta por dirección de red (R3 — mínimo viable)

`src/domain/policies/alerta_ip.py` se calca de `src/domain/policies/login_throttle.py`:
misma forma, clave IP en vez de nombre de usuario, emite `WARNING` al superar el umbral en
una ventana configurable.

Vive en memoria del proceso, igual que el throttle — y hereda su limitación ya registrada
en el roadmap: con varios workers o tras un reinicio, el estado se pierde. `S05
(seguridad_web_05_throttle_postgres)` lo persistirá; no se adelanta aquí.

## 7. Formatter JSON y rotación (R4)

```python
import logging
from logging.handlers import RotatingFileHandler

HANDLER = RotatingFileHandler(
    filename=settings.SECURITY_LOG_FILE,
    maxBytes=settings.SECURITY_LOG_MAX_BYTES,
    backupCount=settings.SECURITY_LOG_BACKUP_COUNT,
    encoding="utf-8",
    delay=True,
)
HANDLER.setFormatter(_JsonSecurityFormatter())
```

`_JsonSecurityFormatter.format()` serializa únicamente `_CAMPOS_PERMITIDOS`; el resto se
descarta silenciosamente. Nunca se asigna `mode="w"` al handler — solo append por defecto.

Si `SECURITY_LOG_FILE` es `None`, se usa un `NullHandler` (entorno de desarrollo sin
fichero configurado).

## 8. `/health` real y manejador global (R8, R9)

```python
# main.py
@app.get("/health")
async def health():
    ok = verify_db_integrity()          # src/infrastructure/db/connection.py:172
    if not ok:
        return JSONResponse(status_code=503, content={"status": "error"})
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Excepción no capturada: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno"})
```

## 9. Alternativa descartada

**Inyectar el security logger directamente en `route_guard` y `login`.** Más directo y
evitaría depender de `obs_01`. Se descarta porque:
- Viola R5 — la interfaz accedería al logger.
- Duplicaría en la capa de interfaz la decisión de qué constituye un evento de seguridad,
  que ya vive modelada en `TipoEventoSesion`. Serían dos listas que se desincronizarían.

## 10. Fuera de alcance declarado

- **R6 (append-only por permisos del SO):** nota operacional en el checklist de deploy; no
  verificable en Windows.
- IP geográficamente inusual: exige GeoIP (dependencia externa).
- Operaciones fuera de horario habitual: exige dato de horario por institución, que hoy no
  existe como campo.
- Sentry, OpenTelemetry, Prometheus: fase de comercialización.
- Visor de logs en la UI de admin.
- Backups: `specs/seguridad_web_10_backup_rollback`.
