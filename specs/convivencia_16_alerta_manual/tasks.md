# convivencia_16_alerta_manual — Tasks
> Sin cambios de BD. Prerequisito: convivencia_15 DONE.

## Objetivo
Director y coordinador pueden crear una alerta de tipo `SEGUIMIENTO_REQUERIDO`
dirigida a un profesor específico de un estudiante, con un mensaje libre.
La alerta aparece en el panel del profesor destinatario.

## Scope
```
src/services/convivencia_service.py
src/interface/pages/convivencia/seguimiento.py   ← crear o ampliar
tests/unit/services/test_convivencia_service.py
```

## Diseño

### RBAC
Solo `Rol.DIRECTOR` y `Rol.COORDINADOR` pueden crear alertas de seguimiento manuales.

### DTO nuevo
```python
class NuevaAlertaSeguimientoDTO(BaseModel):
    estudiante_id:    int
    usuario_destino_id: int        # profesor destinatario
    descripcion:      str          # mensaje libre
    nivel:            NivelAlerta  = NivelAlerta.ADVERTENCIA
```

### Método nuevo en `ConvivenciaService`
```python
def crear_alerta_seguimiento_manual(
    self,
    dto: NuevaAlertaSeguimientoDTO,
    usuario_id: int | None = None,
    usuario_rol: str | None = None,
) -> Alerta:
    """
    Crea una Alerta(tipo=SEGUIMIENTO_REQUERIDO, usuario_destino_id=dto.usuario_destino_id).
    RBAC: solo DIRECTOR y COORDINADOR.
    """
```
Internamente: verificar RBAC → construir `Alerta(tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO, ...)` → `self._alerta_repo.guardar_alerta(alerta)`.

### Página `seguimiento.py`
Nueva página `/convivencia/seguimiento` con dos secciones:

**Sección "Crear alerta de seguimiento"** (visible solo para director/coordinador):
- Selector de estudiante del grupo.
- Selector de profesor destinatario (profesores con asignación en el grupo).
- Campo de mensaje/descripción (textarea).
- Nivel (selector: Advertencia / Crítica).
- Botón "Enviar alerta" con `confirm_dialog`.
- `toast_success` al crear.

**Sección "Alertas enviadas"** (solo para director/coordinador):
- Tabla de alertas `SEGUIMIENTO_REQUERIDO` del grupo del contexto.
- Columnas: Estudiante, Profesor destinatario, Descripción, Nivel, Fecha, Estado.

Registrar ruta en `main.py`: `/convivencia/seguimiento`.
Añadir a `NAV_ITEMS` bajo grupo "Aula", permisos `[Rol.DIRECTOR, Rol.COORDINADOR, Rol.DIRECTOR_GRUPO]` (director de grupo solo puede ver, no crear — el guard lo diferencia).

## Tareas

### T1 — `convivencia.py`: añadir `NuevaAlertaSeguimientoDTO`
En `src/domain/models/convivencia.py` (o en el propio `convivencia_service.py`
como DTO local si es más conveniente para evitar importación circular).

### T2 — `convivencia_service.py`: añadir `crear_alerta_seguimiento_manual`
Con `@requiere_escritura`.
Verificar: `check_imports --layer services`

### T3 — `seguimiento.py`: implementar la página
Patrón estándar: guard → _s → refreshable → app_layout.
Solo para director/coordinador el formulario de creación.
Verificar: `check_design`, `check_imports --layer interface`

### T4 — Registrar ruta y nav (`main.py`, `layout.py`)

### T5 — Tests
`tests/unit/services/test_convivencia_service.py`:
- `test_crear_alerta_seguimiento_manual_flujo_nominal` — director crea alerta → `alerta_repo.guardar_alerta` llamado con `TipoAlerta.SEGUIMIENTO_REQUERIDO`.
- `test_crear_alerta_seguimiento_profesor_no_autorizado` — profesor → `PermissionError`.

## criterio_done
- [ ] `crear_alerta_seguimiento_manual` en servicio (RBAC dir/coord).
- [ ] Página `/convivencia/seguimiento` carga sin errores.
- [ ] Formulario crea alerta con `tipo=SEGUIMIENTO_REQUERIDO` y `usuario_destino_id` correcto.
- [ ] `check_design` y `check_imports` verdes.
- [ ] 2 tests unitarios verdes.
- [ ] `init.py --quick` → ENTORNO OK.
