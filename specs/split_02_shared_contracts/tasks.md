# split_02_shared_contracts — Tareas

Scope: `openapi/avedra-openapi.yaml` (en avedra-shared-contracts),
`scripts/export_schemas.py` (en avedra-backend), `dto/` (en avedra-shared-contracts).

---

## T1 — Crear OpenAPI stub

**Artefacto:** `avedra-shared-contracts/openapi/avedra-openapi.yaml`

Crear un archivo OpenAPI 3.1 con los endpoints planificados. Cada endpoint
marcado con `x-status: planned` hasta que la API los implemente.

Endpoints minimos (derivados de los servicios existentes):
- `POST /api/v1/auth/login`
- `GET /api/v1/estudiantes`
- `GET /api/v1/usuarios`
- `GET /api/v1/asistencia`
- `GET /api/v1/observaciones`
- `GET /api/v1/configuracion`

**Verificacion:**
```bash
# Validar sintaxis YAML
python -c "import yaml; yaml.safe_load(open('openapi/avedra-openapi.yaml'))"
```

---

## T2 — Crear export_schemas.py

**Artefacto:** `avedra-backend/scripts/export_schemas.py`

Script que recorre `src/domain/models/` y exporta cada modelo Pydantic
(subclases de AvedraModel, incluyendo indirectas via EntidadDominio y
DTODominio) como JSON Schema.

Argumentos:
- `--output DIR` (default: `../avedra-shared-contracts/dto`)

**Verificacion:**
```bash
python scripts/export_schemas.py --output ../avedra-shared-contracts/dto/
ls ../avedra-shared-contracts/dto/*.json | wc -l  # debe ser > 0
```

---

## T3 — Generar DTOs iniciales

Ejecutar export_schemas.py y verificar que los JSON Schemas son validos.

```bash
python scripts/export_schemas.py --output ../avedra-shared-contracts/dto/
python -c "
import json, pathlib
for f in pathlib.Path('../avedra-shared-contracts/dto').glob('*.json'):
    data = json.loads(f.read_text())
    assert 'title' in data, f'{f.name}: falta title'
    print(f'  OK: {f.name}')
"
```

---

## Cierre del paso

Verificar:
1. `openapi/avedra-openapi.yaml` es YAML valido con estructura OpenAPI 3.1
2. `dto/` contiene al menos 10 JSON Schemas (hay ~30 modelos en el dominio)
3. `scripts/export_schemas.py` se puede ejecutar sin errores

Escribir resumen en `progress/impl_split_02_shared_contracts.md` y
devolver al leader solo esa referencia.
