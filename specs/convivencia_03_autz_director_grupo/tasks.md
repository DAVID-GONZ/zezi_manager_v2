# convivencia_03 — Autorización por objeto: "¿es director de este grupo?"

> Parte de la épica `convivencia_00_roadmap` (Fase 1). Depende de **convivencia_01/02**. Es el helper que consumirán Comportamiento (Fase 2) y Seguimiento (Fase 5).

## Contexto y decisión (David)

La autoridad del director de grupo es **por objeto**, no un rol global. Se necesita una función reutilizable, fuente única de verdad, consultable desde servicio y vista (defensa en profundidad, como `rbac_usuarios.py`).

Estado actual:
- Ya existe autorización por objeto para institución (paso_36) y política pura `policies/rbac_usuarios.py`. Este paso añade la política análoga para dirección de grupo.

## Tareas

### [x] T1 — Política / helper de autorización
- Crear una función/política reutilizable (ubicación consistente con el proyecto: `domain/policies/` para lógica pura si no requiere BD, o método de servicio si necesita consultar el repo). Firmas objetivo:
  - `es_director_de_grupo(usuario_id, grupo_id) -> bool`
  - `es_director_de_grupo_de_estudiante(usuario_id, estudiante_id, periodo_id?) -> bool` (resuelve el grupo del estudiante y compara).
  - Conveniencia: `puede_gestionar_comportamiento(usuario_rol, usuario_id, grupo_id) -> bool` = director/coordinador **o** director de grupo de ese grupo. (Se usará en convivencia_04.)
- Los directivos (director/coordinador) siempre pasan; el profesor solo si es director del grupo en cuestión. Documentar la matriz en el docstring.

### [x] T2 — Tests
- Tests unitarios de la política: director de grupo del grupo → True; profesor de otro grupo → False; director/coordinador → True; grupo/estudiante inexistente → False (sin excepción). Mockear el repo donde aplique.

### [x] T3 — Verificación
- `python init.py` VERDE (`.venv/Scripts/python.exe`).
- `progress/impl_convivencia_03.md` + `progress/review_convivencia_03.md`.

## criterio_done
Existe un helper reutilizable y testeado que responde "¿este usuario es director de este grupo / del grupo de este estudiante?" y la conveniencia `puede_gestionar_comportamiento`, con matriz documentada y tests unitarios verdes; `python init.py` verde. Aún no se consume desde rutas/servicios de comportamiento (eso es convivencia_04).
