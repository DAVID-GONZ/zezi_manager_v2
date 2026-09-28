# rebrand_05_pyproject — Tareas

Scope: solo `pyproject.toml`.
Cualquier otro archivo -> PARAR y reportar al leader.

---

## T1 — Metadata del paquete

**Artefacto:** `pyproject.toml`

- Linea 2: `name = "zeci-manager-v2"` -> `name = "avedra"`.
- Linea 4: `description = "Add your description here"` ->
  `description = "AVEDRA — Administracion y Visualizacion Educativa para la Direccion y el Registro Academico"`.

**Verificacion:**
```
grep -c "zeci" pyproject.toml
```
Debe dar `0`.

---

## Cierre del paso

```
grep -rni "zeci" pyproject.toml config.py main.py container.py src/ tests/
python scripts/init.py
```
Grep sin resultados en ningun archivo. `init.py` en RESULTADO FINAL: TODO VERDE.

Escribir el resumen en `progress/impl_rebrand_05_pyproject.md` y
devolver al leader solo esa referencia.
