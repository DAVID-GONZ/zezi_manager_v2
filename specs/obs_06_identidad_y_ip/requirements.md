# Requisitos: Identidad del actor e IP en toda la bitácora (obs_06)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgos
> A3(b), B3, B5, B12, C1, C3.
> **Depende de:** nada. Es el primer paso de la épica y el prerrequisito de
> `obs_07`, `obs_08`, `obs_09` y `obs_13`.
> **Alcance:** los puntos de emisión de eventos (interfaz y servicios), el
> contexto de actor, el esquema de `audit_log` y `auditoria`, el repositorio
> SQLite y el logger de seguridad. No toca la cobertura de huella: los 23
> servicios que ya llaman `auditar_cambio` no se modifican.

## Estado medido de la bitácora (`data/app.db`, 2026-09-19)

| Medida | Valor |
|---|---|
| Eventos en `auditoria` | 508 |
| Eventos con `ip_address` no nula | **0** |
| `ACCESO_DENEGADO` con `usuario = "anon"` y `usuario_id` nulo | 484 |
| Columnas de identidad en `audit_log` | solo `usuario_id` (sin username, sin IP) |

## Los cinco defectos que este paso cierra

### D1 — La IP nunca se captura

`_obtener_ip()` vive anidado dentro de la clausura de `login.py:86`, con dos
`try/except` que devuelven `None` sin dejar rastro. El resultado medido es 0 de
508 filas con IP, incluidos los logins exitosos. Ningún test cubre el camino
porque la función no es importable desde fuera de la página.

### D2 — La alerta por ráfaga de IP está muerta en ejecución

`AuditoriaService.registrar_evento` solo invoca
`alerta_ip.registrar_fallo_ip(evento.ip_address)` bajo
`if evento.ip_address is not None`. Con D1, esa condición nunca se cumple: la
política completa de `obs_03` es código inalcanzable en producción pese a estar
en verde en los tests unitarios, que le pasan la IP a mano.

### D3 — Cuatro formatos distintos de identidad en la misma columna

| Punto de emisión | Valor escrito en `EventoSesion.usuario` |
|---|---|
| `login.py` | `user_db.usuario` — username |
| `main.py` → `pagina_logout` | `usuario_nombre` — nombre para mostrar |
| `session_context.py` → `_auditar_ver_como` | `admin_nombre` — nombre para mostrar |
| `solo_lectura.py`, `contexto_tenant.py` | `str(uid or "anon")` — entero o literal |

La columna «Usuario» de la bitácora no es agrupable ni buscable.

### D4 — `audit_log` no conserva identidad estable

Columnas actuales: `usuario_id, accion, tabla, registro_id, valor_anterior,
valor_nuevo, timestamp, hash_cadena, institucion_id`. La tabla `auditoria`
guarda `usuario` como texto precisamente «para preservar tras borrado»;
`audit_log` no hizo lo mismo y tampoco guarda IP. Un usuario desactivado o
renombrado deja cambios sin identidad reconstruible.

### D5 — El log de seguridad está apagado y pierde el sujeto

`SECURITY_LOG_FILE` vale `None` por defecto (`config.py:137`) → `NullHandler`, y
las tres variables están comentadas en `.env.example` (líneas 56-58): una
instalación por defecto no escribe nada. Además `_CAMPOS_PERMITIDOS` no incluye
`objetivo`, así que `ver_como(admin, objetivo, accion)` y
`gestion_usuario(actor, objetivo, operacion)` reciben el sujeto de la acción y
lo descartan al serializar.

---

R1: EL SISTEMA DEBE exponer la captura de IP como un módulo importable,
    `src/interface/context/request_ip.py`, con una única función pública
    `ip_de_peticion() -> str | None` que resuelva `X-Forwarded-For` (primer
    salto) y, en su defecto, `request.client.host`.

R2: CUANDO `ip_de_peticion()` no logre resolver una IP, el sistema DEBE emitir
    un `logger.warning` identificable en vez de devolver `None` en silencio.

R3: EL SISTEMA DEBE disponer de un test que falle si `ip_de_peticion()` devuelve
    `None` ante una petición simulada con `X-Forwarded-For` y ante una con
    `client.host`.

