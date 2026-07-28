# convivencia_13_catalogo_retroalimentacion — Tasks
> Sin cambios de BD. Prerequisito: convivencia_12 DONE.

## Objetivo
Cerrar el ciclo del catálogo: permitir que una observación libre existente
se promueva a plantilla reutilizable, y que al crear una nueva observación
se sugieran automáticamente las plantillas más usadas de la categoría
seleccionada (ordenadas por `uso_count` DESC).

## Scope
```
src/services/convivencia_service.py
src/interface/pages/convivencia/observaciones.py
tests/unit/services/test_convivencia_service.py
```

## Diseño

### Nuevo método en servicio
```python
def promover_observacion_a_plantilla(
    self,
    observacion_id: int,
    usuario_id: int | None = None,
    usuario_rol: str | None = None,
) -> PlantillaObservacion:
    """
    Crea una nueva PlantillaObservacion a partir del texto y categoria_id
    de una ObservacionPeriodo existente.
    RBAC: solo DIRECTOR y COORDINADOR pueden promover.
    Retorna la nueva plantilla guardada.
    """
```

Internamente:
1. Obtener la observación vía `self._repo.get_observacion(observacion_id)`.
2. Verificar RBAC: solo `DIRECTOR` / `COORDINADOR`.
3. Crear `PlantillaObservacion(texto=obs.texto, categoria_id=obs.categoria_id)`.
4. Llamar `self._repo.guardar_plantilla(plantilla)`.
5. Retornar la plantilla guardada.

### Sugerencias de plantillas más usadas
En `listar_plantillas`, el repo ya ordena por `uso_count DESC` (añadir al ORDER BY
en la query existente). El servicio expone `listar_plantillas_sugeridas(categoria_id, limite=5)`.

```python
def listar_plantillas_sugeridas(
    self,
    categoria_id: int | None = None,
    limite: int = 5,
) -> list[PlantillaObservacion]:
    return self._repo.listar_plantillas(categoria_id=categoria_id, solo_activas=True)[:limite]
```

### UI actualizada
En `observaciones.py`:
- El selector de plantillas (abierto desde "Usar plantilla") muestra las plantillas
  ordenadas por `uso_count` DESC (ya ordenadas por el repo).
- Añadir botón de acción "Promover a plantilla" en cada fila de observación existente,
  visible solo para coordinador/director. Usa `confirm_dialog` antes de ejecutar.
- Al promover → `toast_success("Observación guardada como plantilla")`.

## Tareas

### T1 — `convivencia_service.py`: añadir `promover_observacion_a_plantilla` y `listar_plantillas_sugeridas`
Verificar: `check_imports --layer services`

### T2 — `sqlite_convivencia_repo.py`: ordenar `listar_plantillas` por `uso_count DESC`
Cambiar la query de `listar_plantillas` para añadir `ORDER BY uso_count DESC, nombre ASC`.
(Si no hay campo `nombre`, ordenar solo por `uso_count DESC`.)

### T3 — `observaciones.py`: botón "Promover a plantilla" por fila + sugerencias
- Botón visible solo si `ctx.rol in (Rol.DIRECTOR, Rol.COORDINADOR)`.
- `confirm_dialog` antes de promover.
- Selector de plantillas usa el servicio con sugerencias ordenadas.
Verificar: `check_design`, `check_imports --layer interface`

### T4 — Tests
`tests/unit/services/test_convivencia_service.py`:
- `test_promover_observacion_a_plantilla_crea_plantilla` — servicio crea y guarda plantilla.
- `test_promover_observacion_profesor_no_autorizado` — profesor → `PermissionError`.
- `test_listar_plantillas_sugeridas_limite` — retorna máximo N elementos.

## criterio_done
- [ ] `promover_observacion_a_plantilla` en servicio (solo dir/coord).
- [ ] `listar_plantillas_sugeridas` en servicio.
- [ ] `listar_plantillas` ordena por `uso_count DESC`.
- [ ] Botón "Promover" visible en UI para directivos.
- [ ] 3 tests unitarios verdes.
- [ ] `init.py --quick` → ENTORNO OK.
