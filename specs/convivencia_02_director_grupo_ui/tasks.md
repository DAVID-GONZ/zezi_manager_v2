# convivencia_02 — Director de grupo: RBAC de /admin/grupos + asignación en UI

> Parte de la épica `convivencia_00_roadmap` (Fase 1). Depende de **convivencia_01** (columna+modelo+repo listos).

## Contexto y decisión (David)

El **coordinador debe tener acceso pleno a `/admin/grupos`** (en el contexto real colombiano gestiona grupos), y tanto **director como coordinador** asignan el director de grupo desde ahí.

Estado actual:
- `/admin/grupos` está en `_DIRECTOR` (main.py:180) — coordinador no entra.
- `grupos.py` hace CRUD de grupos. Candidatos a director de grupo = docentes con asignación en el grupo: `asignacion_service.listar_por_grupo(grupo_id)` (devuelve `AsignacionInfo` con docente).

## Tareas

### T1 — RBAC de la ruta
- En `main.py`, cambiar `/admin/grupos` de `roles=_DIRECTOR` a `roles=_DIR_COORD` (acceso pleno: crear/editar/eliminar grupos y grados, igual que director; **sin gateo interno**).
- Revisar `grupos.py` por si asume `usuario_rol == "director"` en algún gating interno; si existe, ampliarlo a coordinador para no romper el acceso pleno.

### T2 — Servicio: asignar director de grupo
- Añadir en el servicio de grupos un método de alto nivel `asignar_director_grupo(grupo_id, usuario_id | None)` (con `@requiere_escritura` y scope tenant), que valide que el usuario destino sea un docente **con asignación activa en ese grupo** (candidato válido) antes de persistir. `None` = desasignar.
- Método auxiliar `candidatos_director_grupo(grupo_id)` que devuelva los docentes con asignación en el grupo (reutilizando `asignacion_service`/repo) para poblar el selector.

### T3 — UI en grupos.py
- En el formulario/fila de grupo, añadir un **selector "Director de grupo"** poblado con `candidatos_director_grupo(grupo_id)` (mostrar nombre del docente; opción "— Sin asignar —"). Al cambiar, llamar `asignar_director_grupo(...)` y refrescar.
- Mostrar el director de grupo actual en el listado de grupos.
- Respetar el design system (form_dialog/select, clases CSS, `ThemeManager.icono`, sin colores quemados). Manejar el caso "grupo sin asignaciones aún" (selector vacío + hint).

### T4 — Verificación
- `python init.py` VERDE (`.venv/Scripts/python.exe`); `check_design --file grupos.py` y `check_imports` de interface en verde.
- Tests de servicio: `asignar_director_grupo` rechaza un usuario sin asignación en el grupo; acepta uno válido; `None` desasigna. `candidatos_director_grupo` devuelve solo docentes del grupo.
- Verificación manual documentada: coordinador entra a `/admin/grupos` y asigna director de grupo.
- `progress/impl_convivencia_02.md` + `progress/review_convivencia_02.md`.

## criterio_done
Coordinador y director acceden plenamente a `/admin/grupos`; desde ahí asignan/cambian/quitan el director de grupo (solo entre docentes con asignación en el grupo); el listado muestra el director actual; tests de servicio verdes; `python init.py` verde; check_design/check_imports verdes.