R4: `src/services/contexto_actor.py` DEBE transportar, además del `usuario_id`,
    el `username` y la `ip` del actor de la petición en curso, accesibles como
    `actor_username()` y `actor_ip()`. El módulo SIGUE sin importar interfaz ni
    infraestructura.

R5: `activar_actor()` DEBE aceptar `username` e `ip` como parámetros opcionales
    con valor por defecto `None`, de modo que las llamadas existentes de una
    sola posición sigan siendo válidas.

R6: EL SISTEMA DEBE concentrar la construcción de `EventoSesion` desde la capa
    de interfaz en un único módulo, `src/interface/context/eventos_sesion.py`,
    que fije siempre `usuario` = username, `usuario_id`, `ip_address` e
    `institucion_id`.

R7: LOS CINCO PUNTOS DE EMISIÓN (`login.py`, `pagina_logout` en `main.py`,
    `session_context._auditar_ver_como`, `route_guard`, y los de servicios
    `solo_lectura.py` / `contexto_tenant.py`) DEBEN escribir el **username**
    en el campo `usuario`. Ningún punto de emisión escribe un entero, un nombre
    para mostrar ni el literal `"anon"` cuando hay sesión activa.

R8: LA TABLA `audit_log` DEBE incorporar las columnas `usuario TEXT` (snapshot
    del username en el momento del cambio) e `ip_address TEXT`.

R9: LA TABLA `auditoria` DEBE incorporar la columna `objetivo TEXT` (el sujeto
    sobre el que recae la acción: el usuario impersonado, el usuario
    gestionado) y la columna `severidad TEXT NOT NULL DEFAULT 'INFO'` con
    `CHECK` sobre los valores del enum `SeveridadEvento` (`INFO`,
    `ADVERTENCIA`, `CRITICA`). `EventoSesion` DEBE reflejar ambos campos.
    Este paso crea `severidad` y la escribe con su valor por defecto;
    `obs_07` la clasifica y la consume.

R10: `RegistroCambio` DEBE incorporar los campos `usuario: str | None` e
     `ip_address: str | None`, y `auditar_cambio()` DEBE resolverlos desde
     `contexto_actor` cuando no se pasen explícitamente, conservando la regla
     de que nunca propaga excepciones.

R11: EL PAYLOAD FIRMADO de `audit_log` (`_payload_cambio`) DEBE incluir
     `usuario` e `ip_address`, de modo que alterarlos rompa la cadena SHA-256.

R12: `_CAMPOS_PERMITIDOS` del logger de seguridad DEBE incluir `objetivo`, y
     `ver_como()` y `gestion_usuario()` DEBEN emitirlo. La whitelist SIGUE
     siendo cerrada: no se acepta `**kwargs` libre.

R13: `SECURITY_LOG_FILE` DEBE tener un valor por defecto efectivo
     (`logs/security.log`) y las tres variables `SECURITY_LOG_*` DEBEN quedar
     descomentadas en `.env.example`.

R14: CUANDO un evento `LOGIN_FALLIDO` llegue con IP resuelta, el sistema DEBE
     invocar `alerta_ip.registrar_fallo_ip`, y DEBE existir un test de ráfaga
     que verifique la emisión del `WARNING` tras `MAX_FALLOS_IP` fallos.

R15: NINGÚN CAMBIO de este paso debe modificar los 23 servicios que llaman
     `auditar_cambio`, ni hacer crecer `SERVICIOS_SIN_HUELLA_DEUDA`.

## Criterio de done

- Una sesión de login deja una fila en `auditoria` con `usuario` = username e
  `ip_address` no nula.
- Un cambio de datos deja una fila en `audit_log` con `usuario`, `usuario_id` e
  `ip_address` poblados.
- Cinco intentos de login fallido desde la misma IP producen la advertencia
  `ALERTA_IP` en `logs/security.log`.
- Una impersonación produce una línea JSON con `objetivo` en el log de seguridad.
- `python scripts/init.py` completamente verde, incluida la puerta
  `check_auditoria.py` sin nuevas entradas de deuda.
