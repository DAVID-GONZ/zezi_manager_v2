# Tasks: mejora_10c — Consolidación de naming (opcional / baja prioridad)

Prerrequisitos: ninguno. Cero cambio visual (solo renombres).

---

## T1 — Inventario de nombres a renombrar

- Correr `python scripts/audit_design.py` y tomar la lista "presentacionales".
- Filtrar a los que tienen reemplazo semántico claro y ≤ pocos usos. Candidato inicial:
  `text-xs-meta` → `meta-text`. (Los `u-*`, `bg-*-soft`, `flex-*`, `gap-*` son utilidades
  intencionales: **no** renombrar.)
- Producir la tabla `viejo → nuevo` en `progress/impl_mejora_10c.md`.

---

## T2 — Rename seguro (uno por uno)

Por cada par `viejo → nuevo`:
- `grep -rn "viejo" src/interface/design/styles src/interface/pages` (CSS + `.classes()` + f-strings).
- Renombrar la definición en CSS y migrar cada uso.
- `python scripts/check_design.py --all` → regla G verde (sin clases indefinidas).

---

## T3 — Documentar la convención

**Archivo:** `src/interface/design/styles/CLASS_CONTRACT.md`
- Añadir sección "Convención de nombres para clases nuevas":
  componentes `comp` + `comp--variante`; utilidades semánticas `u-*`;
  prohibido introducir nombres presentacionales nuevos.

---

## T4 — Verificación

- `python scripts/audit_design.py` → la lista de presentacionales se reduce; % semántico sube.
- `python scripts/check_design.py --all` y `python init.py` en verde.
