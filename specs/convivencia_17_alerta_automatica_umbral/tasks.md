# convivencia_17_alerta_automatica_umbral — Tasks
> Sin cambios de BD. Prerequisito: convivencia_15 DONE.

## Objetivo
Reemplazar el hack `PLAN_MEJORAMIENTO_VENCIDO` en `_verificar_alerta_comportamiento`
por el tipo semánticamente correcto `SEGUIMIENTO_REQUERIDO`. El umbral sigue
siendo configurable a través de `configuracion_alertas`. No se duplican alertas
pendientes.

## Scope
```
src/services/convivencia_service.py
tests/unit/services/test_convivencia_service.py
```

## Diseño

### El hack actual
`_verificar_alerta_comportamiento` usa `TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO`
como proxy porque no existía `SEGUIMIENTO_REQUERIDO`. Ahora que el enum y el
schema lo soportan (convivencia_15), el reemplazo es directo.

### Cambios en `_verificar_alerta_comportamiento`
Reemplazar las 3 referencias a `TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO` por
`TipoAlerta.SEGUIMIENTO_REQUERIDO`:
1. `get_configuracion(anio_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)`.
2. `existe_pendiente(estudiante_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)`.
3. `alerta = Alerta(tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO, ...)`.

La descripción de la alerta cambia a:
```python
f"El estudiante tiene {conteo} registro(s) negativo(s) de comportamiento "
f"(umbral: {int(cfg.umbral)}). Se recomienda seguimiento."
```

### `usuario_destino_id` en la alerta automática
Las alertas automáticas NO tienen `usuario_destino_id` (son de visibilidad
general, no dirigidas a un profesor específico). `usuario_destino_id=None`.

### Eliminar el comentario "hack"
El docstring de `_verificar_alerta_comportamiento` y el comentario interno
`# HACK: tipo incorrecto` deben eliminarse.

## Tareas

### T1 — `convivencia_service.py`: sustituir las 3 referencias al tipo incorrecto
1. `get_configuracion(anio_id, TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO)` →
   `get_configuracion(anio_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)`.
2. `existe_pendiente(estudiante_id, TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO)` →
   `existe_pendiente(estudiante_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)`.
3. `tipo_alerta=TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO` →
   `tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO`.
4. Actualizar descripción de la alerta.
5. Eliminar comentarios de hack.

**Verificación**:
```
.venv/Scripts/python.exe -c "
import ast
with open('src/services/convivencia_service.py', encoding='utf-8') as f:
    src = f.read()
assert 'PLAN_MEJORAMIENTO_VENCIDO' not in src, 'hack aun presente'
assert 'SEGUIMIENTO_REQUERIDO' in src
print('OK')
"
```

### T2 — Tests
`tests/unit/services/test_convivencia_service.py`:
- `test_verificar_alerta_usa_tipo_seguimiento` — FakeAlertaRepo captura el tipo
  de alerta guardada y verifica que es `TipoAlerta.SEGUIMIENTO_REQUERIDO`.
- `test_verificar_alerta_no_duplica_pendiente` — si `existe_pendiente` retorna
  True, `guardar_alerta` no es llamado.
- `test_verificar_alerta_nivel_critico_doble_umbral` — si `conteo >= umbral * 2`,
  el nivel es `NivelAlerta.CRITICA`.

## criterio_done
- [ ] `PLAN_MEJORAMIENTO_VENCIDO` no aparece en `convivencia_service.py`.
- [ ] `SEGUIMIENTO_REQUERIDO` usado en las 3 referencias.
- [ ] Descripción de alerta actualizada.
- [ ] 3 tests unitarios verdes.
- [ ] `init.py --quick` → ENTORNO OK.
