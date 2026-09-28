# split_02_shared_contracts — Requisitos

## Contexto

Fase 3.2-3.3 del repo split. El repo `avedra-shared-contracts` ya esta
inicializado (paso manual 3.1) con directorios `openapi/`, `dto/`,
`design-system/`. Este paso crea el contenido generado: OpenAPI stub y
script de exportacion de DTOs como JSON Schema.

**Repo destino:** `avedra-shared-contracts` (con scripts ejecutados desde
`avedra-backend`).

## Requisitos (EARS)

**R1** — Existe `openapi/avedra-openapi.yaml` con la especificacion OpenAPI 3.1.
Si la API aun no esta implementada: stub con endpoints planificados marcados
`x-status: planned`. Si la API ya existe: generado desde FastAPI.

**R2** — Existe `scripts/export_schemas.py` en `avedra-backend` que recorre
`src/domain/models/` y exporta cada modelo Pydantic como JSON Schema a un
directorio de salida.

**R3** — `dto/` contiene los JSON Schemas exportados, uno por modelo.

**R4** — Cada JSON Schema tiene `$id`, `title` y `description` derivados
del modelo Pydantic original.

## Fuera de alcance

- Design tokens (paso manual 3.4: se copian, no se generan).
- Versionado semantico del contrato (se decide despues).
- CI que automatice la regeneracion (va en split_05_cicd).
