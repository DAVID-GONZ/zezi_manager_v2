# convivencia_14_promocion_a_comportamiento — Tasks
> ⚠️ TOCA BD — puerta de aprobación de David antes del implementer.
> Prerequisito: convivencia_11 DONE.

## Objetivo
Añadir FK `registro_comportamiento_id` (nullable) a `observaciones_periodo`,
de modo que una observación de categoría comportamental pueda "promoverse" a
un `RegistroComportamiento` formal, con trazabilidad bidireccional.

## Scope
```
src/infrastructure/db/schema.py
src/domain/models/convivencia.py
src/domain/ports/convivencia_repo.py
src/infrastructure/db/repositories/sqlite_convivencia_repo.py
src/services/convivencia_service.py
src/interface/pages/convivencia/observaciones.py
tests/
```

## Diseño

### Columna nueva en `observaciones_periodo` (migración idempotente)
```python
_asegurar_columna(
    conn, "observaciones_periodo", "registro_comportamiento_id",
    "INTEGER REFERENCES registros_comportamiento(id) ON DELETE SET NULL"
)
```

### Modelo `ObservacionPeriodo` actualizado
```python
registro_comportamiento_id: int | None = None
```

### Método nuevo en servicio
```python
def promover_a_comportamiento(
    self,
    observacion_id: int,
    usuario_id: int | None = None,
    usuario_rol: str | None = None,
) -> RegistroComportamiento:
    """
    Solo disponible para observaciones cuya CategoriaObservacion.es_comportamental=True.
    Crea un RegistroComportamiento a partir del texto de la observación
    y enlaza la observación al registro creado.
    RBAC: DIRECTOR, COORDINADOR o director de grupo del grupo del estudiante.
    """
```

Internamente:
1. Obtener la observación. Verificar que `categoria_id` apunta a una categoría
   con `es_comportamental=True`. Si no → `ValueError("La categoría no es comportamental")`.
2. Verificar RBAC.
3. Crear `RegistroComportamiento(estudiante_id=obs.estudiante_id,
   grupo_id=<resolver desde asignacion>, periodo_id=obs.periodo_id,
   tipo=TipoRegistro.DIFICULTAD, descripcion=obs.texto, usuario_id=usuario_id)`.
4. Guardar el registro vía `self._repo.guardar_registro(registro)`.
5. Actualizar la observación: `obs.registro_comportamiento_id = registro.id`.
   Llamar `self._repo.actualizar_observacion(obs)`.
6. Retornar el `RegistroComportamiento` creado.

### UI
En `observaciones.py`, añadir botón "Promover a Comportamiento" por fila, visible si:
- `obs.categoria_id` apunta a categoría `es_comportamental=True`.
- `obs.registro_comportamiento_id is None` (aún no promovida).
- RBAC: director, coordinador, o director de grupo.
- `confirm_dialog` antes de ejecutar.
- Tras promover, refrescar la lista (el botón desaparece porque `registro_comportamiento_id != None`).

## Tareas

### T1 — `schema.py`: migración idempotente
Añadir `_asegurar_columna` para `registro_comportamiento_id`.
Verificación: `PRAGMA table_info(observaciones_periodo)` incluye la columna.

### T2 — `convivencia.py`: actualizar `ObservacionPeriodo`
Añadir `registro_comportamiento_id: int | None = None`.

### T3 — Repo: propagar campo en INSERT/UPDATE/mapper
- `guardar_observacion` y `actualizar_observacion` incluyen `registro_comportamiento_id`.
- `_row_to_observacion` mapea el campo.

### T4 — `convivencia_service.py`: añadir `promover_a_comportamiento`
Con `@requiere_escritura`. Resolver `grupo_id` desde la asignación del contexto
usando `catalogo_academico_svc_provider`.

### T5 — `observaciones.py`: botón "Promover a Comportamiento"
- Visible según las condiciones de la sección Diseño.
- `confirm_dialog("¿Convertir en registro oficial de comportamiento?")`.
Verificación: `check_design`, `check_imports --layer interface`

### T6 — Tests
`tests/unit/services/test_convivencia_service.py`:
- `test_promover_a_comportamiento_crea_registro` — flujo nominal.
- `test_promover_a_comportamiento_categoria_no_comportamental` — `ValueError`.
- `test_promover_a_comportamiento_ya_promovida` — segunda llamada crea otro registro
  (no error, simplemente crea una nueva entrada; la observación queda con el último `id`).

`tests/integration/`: añadir test de integración que verifique la FK en BD.

## criterio_done
- [ ] Columna `registro_comportamiento_id` en `observaciones_periodo` (idempotente).
- [ ] `ObservacionPeriodo.registro_comportamiento_id` en el modelo.
- [ ] `promover_a_comportamiento` en servicio valida `es_comportamental`.
- [ ] FK se persiste en BD después de promover.
- [ ] Botón en UI visible solo para categorías comportamentales sin promover.
- [ ] Tests nuevos verdes.
- [ ] `init.py --quick` → ENTORNO OK.
