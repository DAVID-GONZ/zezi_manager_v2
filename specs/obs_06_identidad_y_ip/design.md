# Diseño: Identidad del actor e IP en toda la bitácora (obs_06)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/interface/context/request_ip.py` | crear | Única resolución de IP de la petición. Importable y testeable. |
| `src/interface/context/eventos_sesion.py` | crear | Único constructor de `EventoSesion` desde la interfaz. |
| `src/services/contexto_actor.py` | modificar | Transporta `usuario_id`, `username` e `ip` en un solo `ContextVar`. |
| `src/interface/context/session_context.py` | modificar | Activa el actor con los tres datos; `_auditar_ver_como` usa el constructor único. |
| `src/interface/pages/login.py` | modificar | Retira `_obtener_ip()` anidado; usa `request_ip` y el constructor único. |
| `main.py` | modificar | `pagina_logout` usa el constructor único (username, no nombre para mostrar). |
| `src/interface/auth/route_guard.py` | modificar | `ACCESO_DENEGADO` usa el constructor único. |
| `src/services/solo_lectura.py` | modificar | Usa `actor_username()` / `actor_ip()` en vez de `str(uid or "anon")`. |
| `src/services/contexto_tenant.py` | modificar | Igual que el anterior. |
| `src/domain/models/auditoria.py` | modificar | `SeveridadEvento`; `EventoSesion.severidad`; `RegistroCambio.usuario` e `ip_address`; factories. |
| `src/services/auditoria_helpers.py` | modificar | `auditar_cambio` resuelve `usuario` e `ip` desde el contexto. |
| `src/infrastructure/db/schema.py` | modificar | DDL de `audit_log` (+2 columnas) y `auditoria` (+`severidad`). |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | modificar | INSERT/SELECT y payload firmado de ambas tablas. |
| `src/infrastructure/logging/security_logger.py` | modificar | `objetivo` en la whitelist y en los dos emisores. |
| `config.py`, `.env.example` | modificar | `SECURITY_LOG_FILE` con default efectivo. |

## 2. `request_ip.py` — la captura deja de ser silenciosa

El defecto actual no es el algoritmo, es que su fallo no se puede observar: dos
`except` anidados devuelven `None` y la página sigue. El módulo nuevo conserva el
algoritmo y hace ruidoso el fallo (R2).

```python
"""request_ip.py — resolución única de la IP de la petición en curso."""
from __future__ import annotations

import logging

logger = logging.getLogger("INTERFACE.REQUEST_IP")


def _de_request(request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    cliente = getattr(request, "client", None)
    return getattr(cliente, "host", None)


def ip_de_peticion() -> str | None:
    """IP del cliente, o None si no hay petición resoluble (y lo advierte)."""
    request = None
    try:
        from nicegui import app as _app
        request = _app.storage.request
    except Exception:
        try:
            from nicegui import Client
            request = Client.current().request
        except Exception:
            request = None

    if request is None:
        logger.warning("IP no resuelta: no hay petición accesible en el contexto")
        return None
    try:
        ip = _de_request(request)
    except Exception as exc:
        logger.warning("IP no resuelta: %s", exc)
        return None
    if ip is None:
        logger.warning("IP no resuelta: la petición no expone X-Forwarded-For ni client.host")
    return ip
```

`_de_request` se separa a propósito: es la parte pura y es lo que el test de R3
ejercita con un doble de petición, sin servidor NiceGUI.

## 3. `contexto_actor.py` — un solo ContextVar con los tres datos

El problema de `solo_lectura.py` y `contexto_tenant.py` es de capas: están en
servicios, no pueden importar interfaz y solo tienen el `usuario_id`, así que
escriben `str(uid or "anon")`. La solución es que el contexto neutral transporte
ya resuelto lo que necesitan. El módulo sigue siendo stdlib puro.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ActorContexto:
    usuario_id: int | None = None
    username: str | None = None
    ip: str | None = None


_actor_actual: contextvars.ContextVar[ActorContexto] = contextvars.ContextVar(
    "zeci_actor_actual", default=ActorContexto()
)


