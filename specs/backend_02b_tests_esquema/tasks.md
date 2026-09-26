# Tareas: backend_02b_tests_esquema

> SCOPE — únicos archivos que pueden crearse:
> `tests/unit/infrastructure/test_schema_integrity.py` (nuevo).
>
> Fuera de scope: `schema.py`, código de producción, otros tests.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**

---

## T1 — Helpers de introspección DDL  [ ]

En `test_schema_integrity.py`, crear funciones auxiliares que:

1. Extraigan nombres de tabla de la lista `SCHEMA` (regex sobre
   `CREATE TABLE IF NOT EXISTS (\w+)`).
2. Extraigan FKs declaradas del DDL de cada tabla (regex sobre
   `FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s+(\w+)`).
3. Extraigan tablas referenciadas por cada tabla (`REFERENCES (\w+)`).

**Verificación:** importar el módulo sin error.

---

## T2 — Test de tablas existentes (R1)  [ ]

Verificar que toda tabla extraída de `SCHEMA` existe en
`sqlite_master` de la base aplicada.

Usar la fixture `db_schema` (BD vacía con schema, scope session).

```python
def test_todas_las_tablas_existen(db_schema):
    tablas_declaradas = extraer_tablas_de_schema()
    tablas_reales = {row[0] for row in db_schema.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    faltantes = tablas_declaradas - tablas_reales
    assert not faltantes, f"Tablas declaradas que no existen: {faltantes}"
```

---

## T3 — Test de columnas por tabla (R2)  [ ]

Para cada tabla, comparar las columnas declaradas en el DDL contra
`PRAGMA table_info(tabla)`. Verificar nombre y tipo.

**Criterio:** no se comparan defaults ni constraints de columna — solo
nombre y tipo afinidad. Los constraints se verifican en T4.

---

## T4 — Test de foreign keys (R3)  [ ]

Para cada tabla:
1. Extraer FKs del DDL.
2. Obtener FKs reales con `PRAGMA foreign_key_list(tabla)`.
3. FKs declaradas en DDL que no existen en PRAGMAs → error.
4. Columnas `*_id` sin FK → advertencia (no fallo, hay casos legítimos).

**D2:** `grupos.sala_id` sin FK declarada. Marcar como `xfail` con reason
`"D2: FK fantasma — se resuelve en backend_04"`.

---

## T5 — Test de orden de dependencias (R6)  [ ]

Recorrer `SCHEMA` en orden. Para cada tabla, verificar que todas las tablas
que referencia ya aparecieron antes en la lista.

**D1:** `grupos` referencia `usuarios` antes de crearla. Marcar como `xfail`
con reason `"D1: orden de dependencias violado — se resuelve en backend_04"`.

---

## T6 — Test de índices (R4)  [ ]

Verificar que todo índice declarado en `INDICES` existe en `sqlite_master`
con `type='index'`.

---

## T7 — Test de triggers (R5)  [ ]

Verificar que todo trigger declarado en `TRIGGERS` existe en `sqlite_master`
con `type='trigger'`.

---

## T8 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/test_schema_integrity.py -v
.venv/Scripts/python.exe scripts/init.py
```

TODO VERDE (los `xfail` de D1 y D2 no bloquean). El paso no se declara
`done` sin esto.

**Artefacto:** `progress/impl_backend_02b.md` con el resumen.
