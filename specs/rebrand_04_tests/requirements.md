# rebrand_04_tests — Requisitos

## Contexto

Paso 4 del rebrand ZECI -> AVEDRA. Actualiza los archivos de test para
reflejar los renombrados de Pasos 1-3: `ZeciModel` -> `AvedraModel`,
`ZeciError` -> `AvedraError`, logger `avedra.security`, emails
`@avedra.edu.co`, nombre de institucion "Demo", y variables de entorno
E2E. DEBE ejecutarse inmediatamente despues de Paso 2 para restaurar
la suite verde.

## Requisitos (EARS)

**R1** — Mientras la suite de tests se ejecuta, todos los imports de
`ZeciModel` se reemplazan por `AvedraModel`.

**R2** — Mientras la suite de tests se ejecuta, todos los imports y
referencias a `ZeciError` se reemplazan por `AvedraError`.

**R3** — Mientras la suite de tests se ejecuta, los handlers de logger
usan `avedra.security` en vez de `zeci.security`.

**R4** — Mientras la suite de tests se ejecuta, los datos de fixture
usan emails `@avedra.edu.co` y nombre de institucion coherente con
el seed actualizado.

**R5** — Las variables de entorno del entrypoint E2E usan prefijo
`AVEDRA_` en vez de `ZECI_`.

**R6** — `grep -ri "zeci" tests/` retorna 0 resultados. Suite verde.

## Fuera de alcance

- Cambios en `src/` (ya hechos en Pasos 1-3).
- Cambios en `conftest.py` que no sean docstrings o fixtures de datos.
