# Tasks — paso_12e_menu_ia

## Resumen

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | Reescribir NAV_ITEMS | `layout.py` | grep estructura |
| T2 | Comparar permisos por rol con original | — | revisión manual |
| T3 | test_navitems.py | `tests/unit/interface/design/` | pytest |
| T4 | Smoke por rol | manual | login × 4 roles |
| T5 | Verificación final | — | init.py + tests |

---

## T1 — Reescribir NAV_ITEMS

**Prerequisito:** copiar de respaldo (`progress/impl_12e.md` § "Backup NAV_ITEMS
original") el contenido actual de `NAV_ITEMS` antes de tocarlo. Esto se conserva
como referencia para T2.

En `src/interface/design/layout.py`, reemplazar el bloque `NAV_ITEMS: list[dict] = [...]`
(líneas ~60-143) por el bloque completo de design.md §1.

**Verificación rápida:**
```
python -c "from src.interface.design.layout import NAV_ITEMS; print(len([i for i in NAV_ITEMS if 'divider' not in i]))"
# debe imprimir 6
```

---

## T2 — Verificar permisos por rol contra original

Para cada subitem en el nuevo NAV_ITEMS, comparar el campo `"rol"` con el del
NAV_ITEMS original (respaldado en T1).

Procedimiento:

1. Generar dos dicts `{ruta: roles}`:
   ```python
   def extraer(items):
       resultado = {}
       for it in items:
           if "ruta" in it:
               resultado[it["ruta"]] = set(it["rol"])
           for c in it.get("children", []):
               if "ruta" in c:
                   resultado[c["ruta"]] = set(c["rol"])
       return resultado
   ```
2. Diff:
   ```python
   for ruta, roles_nuevo in extraer(NAV_NUEVO).items():
       roles_viejo = NAV_VIEJO_DICT.get(ruta)
       if roles_viejo and roles_viejo != roles_nuevo:
           print(f"DIFF en {ruta}: antes {roles_viejo}, ahora {roles_nuevo}")
   ```
3. Para cada diff, el implementer decide:
   - Si el cambio es intencional (justificado en design.md): documentarlo.
   - Si es accidental: corregir el nuevo NAV_ITEMS para preservar el viejo.

**Resultado documentado en `progress/impl_12e.md` §T2 con tabla "ruta → roles
antes / roles después / decisión".**

---

## T3 — Test de invariantes

Crear `tests/unit/interface/design/test_navitems.py` con el contenido completo de
design.md §3 (incluyendo `RUTAS_REQUERIDAS`).

**Importante:** la lista `RUTAS_REQUERIDAS` debe construirse a partir del
NAV_ITEMS original (respaldado en T1), no inventada. El implementer la genera
una vez con:

```python
from copy import deepcopy
# pega aquí el NAV_ITEMS original y corre:
def flat(items):
    r = []
    for it in items:
        if "ruta" in it: r.append(it["ruta"])
        for c in it.get("children", []):
            if "ruta" in c: r.append(c["ruta"])
    return r
print(sorted(flat(NAV_VIEJO)))
```

Y pega el resultado como set literal.

**Verificación:**
```
pytest tests/unit/interface/design/test_navitems.py -v
```

Los 3 tests deben pasar.

---

## T4 — Smoke por rol

Arrancar app. Hacer login con cada uno de los 4 roles:

- **admin**: ve los 6 grupos. Bajo Académico ve los 5 hijos. Bajo Admin ve los 2.
- **director**: igual que admin (mismos permisos generalmente).
- **coordinador**: ve 5 grupos (no Admin). Bajo Académico ve 2 hijos
  (Estudiantes, Horarios). Bajo Evaluación ve los 5. Bajo Informes ve los 6.
- **profesor**: ve 5 grupos (no Admin). Bajo Académico ve 2 hijos (Estudiantes,
  Horarios). Bajo Evaluación ve 3-4 (sin Cierre de Periodo ni Cierre de Año).
  Bajo Informes ve 4 (sin Consolidados).

Documentar resultado por rol en `progress/impl_12e.md` §T4.

---

## T5 — Verificación final

```
python init.py                                 # verde
pytest tests/ --tb=short                       # verde
pytest tests/unit/interface/design/ -v         # foco
```

Reviewer:
- NAV_ITEMS tiene exactamente la estructura de design.md §1.
- No hay rutas perdidas (test pasa).
- Permisos por rol idénticos al original o cambios documentados.
- No hay renames de archivos ni de rutas (URLs intactas).
- Iconos: ningún Material Symbol inventado (verificar contra lista oficial si
  hay duda — `book`, `co_present`, `dashboard`, `analytics`, `person`,
  `grading`, etc., son válidos).
