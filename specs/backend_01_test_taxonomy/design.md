# Diseño: backend_01_test_taxonomy

## Punto de partida medido

| Métrica | Valor |
|---|---|
| Archivos de test | 194 |
| Tests que importan `sqlite3` directamente | 21 |
| Tests de integración (carpeta `tests/integration/`) | ~30 archivos |
| Tests unitarios que usan fixtures de BD (`db_conn`, `db_seed`, `seed_result`, `db_dev`) | por medir |
| Tests unitarios con FakeRepository | mayoría de `tests/unit/services/` |

## Criterio de clasificación

Un test es `repo` si cumple **cualquiera** de:

1. Importa `sqlite3` directamente.
2. Usa los fixtures `db_conn`, `db_seed`, `seed_result` o `db_dev` (los cuatro
   provistos por `conftest.py` que crean conexiones SQLite).
3. Instancia directamente un repositorio `Sqlite*Repository`.
4. Vive en `tests/integration/` (todos tocan la BD real en memoria).

Un test es agnóstico si no cumple ninguna.

## D1 — Marcado automático en conftest.py

El mecanismo ya existe: `pytest_collection_modifyitems` en `conftest.py` marca
`integration`, `unit`, `e2e` y `browser` por ubicación de carpeta. Se extiende
para añadir `repo` a los tests que usan fixtures de BD.

Dos estrategias complementarias:

1. **Por carpeta:** todo test en `tests/integration/` recibe `repo` además de
   `integration` (ya estaba recibiendo solo `integration`).

2. **Por fixture:** un fixture marker que detecta si el test solicita `db_conn`,
   `db_seed`, `seed_result` o `db_dev` y le añade `repo` dinámicamente.
   Implementación: en `pytest_collection_modifyitems`, inspeccionar
   `item.fixturenames` para cada item.

La opción 2 es la más precisa: si un test en `tests/unit/` pide `db_conn`,
recibirá `repo` sin necesidad de moverlo de carpeta. No todos los tests de
`tests/unit/` son agnósticos — algunos en `unit/infrastructure/` o
`unit/domain/` usan la BD.

## D2 — Registro del marker

En `pyproject.toml`, sección `[tool.pytest.ini_options]`, añadir:

```toml
[tool.pytest.ini_options]
markers = [
    "repo: test que depende del backend de BD (SQLite/futuro Postgres)",
    # ... markers existentes
]
```

## D3 — Inventario como artefacto

Producir `progress/impl_backend_01.md` con la clasificación completa:
listado de archivos `repo` y listado de archivos agnósticos, para que
`backend_02` sepa exactamente qué tests debe parametrizar.

## Alternativa descartada

**Mover archivos a subdirectorios `tests/repo/` y `tests/agnostic/`.**
Rompería imports relativos, conftest scoping y el historial de git. Los markers
son el mecanismo nativo de pytest para esto.
