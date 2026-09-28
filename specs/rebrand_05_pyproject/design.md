# rebrand_05_pyproject — Diseno

## Cambios en `pyproject.toml`

| Linea | Antes | Despues |
|---|---|---|
| 2 | `name = "zeci-manager-v2"` | `name = "avedra"` |
| 4 | `description = "Add your description here"` | `description = "AVEDRA — Administracion y Visualizacion Educativa para la Direccion y el Registro Academico"` |

El nombre pasa de `zeci-manager-v2` a `avedra` (sin sufijo de version,
porque el campo `version` ya la lleva).

## Riesgo

Nulo. No hay publicacion en PyPI ni dependencias externas que referencien
este nombre. El cambio afecta unicamente el nombre que `pip install -e .`
registra en el entorno virtual.
