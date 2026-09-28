# split_03_agents_backend — Requisitos

## Contexto

Fase 5.1 + 5.5 + 5.6 del repo split. Crear los agentes Claude, CLAUDE.md y
herramientas para `avedra-backend` y el CLAUDE.md de `avedra-shared-contracts`.

**Repos destino:** `avedra-backend` y `avedra-shared-contracts`.

## Requisitos (EARS)

**R1** — Existe `.claude/agents/` en avedra-backend con: `leader.md`,
`implementer.md`, `reviewer.md`, `spec_author.md`.

**R2** — `leader.md` del backend incluye la regla de contrato API:
cuando un paso modifica endpoint/schema/enum, regenerar OpenAPI y anotar
`CONTRACT_CHANGED` en progress/current.md.

**R3** — `implementer.md` del backend tiene scope `src/` + `app/` (sin
`interface/`) y las reglas duras adaptadas (model_dump, no src.db fuera
de infrastructure, no repos fuera de container).

**R4** — `reviewer.md` del backend valida: API contracts, imports, tests,
reglas anti AI-slop. NO valida CSS/tokens/design system.

**R5** — Existe `CLAUDE.md` en la raiz de avedra-backend, adaptado al
contexto de un repo solo-backend (sin reglas de design system).

**R6** — `scripts/generar_estructura.py` adaptado: sin NOISE_DIRS de
roadmaps/specs/progress, con `app/` en el scope. Conserva consola UTF-8.

**R7** — Existe `CLAUDE.md` en la raiz de avedra-shared-contracts que
explica que es un repo de solo lectura y el flujo de actualizacion.

**R8** — Existe `settings.json` en `.claude/` del backend con la
configuracion base.

## Fuera de alcance

- Agentes del frontend (va en split_04_agents_frontend).
- CI/CD (va en split_05_cicd).
