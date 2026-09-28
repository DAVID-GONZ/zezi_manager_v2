# split_05_cicd — Requisitos

## Contexto

Fase 6 del repo split. Crear los workflows de GitHub Actions y scripts
que mantienen sincronizados los contratos entre repos.

**Repos destino:** `avedra-backend` y `avedra-frontend`.

## Requisitos (EARS)

**R1** — Existe `.github/workflows/publish-contract.yml` en avedra-backend
que se dispara cuando cambian archivos en `app/routes/` o `src/domain/models/`.
Genera OpenAPI, exporta DTOs y abre un PR automatico en avedra-shared-contracts.

**R2** — Existe `.github/workflows/validate-contract.yml` en avedra-frontend
que se dispara cuando avedra-shared-contracts publica una nueva version.
Regenera el cliente API, corre typecheck y crea un issue si falla.

**R3** — Existe `scripts/check_contract_drift.sh` en avedra-backend que
compara la version de OpenAPI actual en shared-contracts con la que el
backend generaria ahora. Si difieren, retorna exit code 1 con un mensaje
indicando las diferencias.

**R4** — Los workflows usan secrets de GitHub para acceso cross-repo
(CONTRACTS_PAT o GitHub App token).

## Fuera de alcance

- CI general de cada repo (linting, tests) — eso es responsabilidad de
  cada repo individualmente.
- Deploy (Caddy, Docker, hosting) — paso posterior.
