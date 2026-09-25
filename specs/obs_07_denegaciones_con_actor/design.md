# Diseño: Denegaciones con actor y clasificación por severidad (obs_07)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `progress/diagnostico_obs_07.md` | crear | Evidencia de la causa raíz. Se escribe **antes** de tocar código. |
| `src/domain/policies/severidad_evento.py` | crear | Función pura `severidad_de(tipo_evento, motivo)`. Fuente única de la clasificación. |
| `src/interface/context/eventos_sesion.py` | modificar | Deriva la severidad al construir, en vez de recibirla suelta. |
| `src/interface/context/event_context.py` | modificar | Cierre del hueco de `ContextVar` que el diagnóstico identifique. |
| `src/interface/context/session_context.py` | modificar | Igual; más `logger.warning` en `_auditar_ver_como`. |
| `src/services/solo_lectura.py` | modificar | Severidad `ADVERTENCIA`; `logger.warning` en el fallo de auditoría. |
| `src/services/contexto_tenant.py` | modificar | Severidad `CRITICA`; `logger.warning` en el fallo. |
| `main.py` | modificar | `logger.warning` en el fallo de auditoría del logout. |
| `src/services/auditoria_service.py` | modificar | `resumen_uso` cuenta solo denegaciones `CRITICA`. |
| `src/interface/presenters/admin/auditoria_presenter.py` | modificar | Filtro `severidad` en el estado y en el DTO. |
| `src/interface/pages/admin/auditoria.py` | modificar | Selector de severidad y badge por fila. |
| `src/domain/models/auditoria.py` | modificar | `FiltroAuditoriaDTO.severidad`. |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | modificar | `WHERE severidad = ?`. |

## 2. El diagnóstico es una tarea, no un preámbulo

`CLAUDE.md` es explícito: «antes de culpar a un cambio, compara contra `HEAD` en
un worktree limpio; afirmar *ya estaba roto* sin comprobarlo ha desviado
diagnósticos». Este paso empieza por medir, y el entregable de esa medición es
un archivo. Tres preguntas, cada una con su método:

**P1 — ¿Por qué `actor_actual()` es `None` al denegar?**
Instrumentar temporalmente `solo_lectura.verificar_escritura` y el guard
cross-tenant de `contexto_tenant` para volcar, junto al evento, el
`id(contextvars.copy_context())` y el stack (`traceback.extract_stack()`).
Reproducir una denegación desde la UI. La hipótesis a confirmar o descartar es
que la denegación ocurre en una task que `tenant_01` no cubre: el interceptor
de `event_context.py` envuelve `Client.handle_event`, pero una escritura
disparada desde un `ui.timer`, un `run.io_bound` o un callback de diálogo puede
no pasar por ahí.

**P2 — ¿Por qué `LOGOUT` y `VER_COMO_*` no dejan filas?**
Los tres emisores están rodeados de `except Exception: pass`. Sustituir
temporalmente el `pass` por un `logger.exception` y ejecutar el camino. Dos
sospechas ordenadas por coste de comprobación: (a) la excepción existe y se
traga —por ejemplo el `CHECK` de `tipo_evento` o un campo que el modelo rechaza—
o (b) el camino no se ejecuta, porque `app.storage.user` ya está vacío cuando
`pagina_logout` construye el evento.

**P3 — ¿Qué son las 379 denegaciones contra la institución 2?**
Correlacionar por `fecha_hora` con las filas de `audit_log` y con los logins
del mismo intervalo para acotar qué sesión y qué pantalla las produce. La
salida es una respuesta, no una lista de posibilidades: o el nombre del flujo
que pide un objeto de otro tenant, o la constatación de un acceso cruzado real.
Si es lo segundo, R9 manda: se reporta y se abre paso propio.

## 3. `severidad_evento.py` — clasificación pura

La severidad no se decide en cada punto de emisión (volvería a divergir, como
divergió la identidad en `obs_06`): se deriva de una función pura que vive en
`domain/policies/`, junto a `rbac_usuarios` y `login_throttle`.

