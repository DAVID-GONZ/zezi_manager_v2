# split_05_cicd — Diseno

## publish-contract.yml (avedra-backend)

```yaml
name: Publish Contract
on:
  push:
    branches: [main]
    paths:
      - 'app/routes/**'
      - 'src/domain/models/**'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e .

      - name: Generate OpenAPI
        run: python scripts/generate_openapi.py

      - name: Export DTOs
        run: python scripts/export_schemas.py --output contract-output/dto/

      - name: Clone shared-contracts
        uses: actions/checkout@v4
        with:
          repository: <usuario>/avedra-shared-contracts
          token: ${{ secrets.CONTRACTS_PAT }}
          path: shared-contracts

      - name: Update contract files
        run: |
          cp contract-output/openapi.yaml shared-contracts/openapi/avedra-openapi.yaml
          cp contract-output/dto/*.json shared-contracts/dto/

      - name: Create PR in shared-contracts
        # Usar peter-evans/create-pull-request o similar
        ...
```

## validate-contract.yml (avedra-frontend)

```yaml
name: Validate Contract
on:
  repository_dispatch:
    types: [contract-updated]
  # O usar workflow_dispatch + schedule como fallback

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install
        run: npm ci

      - name: Clone shared-contracts
        uses: actions/checkout@v4
        with:
          repository: <usuario>/avedra-shared-contracts
          token: ${{ secrets.CONTRACTS_PAT }}
          path: shared-contracts

      - name: Regenerate API client
        run: npm run generate:api

      - name: Typecheck
        run: npm run typecheck

      - name: Create issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Contract validation failed',
              body: 'The shared contract was updated but typecheck fails. Review the generated API client.',
              labels: ['contract', 'breaking']
            })
```

## check_contract_drift.sh (avedra-backend)

```bash
#!/usr/bin/env bash
set -euo pipefail

# Genera OpenAPI fresco y compara con shared-contracts
python scripts/generate_openapi.py --output /tmp/current-openapi.yaml

SHARED="../avedra-shared-contracts/openapi/avedra-openapi.yaml"

if ! diff -q /tmp/current-openapi.yaml "$SHARED" > /dev/null 2>&1; then
    echo "DRIFT DETECTADO: OpenAPI en shared-contracts difiere del backend"
    diff --unified /tmp/current-openapi.yaml "$SHARED" || true
    exit 1
fi

echo "OK: OpenAPI sincronizado"
```

## Autenticacion cross-repo

Los workflows necesitan un Personal Access Token (PAT) o GitHub App token
con permisos para:
- Clonar avedra-shared-contracts
- Crear branches y PRs en avedra-shared-contracts
- Crear issues en avedra-frontend

El token se configura como secret `CONTRACTS_PAT` en ambos repos.

## Riesgo

Medio. La configuracion de secrets y permisos cross-repo es propensa a
errores la primera vez. Probar manualmente antes de confiar en la
automatizacion.
