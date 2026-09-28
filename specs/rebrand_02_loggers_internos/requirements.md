# rebrand_02_loggers_internos — Requisitos

## Contexto

Paso 2 del rebrand ZECI -> AVEDRA. Limpia todas las referencias internas
en `src/` que no son visibles al usuario final ni son seed data: nombres
de logger, nombres de ContextVar, nombres de clase base (ZeciModel,
ZeciError) y docstrings de modulo. Al cerrar, `grep -r "zeci" src/` solo
retorna `seed.py` (que se limpia en Paso 3).

## Requisitos (EARS)

**R1** — Cuando el sistema escribe al log de seguridad, el nombre del
logger es `avedra.security`, no `zeci.security`.

**R2** — Cuando el sistema accede a las ContextVar de solo lectura, tenant
y actor, sus nombres internos son `avedra_solo_lectura`,
`avedra_institucion_actual` y `avedra_actor_actual`.

**R3** — La clase base de excepciones de dominio se llama `AvedraError`
y todas sus subclases la heredan.

**R4** — La clase base de modelos de dominio se llama `AvedraModel` y los
tipos `EntidadDominio` y `DTODominio` la heredan.

**R5** — Todos los docstrings de modulo en `src/` que dicen "ZECI Manager"
dicen "AVEDRA".

**R6** — Los exports publicos (`__all__`) reflejan los nombres nuevos.

**R7** — `grep -ri "zeci" src/` solo retorna lineas en `seed.py`.

## Fuera de alcance

- Strings visibles al usuario (Paso 1, ya resuelto).
- Seed data (Paso 3).
- Tests (Paso 4 — se ajustan DESPUES de este paso).
- `container.py` (docstring se toca en Paso 1 via config.py).