def activar_actor(
    usuario_id: int | None,
    username: str | None = None,   # NUEVO — opcional: las llamadas de 1 argumento siguen válidas
    ip: str | None = None,         # NUEVO
) -> None:
    _actor_actual.set(ActorContexto(usuario_id, username, ip))


def actor_actual() -> int | None:      # firma intacta
    return _actor_actual.get().usuario_id


def actor_username() -> str | None:    # NUEVO
    return _actor_actual.get().username


def actor_ip() -> str | None:          # NUEVO
    return _actor_actual.get().ip
```

`usar_actor(id)` mantiene su firma y acepta los dos nuevos opcionales. El
choke point de activación sigue siendo `SessionContext.desde_storage()`, que
ahora pasa también `username` e `ip_de_peticion()`, conservando la **regla de
impersonación**: con `impersonando=True` el actor es el admin real.

## 4. `eventos_sesion.py` — un solo constructor

```python
"""eventos_sesion.py — constructor único de EventoSesion desde la interfaz."""
from __future__ import annotations

from src.domain.models.auditoria import EventoSesion, SeveridadEvento, TipoEventoSesion
from src.interface.context.request_ip import ip_de_peticion


def construir_evento(
    *,
    usuario: str,
    usuario_id: int | None,
    tipo_evento: TipoEventoSesion,
    detalles: str | None = None,
    objetivo: str | None = None,
    severidad: SeveridadEvento = SeveridadEvento.INFO,
    institucion_id: int | None = None,
) -> EventoSesion:
    """`usuario` es SIEMPRE el username, nunca el nombre para mostrar ni un id."""
    return EventoSesion(
        usuario=usuario,
        usuario_id=usuario_id,
        tipo_evento=tipo_evento,
        ip_address=ip_de_peticion(),
        detalles=detalles,
        objetivo=objetivo,
        severidad=severidad,
        institucion_id=institucion_id,
    )
```

Los dos emisores que viven en servicios (`solo_lectura`, `contexto_tenant`) no
pueden usar este módulo — importaría interfaz desde servicios. Construyen
`EventoSesion` directamente, pero ya con datos buenos:

```python
# solo_lectura.verificar_escritura() y contexto_tenant, en vez de str(uid or "anon")
from src.services.contexto_actor import actor_actual, actor_ip, actor_username

