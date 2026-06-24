# paso_44 — Catálogo de grados editable en /admin/grupos

## Contexto y decisión (David)

Para que "cada nivel actúe con un significado real" (1001=décimo, 602=sexto), el **catálogo de grados** debe poder editarse y guardarse. David eligió hacerlo **junto a Grupos (`/admin/grupos`)**.

Estado actual:
- Tabla `grados` (numero 1-13 UNIQUE, nombre, min_estudiantes, max_estudiantes, horas_semanales). Modelo `Grado`. CRUD ya existe en `plan_estudios_service`: `listar_grados()`, `guardar_grado(...)`, `eliminar_grado(numero)`.
- `/admin/grupos` (`grupos.py`, director-only por paso_35) crea/edita grupos con el `grado` como un **number libre 1-13**, sin catálogo.

**Nota multi-tenant:** `grados` es un catálogo **global** (sin `institucion_id`); el significado de los niveles es universal (no se vuelve per-institución en este paso). Lo específico de cada institución son sus grupos (ya con `institucion_id`).

## Tareas

### T1 — Sección "Grados" en grupos.py
- Añadir en `/admin/grupos` un panel/sección **"Grados"** (director-only; la página ya lo es) que liste el catálogo con `Container.plan_estudios_service().listar_grados()`: numero, nombre, min/max estudiantes, horas. 
- Acciones: **crear/editar** un grado (numero, nombre, min/max, horas) vía `guardar_grado(...)` y **eliminar** vía `eliminar_grado(numero)` (con confirm_dialog; impedir/avisar si hay grupos usando ese grado — si el servicio no lo valida, al menos advertir). Refrescar la lista al guardar.
- Respetar el design system (form_dialog/clases CSS; sin colores quemados; ThemeManager.icono).

### T2 — Campo "grado" del grupo = select del catálogo
- En el formulario de crear/editar grupo (`grupos.py`), cambiar el campo **grado** de number libre a un **select** poblado con los grados definidos (`numero — nombre`), de modo que los grupos referencien grados del catálogo (significado real del nivel). Fallback razonable si el catálogo está vacío (p.ej. permitir 1-13 o avisar de definir grados primero). Mantener la validación 1-13.

### T3 — Verificación
- `python init.py` VERDE (baseline 1216 passed, 1 skipped; corregir fallout). check_design `--file` grupos.py + check_imports interface en verde.
- Tests (si aplica a servicio): `guardar_grado`/`eliminar_grado` funcionan; el listado refleja los cambios. (UI sin test de NiceGUI, documentar.)
- `progress/impl_paso_44.md`.

## criterio_done
En `/admin/grupos` el director puede ver, crear, editar y eliminar grados (numero→nombre, min/max, horas) vía `plan_estudios_service`, y el campo grado del grupo es un select del catálogo; `python init.py` verde; check_design/check_imports verdes. (grados global — nota de multi-tenant documentada.)
