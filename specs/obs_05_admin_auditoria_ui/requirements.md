# Requisitos: Auditoría en admin — filtro institución, paginación y KPIs (obs_05)

> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §3.
> **Depende de:** `obs_04a` como mínimo (necesita volumen real de huella para
> que la paginación sea verificable con datos).
> **Alcance:** solo la capa de interfaz y el presenter. No modifica el dominio,
> no modifica el repositorio (el filtro `institucion_id` y el LIMIT/OFFSET ya
> existen en `sqlite_auditoria_repo.py`).

## Los tres huecos actuales (2026-09-09)

### Hueco A — filtro por institución ausente

`FiltroAuditoriaDTO.institucion_id` existe (línea 409 de `auditoria.py`).
`sqlite_auditoria_repo.listar_cambios()` lo filtra (líneas 306–308) y
`listar_eventos()` también (líneas 163–165).

Sin embargo:
- `AuditoriaPresenter.estado` no tiene la clave `"institucion_id"`.
- `AuditoriaPresenter.construir_filtro()` nunca asigna ese campo: el DTO
  siempre viaja con `institucion_id=None`.
- La página no muestra ningún selector de institución.

Consecuencia: un admin cross-tenant que administra varios tenants no puede
acotar la bitácora a una institución concreta.

### Hueco B — paginación sin controles

`_POR_PAGINA = 100` en `auditoria.py` es un techo silencioso. Si hay más de
100 registros, la tabla los trunca sin aviso y sin manera de avanzar.

`AuditoriaPresenter` ya tiene `set_pagina()` y `reset_pagina()`, y el repo ya
aplica `LIMIT`/`OFFSET` vía `filtro.pagina` y `filtro.por_pagina`. Solo faltan
controles de navegación en la UI y el mecanismo para detectar si hay página
siguiente.

### Hueco C — `resumen_uso()` sin consumidor

`AuditoriaService.resumen_uso(dias=7)` y `ResumenUsoDTO` están implementados
y cubiertos por tests (obs_01). El consumidor original que mostraba los KPIs
de login en el inicio del admin se perdió cuando `inicio.py` migró a
`_ADMIN_CARDS`. El dashboard del admin muestra solo cuatro tarjetas de
navegación, sin datos de actividad.

---

R1: LA PÁGINA `auditoria.py` DEBE mostrar un `filter_select` de institución
    en la zona de filtros comunes, visible únicamente cuando el rol del actor
    es `admin`. El select lista todas las instituciones vía
    `Container.institucion_service().listar()`.

R2: `AuditoriaPresenter` DEBE exponer `set_institucion(valor)` e incluir
    `institucion_id` en `estado` y en `construir_filtro()`.

R3: LA PÁGINA DEBE mostrar controles Anterior / Siguiente debajo de cada
    tabla (cambios y sesiones) basados en la estrategia look-ahead: se
    solicita `_POR_PAGINA + 1` registros; si la respuesta supera
    `_POR_PAGINA`, existe página siguiente y se trunca el excedente antes
    de renderizar.

R4: `AuditoriaPresenter` DEBE exponer el estado derivado necesario para los
    controles de paginación: `pagina_actual()` y `hay_siguiente_cambios` /
    `hay_siguiente_sesiones` (booleanos actualizados en cada carga).

R5: EL VALOR `_POR_PAGINA` DEBE reducirse de 100 a 50 para que la paginación
    sea necesaria y verificable con volumen moderado de datos.

R6: `inicio.py` DEBE mostrar una sección de KPIs de uso para el rol `admin`,
    renderizada con el componente existente `stats_grid` / `StatItem` antes
    de los `_ADMIN_CARDS`. Los KPIs provienen de
    `Container.auditoria_service().resumen_uso(dias=7)`:
    - Logins hoy (`logins_hoy`).
    - Usuarios activos 7 d (`usuarios_activos`).
    - Accesos denegados 7 d (`accesos_denegados`).

R7: LA SECCIÓN DE KPIs en `inicio.py` DEBE ser fail-open: si `resumen_uso()`
    lanza excepción, la sección se omite silenciosamente sin romper la página.

R8: NINGÚN CAMBIO debe tocar `IAuditoriaRepository`, `sqlite_auditoria_repo`,
    `AuditoriaService` ni el dominio de auditoría — los tres huecos son
    íntegramente de UI / presenter.

R9: LA PÁGINA DEBE seguir siendo de solo lectura. No se añaden controles de
    escritura.

## Criterio de done

- Un admin puede elegir una institución en el filtro y la tabla muestra solo
  los cambios de ese tenant.
- Con más de 50 registros, el botón "Siguiente" aparece y carga la página 2.
- El dashboard del admin muestra logins_hoy, usuarios_activos y
  accesos_denegados antes de las cuatro tarjetas de navegación.
- `python scripts/init.py` completamente verde (sin nuevas violaciones de
  design system ni imports rotos).
