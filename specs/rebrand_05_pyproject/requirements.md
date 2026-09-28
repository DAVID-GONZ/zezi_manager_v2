# rebrand_05_pyproject — Requisitos

## Contexto

Paso 5 del rebrand ZECI -> AVEDRA. Actualiza la metadata del paquete
en `pyproject.toml`: nombre, descripcion y cualquier referencia residual.
Es el ultimo paso antes del split de repos (Paso 6).

## Requisitos (EARS)

**R1** — El campo `[project].name` es `"avedra"`.

**R2** — El campo `[project].description` describe el producto como AVEDRA.

**R3** — `grep -ri "zeci" pyproject.toml` retorna 0 resultados.

## Fuera de alcance

- Cambio de nombre del directorio del repo (se hace en Paso 6, split).
- Versionado semantico (no cambia por un rebrand).
