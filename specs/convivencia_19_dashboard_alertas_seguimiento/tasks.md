# convivencia_19_dashboard_alertas_seguimiento — Tasks
> Sin cambios de BD. Prerequisito: convivencia_15 + convivencia_16 DONE.

## Objetivo
El dashboard (`/inicio`) muestra las alertas de tipo `SEGUIMIENTO_REQUERIDO`
dirigidas al profesor logueado (`alertas.usuario_destino_id = ctx.usuario_id`).
Reutilizar el panel de alertas existente en `inicio.py` o añadir una sección
"Seguimientos pendientes" diferenciada.

## Scope
```
src/interface/pages/inicio.py
tests/unit/interface/   ← si hay tests de inicio existentes
```
Posiblemente también:
```
src/services/alerta_service.py   (si no expone el método de filtro por destinatario)
```

## Diseño

### Cómo las alertas llegan a `inicio.py`
`inicio.py` ya consume alertas del grupo del contexto vía `AlertaService` o
`EstadisticosService`. Necesitamos una consulta adicional que filtre por
`usuario_destino_id = ctx.usuario_id` AND `tipo_alerta = 'seguimiento_requerido'`
AND `resuelta = 0`.

### Método nuevo en `AlertaService` (o en repo directo)
Si `AlertaService` no tiene un método `listar_alertas_para_usuario(usuario_id)`,
añadirlo. Si el repo `IAlertaRepository` no tiene el método, extenderlo.

```python
# En alerta_service.py o en sqlite_alerta_repo.py:
def listar_alertas_por_destinatario(
    self,
    usuario_destino_id: int,
    tipo: TipoAlerta | None = None,
    solo_pendientes: bool = True,
) -> list[Alerta]
```

Query:
```sql
SELECT * FROM alertas
WHERE usuario_destino_id = ?
  AND (tipo_alerta = ? OR ? IS NULL)
  AND (resuelta = 0 OR ? = 0)
ORDER BY fecha_generacion DESC
```

### UI en `inicio.py`
Añadir una sección (tarjeta / panel) "Seguimientos pendientes" visible solo
para `Rol.PROFESOR` cuando `usuario_destino_id` tenga alertas activas:

```
┌─────────────────────────────────────────────┐
│ 🔔 Seguimientos pendientes (N)              │
│ • [Estudiante X] — "Revisar comportamiento"  │
│   [Fecha] · [Nivel]           [Marcar vista] │
│ • [Estudiante Y] — "..."                     │
└─────────────────────────────────────────────┘
```

- `empty_state` cuando no hay seguimientos pendientes (no mostrar la sección).
- Botón "Marcar como atendido" por fila → llama `alerta_service.resolver_alerta(id, usuario_id)`.
- El panel es un refreshable separado que no recarga los demás stats del dashboard.

Para otros roles (director, coordinador), el panel NO aparece en el dashboard
(ellos ven sus propias alertas por el panel existente).

## Tareas

### T1 — Extender `IAlertaRepository` con `listar_alertas_por_destinatario`
Si el método no existe en el puerto, añadirlo. Implementarlo en
`sqlite_alerta_repo.py`.
Verificar: `check_imports --layer infrastructure`

### T2 — `alerta_service.py`: exponer `listar_alertas_para_usuario(usuario_id)`
Wrapper del método del repo.
Verificar: `check_imports --layer services`

### T3 — `inicio.py`: añadir panel "Seguimientos pendientes"
- Solo visible para `Rol.PROFESOR`.
- Refreshable separado `_seguimientos_refreshable`.
- `empty_state` cuando lista vacía (sin mostrar la sección vacía).
- Botón "Marcar como atendido" llama al servicio y refresca.
Verificar: `check_design`, `check_imports --layer interface`

### T4 — Tests
Si existen tests de `inicio.py`, añadir:
- `test_panel_seguimientos_visible_para_profesor` — con alertas de seguimiento → sección aparece.
- `test_panel_seguimientos_oculto_sin_alertas` — sin alertas → sección no aparece.
Si no existen tests de inicio, crear `tests/unit/interface/test_inicio_seguimientos.py` con mocks.

## criterio_done
- [ ] `listar_alertas_por_destinatario` en repo y servicio.
- [ ] Panel "Seguimientos pendientes" en `inicio.py` visible solo para PROFESOR.
- [ ] `empty_state` cuando no hay seguimientos.
- [ ] "Marcar como atendido" funciona y refresca.
- [ ] `check_design` y `check_imports` verdes.
- [ ] Tests verdes.
- [ ] `init.py --quick` → ENTORNO OK.
