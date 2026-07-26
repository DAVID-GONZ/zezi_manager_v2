# convivencia_01 — Director de grupo: esquema + modelo + repo (backend)

> Parte de la épica `convivencia_00_roadmap` (Fase 1). Backend puro, **sin UI** (la UI es convivencia_02).

## Contexto y decisión (David)

No existe el concepto de **director de grupo** (el `grupos` no tiene columna; el `Rol` solo es admin/director/coordinador/profesor). Decisión: modelarlo como **FK `grupos.director_grupo_id → usuarios.id`** (NO un Rol nuevo). Un profesor sigue siendo profesor, pero es director del grupo X; la autoridad es **por objeto** (se usa en pasos posteriores).

Estado actual:
- Tabla `grupos` (schema.py:225) sin `director_grupo_id`. Modelo `Grupo` en `infraestructura.py:143`.
- Repo `sqlite_infraestructura_repo.py` (grupos) + `IInfraestructuraRepository`.
- Servicio de grupos: `infraestructura_service` / `catalogo_academico_service` (verificar cuál gestiona grupos).

## ⚠️ Puerta de aprobación (leader.md)
Este paso **toca el esquema de BD y el modelo `Grupo`** → requiere **aprobación explícita de David** antes de lanzar el `implementer`. No se toca `src/` hasta el "aprobado".

## Tareas

### T1 — Esquema
- En `schema.py`, `CREATE TABLE ... grupos`: añadir columna `director_grupo_id INTEGER` con `FOREIGN KEY(director_grupo_id) REFERENCES usuarios(id) ON DELETE SET NULL`. Nullable (un grupo puede no tener director asignado aún).
- Confirmar idempotencia según el patrón del proyecto (`CREATE TABLE IF NOT EXISTS` como única fuente de verdad; si el proyecto usa migración/rebuild para BDs existentes, seguir ese mismo patrón — revisar cómo se hizo en pasos previos que añadieron columnas).
- Índice opcional `idx_grupos_director ON grupos(director_grupo_id)` si aporta (consultas "grupos que dirijo").

### T2 — Modelo de dominio
- `Grupo` (`infraestructura.py`): añadir `director_grupo_id: int | None = None`. Sin validador especial (FK opcional). Mantener orden/estilo del modelo.

### T3 — Repositorio + puerto
- `IInfraestructuraRepository` (grupos) y `sqlite_infraestructura_repo.py`: que el CRUD de grupos **lea y escriba** `director_grupo_id` (SELECT, INSERT/UPDATE, hidratación del modelo). Respetar el scope multi-tenant existente.
- Añadir lectura auxiliar mínima si hace falta para pasos siguientes (p.ej. `get_grupo` ya devuelve el campo). NO añadir aquí el método de "asignar director" de alto nivel (eso es convivencia_02, capa servicio/UI).

### T4 — Verificación
- `python init.py` VERDE (`.venv/Scripts/python.exe`). Corregir cualquier fallout de hidratación del modelo.
- Test de integración: guardar un grupo con `director_grupo_id` y releerlo conserva el valor; `ON DELETE SET NULL` deja el grupo con `director_grupo_id = NULL` al borrar el usuario.
- `progress/impl_convivencia_01.md` + `progress/review_convivencia_01.md`.

## criterio_done
La tabla `grupos` tiene `director_grupo_id` (FK a usuarios, ON DELETE SET NULL), el modelo `Grupo` lo expone, y el repo lo persiste/lee correctamente; test de integración verde; `python init.py` verde. Sin cambios de UI ni de RBAC todavía.