```python
"""severidad_evento.py — clasificación de eventos de sesión (dominio puro)."""
from __future__ import annotations

from src.domain.models.auditoria import SeveridadEvento, TipoEventoSesion

# Motivos de denegación esperados por diseño.
MOTIVO_SOLO_LECTURA = "solo_lectura"
MOTIVO_ROL = "rol_insuficiente"
MOTIVO_CROSS_TENANT = "cross_tenant"

_DENEGACION_ESPERADA = frozenset({MOTIVO_SOLO_LECTURA, MOTIVO_ROL})


def severidad_de(
    tipo_evento: TipoEventoSesion,
    motivo: str | None = None,
) -> SeveridadEvento:
    """
    Severidad de un evento.

    ACCESO_DENEGADO se parte en dos: una escritura bloqueada durante un
    «Ver como» o una ruta sin rol son el sistema funcionando (ADVERTENCIA);
    un acceso a un objeto de otra institución no lo es (CRITICA).
    """
    if tipo_evento is TipoEventoSesion.ACCESO_DENEGADO:
        return (
            SeveridadEvento.ADVERTENCIA
            if motivo in _DENEGACION_ESPERADA
            else SeveridadEvento.CRITICA
        )
    if tipo_evento is TipoEventoSesion.LOGIN_FALLIDO:
        return SeveridadEvento.ADVERTENCIA
    return SeveridadEvento.INFO
```

`motivo` es un código estable, no la cadena de `detalles`. Los emisores pasan
la constante; el texto legible sigue yendo en `detalles`.

## 4. Los emisores pasan el motivo, no la severidad

```python
# solo_lectura.verificar_escritura()
EventoSesion(
    usuario=actor_username() or "desconocido",
    usuario_id=uid,
    ip_address=actor_ip(),
    tipo_evento=TipoEventoSesion.ACCESO_DENEGADO,
    severidad=severidad_de(TipoEventoSesion.ACCESO_DENEGADO, MOTIVO_SOLO_LECTURA),
    detalles="Intento de escritura en modo solo lectura (Ver como)",
)
```

y el `except` deja de ser mudo (R5):

```python
except Exception as exc:
    logger.warning("No se pudo auditar la denegación de escritura: %s", exc)
```

Este es el cambio que habría hecho visible D2 hace nueve días.

## 5. `resumen_uso` cuenta solo lo crítico (R7)

```python
elif tipo == TipoEventoSesion.ACCESO_DENEGADO:
    if getattr(ev, "severidad", None) is SeveridadEvento.CRITICA:
        accesos_denegados += 1
```

Con los datos actuales el KPI pasaría de 484 a 379 — y a 0 en cuanto P3 se
resuelva, que es exactamente lo que un KPI debe hacer: quedarse quieto cuando no
pasa nada y moverse cuando pasa algo. `obs_08` lo reescribe como agregación SQL;
aquí solo se corrige el criterio de conteo.

## 6. UI: filtro y badge

El presenter gana `"severidad": None` en `estado`, un `set_severidad(valor)` y
el campo correspondiente en `construir_filtro()`, exactamente igual que
`institucion_id` en `obs_05`. La página añade un `filter_select` en la barra de
filtros de la pestaña Sesiones y una columna de badge:

| Severidad | Variante de `status_badge` |
|---|---|
| `INFO` | `neutral` |
| `ADVERTENCIA` | `warning` |
| `CRITICA` | `error` |

Son variantes ya existentes en `CLASS_CONTRACT.md` (Badge genérico); no se
añade CSS ni clases nuevas.

## 7. Alternativa descartada

**Silenciar las denegaciones esperadas: no escribirlas.**
Resolvería el ruido de un plumazo y es tentador con 105 filas de «Ver como».
Se descarta porque una denegación es evidencia: saber que un admin intentó
escribir mientras impersonaba es precisamente lo que un auditor quiere poder
comprobar, y una bitácora que decide qué no registrar deja de ser una bitácora.
La respuesta correcta al ruido es clasificarlo y filtrarlo en la lectura, no
dejar de escribirlo.

## 8. Orden de implementación recomendado

1. `progress/diagnostico_obs_07.md` — completo, con las tres respuestas.
2. `severidad_evento.py` + su test puro.
3. Cierre del hueco de `ContextVar` que P1 haya identificado.
4. Emisores: motivo, severidad y `logger.warning`.
5. `resumen_uso`, presenter y página.
6. Test de regresión de R8.