uid = actor_actual()
EventoSesion(
    usuario=actor_username() or "desconocido",
    usuario_id=uid,
    ip_address=actor_ip(),
    tipo_evento=TipoEventoSesion.ACCESO_DENEGADO,
    detalles="...",
)
```

El literal `"anon"` desaparece; `"desconocido"` queda solo para el caso sin
sesión (seed, scripts), que `obs_07` investigará.

## 5. Esquema: una sola apertura de la base

Cambiar el esquema obliga a recrear la base (decisión permanente de `CLAUDE.md`:
no hay migraciones). Para no pagar ese coste dos veces, **este paso abre el DDL
una sola vez y añade también la columna que `obs_07` necesitará**, aunque aquí
solo se escriba con su valor por defecto.

```sql
CREATE TABLE IF NOT EXISTS auditoria (
    ...
    ip_address  TEXT,
    fecha_hora  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detalles    TEXT,
    objetivo    TEXT,                                    -- NUEVO: sujeto de la acción
    severidad   TEXT NOT NULL DEFAULT 'INFO'             -- NUEVO: lo clasifica obs_07
                CHECK(severidad IN ('INFO','ADVERTENCIA','CRITICA')),
    hash_cadena TEXT,
    institucion_id INTEGER REFERENCES instituciones(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    ...
    usuario     TEXT,        -- NUEVO: snapshot del username (sobrevive al borrado)
    ip_address  TEXT,        -- NUEVO
    ...
);
```

El `CHECK` de `severidad` se declara aquí y no se difiere a
`backend_04_metadata_schema`: la columna nace con el DDL nuevo, así que no cae
en el supuesto de «`ALTER TABLE ADD CONSTRAINT` que SQLite no soporta» que
justifica la deuda de `scripts/check_enums.py`.

## 6. El payload firmado incorpora la identidad (R11)

```python
@staticmethod
def _payload_cambio(registro: RegistroCambio) -> dict:
    return {
        "usuario": registro.usuario,          # NUEVO
        "usuario_id": registro.usuario_id,
        "ip_address": registro.ip_address,    # NUEVO
        "accion": registro.accion.value,
        "tabla": registro.tabla,
        "registro_id": registro.registro_id,
        "valor_anterior": registro.valor_anterior,
        "valor_nuevo": registro.valor_nuevo,
        "timestamp": registro.timestamp.isoformat(),
    }
```

Decisión y su consecuencia, explícitas: `usuario` e `ip_address` **entran** en el
hash porque son los campos que un manipulador querría reescribir; dejarlos fuera
haría indetectable cambiar de quién fue una acción. El precio es que las filas
firmadas con el payload anterior dejan de verificar — irrelevante aquí porque la
base se recrea de todos modos, y la cadena arranca de nuevo desde `GENESIS`.
`institucion_id` sigue **fuera** del payload, como lo dejó `mejora_07-T7`.

## 7. `auditar_cambio` resuelve identidad, no la recibe

```python
uid = usuario_id if usuario_id is not None else actor_actual()
iid = institucion_id if institucion_id is not None else institucion_actual()
uname = actor_username()      # NUEVO
uip = actor_ip()              # NUEVO
```

Los tres factories de `RegistroCambio` (`para_creacion`, `para_actualizacion`,
`para_eliminacion`) ganan `usuario` e `ip_address` como parámetros opcionales al
final de la firma, para no romper ninguna de las llamadas existentes. La regla
R8 de `obs_01` se mantiene intacta: `auditar_cambio` nunca propaga excepciones.

## 8. Logger de seguridad: añadir el campo, no abrir la whitelist

```python
_CAMPOS_PERMITIDOS = frozenset({
    "usuario", "ip", "timestamp", "rol", "institucion_id",
    "tipo_evento", "motivo", "recurso",
    "objetivo",          # NUEVO
})
```

y los dos emisores que hoy reciben `objetivo` y lo tiran lo incluyen en `extra`.
El diseño de whitelist cerrada de `obs_03` es correcto y se conserva: lo que
falla no es el mecanismo, es que faltaba una entrada.

`config.py`: `SECURITY_LOG_FILE: Path | None = Path("logs/security.log")`. El
validador de `LOG_FILE`/`SECURITY_LOG_FILE` ya existe y crea el directorio padre.

## 9. Test estructural: la identidad no puede volver a divergir

Un verde puntual no impide que el sexto punto de emisión repita el patrón. Se
añade `tests/unit/interface/test_emision_eventos.py` con un chequeo por AST
(no regex — la lección de `check_design.py` ciego a multilínea aplica igual):
recorre `src/interface/` buscando llamadas `EventoSesion(...)` y falla si alguna
ocurre fuera de `src/interface/context/eventos_sesion.py`.

## 10. Alternativa descartada

**Pasar `username` e `ip` como parámetros a cada método de servicio que audita.**
Es explícito y no toca `contexto_actor`, pero obliga a cambiar la firma de los
~137 métodos mutadores que `obs_04` acaba de cubrir, y a que cada llamador
recuerde propagarlos — exactamente el modo de fallo que `obs_01` eliminó al
crear el choke point. El `ContextVar` ya es el mecanismo elegido y probado para
el `usuario_id`; añadirle dos campos cuesta un `dataclass` y cero firmas.

## 11. Orden de implementación recomendado

1. `contexto_actor.py` + su test (base de todo lo demás).
2. `request_ip.py` + su test (R3).
3. `auditoria.py` (dominio): `SeveridadEvento`, campos nuevos, factories.
4. `schema.py` + `sqlite_auditoria_repo.py` (DDL, INSERT, SELECT, payload).
5. `eventos_sesion.py` + migración de los cinco puntos de emisión.
6. `auditoria_helpers.py`.
7. `security_logger.py` + `config.py` + `.env.example`.
8. Test estructural y recreación de la base.
