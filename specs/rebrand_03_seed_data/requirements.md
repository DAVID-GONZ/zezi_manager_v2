# rebrand_03_seed_data — Requisitos

## Contexto

Paso 3 del rebrand ZECI -> AVEDRA. Limpia los datos de ejemplo en
`seed.py`: emails de dominio `@zeci.edu.co`, nombre de institucion
"Institucion Educativa ZECI" en la configuracion de anio. Solo afecta
bases nuevas; las bases existentes conservan sus datos.

## Requisitos (EARS)

**R1** — Cuando el sistema crea una base nueva con seed, los emails de
los usuarios de ejemplo usan el dominio `@avedra.edu.co`.

**R2** — Cuando el sistema crea una base nueva con seed, la configuracion
de anio muestra "Institucion Educativa Demo" (no "ZECI"), porque el nombre
de la institucion real lo configura el colegio, no el seed.

**R3** — `grep -ri "zeci" src/` retorna 0 resultados.

## Fuera de alcance

- Bases de datos existentes (no se recrean).
- El docstring de `seed.py` (ya cubierto en Paso 2).
