# rebrand_03_seed_data — Tareas

Scope: solo `src/infrastructure/db/seed.py`.
Cualquier otro archivo -> PARAR y reportar al leader.

---

## T1 — Emails de dominio

**Artefacto:** `src/infrastructure/db/seed.py`

Reemplazar todas las ocurrencias de `@zeci.edu.co` por `@avedra.edu.co`
(17 lineas, 219-247). Usar replace_all.

**Verificacion:**
```
grep -c "zeci.edu.co" src/infrastructure/db/seed.py
```
Debe dar `0`.

---

## T2 — Nombre de institucion en configuracion de anio

**Artefacto:** `src/infrastructure/db/seed.py`

- Linea 456: `"Institucion Educativa ZECI"` -> `"Institucion Educativa Demo"`.

**Verificacion:**
```
grep -c "ZECI" src/infrastructure/db/seed.py
```
Debe dar `0`.

---

## Cierre del paso

```
grep -rni "zeci" src/ --include="*.py"
```
Debe dar `0` resultados (el docstring ya fue limpiado en Paso 2).

Escribir el resumen en `progress/impl_rebrand_03_seed_data.md` y
devolver al leader solo esa referencia.
