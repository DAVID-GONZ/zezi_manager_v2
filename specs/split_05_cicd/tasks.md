# split_05_cicd — Tareas

Scope: `.github/workflows/` en avedra-backend y avedra-frontend,
`scripts/check_contract_drift.sh` en avedra-backend.

---

## T1 — publish-contract.yml

**Artefacto:** `avedra-backend/.github/workflows/publish-contract.yml`

Workflow que:
1. Se dispara en push a main cuando cambian `app/routes/` o `src/domain/models/`.
2. Genera OpenAPI y exporta DTOs.
3. Clona avedra-shared-contracts.
4. Actualiza los archivos del contrato.
5. Abre un PR en shared-contracts.

**Prerequisito:** `scripts/generate_openapi.py` y `scripts/export_schemas.py`
deben existir (creados en split_02_shared_contracts).

**Verificacion:**
Ejecutar localmente los pasos de generacion:
```bash
python scripts/generate_openapi.py
python scripts/export_schemas.py --output /tmp/dto-test/
```

---

## T2 — validate-contract.yml

**Artefacto:** `avedra-frontend/.github/workflows/validate-contract.yml`

Workflow que:
1. Se dispara via repository_dispatch (o schedule como fallback).
2. Clona shared-contracts.
3. Regenera cliente API (`npm run generate:api`).
4. Corre typecheck.
5. Si falla, crea issue con label `contract`.

**Verificacion:**
Probar manualmente:
```bash
npm run generate:api
npm run typecheck
```

---

## T3 — check_contract_drift.sh

**Artefacto:** `avedra-backend/scripts/check_contract_drift.sh`

Script bash que:
1. Genera OpenAPI fresco en /tmp.
2. Compara con la version en shared-contracts.
3. Si difieren, imprime diff y sale con exit 1.
4. Si son iguales, imprime OK.

**Verificacion:**
```bash
bash scripts/check_contract_drift.sh
echo $?  # debe ser 0 si esta sincronizado
```

---

## T4 — Documentar configuracion de secrets

Crear una seccion en `CLAUDE.md` o un archivo `docs/CI_SETUP.md` en
avedra-backend que documente:
- Que secret `CONTRACTS_PAT` es necesario en ambos repos.
- Que permisos necesita el token.
- Como configurarlo en GitHub Settings > Secrets.

---

## Cierre del paso

Verificar:
1. Los 2 workflows son YAML valido.
2. El script de drift se puede ejecutar localmente.
3. La documentacion de secrets existe.

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/publish-contract.yml'))"
python -c "import yaml; yaml.safe_load(open('.github/workflows/validate-contract.yml'))"
bash scripts/check_contract_drift.sh
```

Escribir resumen en `progress/impl_split_05_cicd.md` y
devolver al leader solo esa referencia.
