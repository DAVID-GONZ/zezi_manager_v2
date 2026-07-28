# convivencia_18_vista_seguimiento_360 — Tasks
> Sin cambios de BD. Prerequisito: convivencia_15 + convivencia_16 DONE.

## Objetivo
Ampliar la página `/convivencia/seguimiento` (creada en convivencia_16) con una
sección de **vista 360°** por estudiante: consolida notas académicas + nota de
comportamiento + observaciones del periodo + alertas activas. Solo lectura.
RBAC: director, coordinador, director de grupo del grupo del contexto.

## Scope
```
src/services/convivencia_service.py
src/interface/pages/convivencia/seguimiento.py
tests/unit/services/test_convivencia_service.py
```

## Diseño

### DTO de salida
```python
class Seguimiento360DTO(BaseModel):
    estudiante_id:       int
    estudiante_nombre:   str
    periodo_id:          int
    nota_comportamiento: float | None
    concepto:            str | None
    nivel_comportamiento: str | None
    observaciones:       list[str]           # textos de obs públicas del periodo
    alertas_activas:     list[str]           # descripciones de alertas no resueltas
    promedio_notas:      float | None        # promedio académico del periodo (opcional)
```

### Método nuevo en `ConvivenciaService`
```python
def vista_360(
    self,
    estudiante_id: int,
    periodo_id: int,
    usuario_id: int | None = None,
    usuario_rol: str | None = None,
) -> Seguimiento360DTO:
    """
    Consolida datos de convivencia + alerta del estudiante en el periodo.
    RBAC: DIRECTOR, COORDINADOR o director_de_grupo del grupo del estudiante.
    """
```

Internamente:
1. RBAC: verificar rol. Para director de grupo, usar el helper `es_director_de_grupo_de_estudiante`
   (diferido de la Fase 1 — implementar aquí si no existe, o simplemente verificar
   `es_director_de_grupo(usuario_id, grupo_id)` pasando el `grupo_id` resuelto desde
   el estudiante).
2. `concepto_dto = self.get_concepto_periodo(estudiante_id, periodo_id)`.
3. `observaciones = self._repo.listar_observaciones_por_estudiante(estudiante_id, periodo_id, solo_publicas=True)`.
4. `alertas = self._alerta_repo.listar_alertas(estudiante_id, solo_pendientes=True)` (filtrar tipo `SEGUIMIENTO_REQUERIDO` o todas).
5. Construir y retornar `Seguimiento360DTO`.

### UI en `seguimiento.py`
Añadir sección "Vista 360°" a la página existente:
- Selector de estudiante del grupo (un solo selector compartido con la sección de alertas).
- Selector de periodo.
- Botón "Ver seguimiento" → llama `vista_360` y renderiza resultado.
- Resultado: tarjetas con `stat_card` para la nota de comportamiento + promedio,
  lista de observaciones con `empty_state` si no hay, panel de alertas activas.
- Todo solo lectura, sin botones de acción.

RBAC:
- Director/coordinador: acceso pleno (ven también la sección de creación de alertas de convivencia_16).
- Director de grupo: solo ve la sección 360° (la sección de creación de alertas está oculta).

## Tareas

### T1 — `convivencia.py`: añadir `Seguimiento360DTO`
### T2 — `convivencia_service.py`: añadir `vista_360`
- Implementar helper `_resolver_grupo_de_estudiante(estudiante_id)` si no existe,
  usando `estudiante_svc_provider` para obtener el `grupo_id` del estudiante.
- RBAC: director de grupo del grupo del estudiante (usar `_es_director_de_grupo`).
Verificar: `check_imports --layer services`

### T3 — `seguimiento.py`: añadir sección 360° a la página existente
- Compartir el selector de estudiante con la sección de alertas.
- `stat_card` para nota de comportamiento.
- `empty_state` cuando no hay observaciones ni alertas.
Verificar: `check_design`, `check_imports --layer interface`

### T4 — Tests
`tests/unit/services/test_convivencia_service.py`:
- `test_vista_360_flujo_nominal_director` — director obtiene DTO con datos.
- `test_vista_360_director_grupo_autorizado` — director de grupo del grupo del estudiante accede.
- `test_vista_360_profesor_no_autorizado` — profesor → `PermissionError`.
- `test_vista_360_sin_datos` — sin nota ni observaciones → DTO con campos None / listas vacías.

## criterio_done
- [ ] `Seguimiento360DTO` en models.
- [ ] `vista_360` en servicio con RBAC correcto (incluyendo director de grupo).
- [ ] Sección 360° en la página de seguimiento.
- [ ] `empty_state` cuando no hay datos.
- [ ] `check_design` y `check_imports` verdes.
- [ ] 4 tests unitarios verdes.
- [ ] `init.py --quick` → ENTORNO OK.
