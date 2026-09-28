# split_02_shared_contracts — Diseno

## OpenAPI: dos caminos

### Opcion A — API ya implementada (FastAPI operativa)

```python
# scripts/generate_openapi.py (en avedra-backend)
import json
from app.main import app

schema = app.openapi()
with open("../avedra-shared-contracts/openapi/avedra-openapi.yaml", "w") as f:
    import yaml
    yaml.dump(schema, f, allow_unicode=True, sort_keys=False)
```

### Opcion B — API aun no implementada (caso actual probable)

Crear un stub YAML manual con los endpoints del roadmap backend marcados
como planificados:

```yaml
openapi: "3.1.0"
info:
  title: AVEDRA API
  version: "0.1.0"
  description: API REST de AVEDRA
paths:
  /api/v1/auth/login:
    post:
      x-status: planned
      summary: Autenticacion de usuario
      ...
  /api/v1/estudiantes:
    get:
      x-status: planned
      summary: Listar estudiantes
      ...
```

Endpoints a incluir en el stub (derivados de servicios existentes):
- Auth (login, refresh, logout)
- Estudiantes (CRUD)
- Usuarios (CRUD)
- Asistencia (registro, consulta)
- Convivencia (observaciones, seguimiento)
- Configuracion (periodos, institucion)
- Informes (consolidados)

## export_schemas.py

```python
# scripts/export_schemas.py (en avedra-backend)
"""Exporta modelos Pydantic como JSON Schema."""

import json
import sys
from pathlib import Path

def export_schemas(output_dir: Path):
    """Recorre src/domain/models/ y exporta cada modelo."""
    from src.domain.models import base
    # Descubrir todas las subclases de AvedraModel
    for model_cls in base.AvedraModel.__subclasses__():
        schema = model_cls.model_json_schema()
        name = model_cls.__name__
        out_file = output_dir / f"{name}.json"
        out_file.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
        print(f"  {name} -> {out_file}")

if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../avedra-shared-contracts/dto")
    output.mkdir(parents=True, exist_ok=True)
    export_schemas(output)
```

**Nota:** Los DTOs heredan indirectamente de `AvedraModel` via `DTODominio`.
El script debe descubrir recursivamente, no solo subclases directas.

## Estructura resultante

```
avedra-shared-contracts/
├── openapi/
│   └── avedra-openapi.yaml      # stub o generado
├── dto/
│   ├── Estudiante.json
│   ├── Usuario.json
│   ├── Observacion.json
│   └── ...                       # uno por modelo
├── design-system/                # llenado en paso manual 3.4
└── .gitignore
```

## Riesgo

Bajo. El stub OpenAPI es declarativo y no afecta codigo. El export_schemas.py
puede fallar si hay modelos con dependencias circulares; en ese caso, excluir
los modelos problematicos y documentar.
