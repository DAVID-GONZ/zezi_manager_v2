# Requisitos: Denegaciones con actor y clasificación por severidad (obs_07)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgos
> B4 y A3(a).
> **Depende de:** `obs_06`, que aporta `actor_username()`, `actor_ip()`, la
> columna `severidad` y el constructor único de eventos.
> **Alcance:** el ciclo de vida del `ContextVar` de actor en los caminos de
> denegación, la clasificación de eventos y su presentación. No cambia el
> esquema: `obs_06` ya abrió la base.

## Estado medido (`data/app.db`, 2026-09-19)

De 508 eventos de sesión, **484 (95,3 %)** son `ACCESO_DENEGADO` escritos con
`usuario = "anon"` y `usuario_id` nulo:

| Detalle del evento | Filas |
|---|---|
| `Cross-tenant: objeto institucion 2` | 379 |
| `Intento de escritura en modo solo lectura (Ver como)` | 105 |

Acumulados entre 2026-09-08 y 2026-09-17. En el mismo periodo:

| Tipo de evento | Filas |
|---|---|
| `LOGOUT` | **0** |
| `VER_COMO_INICIO` / `VER_COMO_FIN` | **0** |

## Los tres defectos que este paso cierra

### D1 — El actor es desconocido justo donde más importa

`solo_lectura.verificar_escritura()` y `contexto_tenant` llaman a
`actor_actual()` y reciben `None`. `obs_06` les da la vía para escribir el
username, pero si el `ContextVar` está vacío en ese punto seguirán escribiendo
`"desconocido"`. La causa raíz no está diagnosticada: `tenant_01` instaló el
interceptor que resincroniza los `ContextVar` antes de cada event handler, pero
no consta que cubra el camino por el que llegan estas denegaciones.

### D2 — Eventos implementados que nunca se escriben

`LOGOUT` y `VER_COMO_*` tienen emisor en el código y cero filas en nueve días de
uso. O el camino no se ejecuta, o la excepción se traga en el `except: pass` que
rodea a los tres emisores. Un evento que se emite y no aparece es peor que uno
que no existe: da falsa confianza.

### D3 — Ruido y señal indistinguibles

Una denegación de escritura durante un «Ver como» es el comportamiento
esperado del modo solo lectura: el admin pulsa un botón y el sistema lo bloquea.
Una denegación cross-tenant es, hasta prueba en contrario, un intento de acceder
a datos de otra institución. Hoy ambas son la misma fila, con el mismo aspecto,
y juntas sepultan los 24 eventos que sí importan.

---

R1: EL EQUIPO DEBE documentar en `progress/diagnostico_obs_07.md` la causa raíz
    de que `actor_actual()` sea `None` en `solo_lectura.py` y
    `contexto_tenant.py`, y la de que `LOGOUT` y `VER_COMO_*` no produzcan
    filas, **antes** de modificar código. El diagnóstico se compara contra
    `HEAD` en un worktree limpio antes de atribuir la causa a ningún cambio.

R2: EL EQUIPO DEBE documentar en el mismo archivo el origen de las 379
    denegaciones cross-tenant contra la institución 2, con el flujo de UI que
    las provoca, y concluir de forma explícita si son un fallo de enfoque de un
    flujo legítimo o un intento real de acceso cruzado.

R3: CUANDO exista una sesión activa, el sistema NO DEBE escribir ningún evento
    `ACCESO_DENEGADO` con `usuario_id` nulo. El `ContextVar` de actor DEBE estar
    poblado en todos los caminos que pueden denegar.

R4: EL SISTEMA DEBE clasificar cada evento de sesión con una `SeveridadEvento`
    en el momento de emitirlo:
    - `INFO` — operación normal (login, logout, ver como).
    - `ADVERTENCIA` — denegación esperada por diseño (escritura bloqueada en
      modo solo lectura, acceso a ruta sin rol).
    - `CRITICA` — denegación no esperada (acceso cross-tenant, login fallido
      repetido desde la misma IP).

R5: LOS TRES EMISORES que hoy envuelven la escritura de auditoría en
    `except Exception: pass` DEBEN registrar el fallo con `logger.warning`
    antes de continuar. La auditoría sigue sin bloquear la operación de
    negocio, pero su fallo deja de ser invisible.

R6: LA PÁGINA `/admin/auditoria` DEBE ofrecer un filtro por severidad en la
    pestaña Sesiones y DEBE mostrar la severidad como badge en cada fila,
    usando las variantes del contrato de clases (`neutral`, `warning`, `error`).

R7: EL RESUMEN DE USO DEBE contar como «accesos denegados» solo los eventos de
    severidad `CRITICA`. Las denegaciones esperadas no inflan el KPI del
    dashboard.

R8: EL SISTEMA DEBE conservar un test de regresión que falle si un evento
    `ACCESO_DENEGADO` se escribe con `usuario_id` nulo habiendo actor activo en
    el contexto.

R9: SI el diagnóstico de R2 concluye que existe un fallo de aislamiento real,
    ese fallo NO se arregla en este paso: se reporta a David y se abre un paso
    propio. Este paso hace visible el problema, no lo repara.

## Criterio de done

- `progress/diagnostico_obs_07.md` responde las tres preguntas de R1 y R2 con
  evidencia (consultas, trazas o worktree limpio), no con hipótesis.
- Provocar una denegación cross-tenant desde una sesión activa escribe una fila
  con username, `usuario_id`, IP y `severidad = 'CRITICA'`.
- Provocar una escritura bloqueada durante «Ver como» escribe una fila con
  `severidad = 'ADVERTENCIA'`.
- Cerrar sesión escribe una fila `LOGOUT`; iniciar y terminar «Ver como»
  escriben sus dos filas.
- El filtro de severidad de la pestaña Sesiones acota la tabla.
- `python scripts/init.py` completamente verde.
