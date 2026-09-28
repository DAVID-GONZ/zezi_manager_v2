# rebrand_02_loggers_internos — Diseno

## Categorias de cambio

### C1 — Loggers (2 archivos, 2 definiciones + 4 docstrings)

| Archivo | Cambio |
|---|---|
| `src/infrastructure/logging/security_logger.py:19,101,118` | `zeci.security` -> `avedra.security` en docstring, `getLogger()` y docstring de clase |
| `src/domain/policies/alerta_ip.py:7,15,32,65` | `zeci.security` -> `avedra.security` en 2 docstrings y `getLogger()` |

### C2 — ContextVars (3 archivos, 1 linea cada uno)

| Archivo | Linea | Antes | Despues |
|---|---|---|---|
| `src/infrastructure/context/solo_lectura.py` | 40 | `"zeci_solo_lectura"` | `"avedra_solo_lectura"` |
| `src/infrastructure/context/contexto_tenant.py` | 46 | `"zeci_institucion_actual"` | `"avedra_institucion_actual"` |
| `src/infrastructure/context/contexto_actor.py` | 47 | `"zeci_actor_actual"` | `"avedra_actor_actual"` |

Los nombres de ContextVar son strings internos de depuracion, no
identificadores de Python. No afectan logica.

### C3 — Clases base (2 archivos, renombrado estructural)

| Archivo | Cambio |
|---|---|
| `src/domain/models/base.py` | `ZeciModel` -> `AvedraModel` (clase, docstring, `__all__`). `EntidadDominio(ZeciModel)` -> `EntidadDominio(AvedraModel)`. `DTODominio(ZeciModel)` -> `DTODominio(AvedraModel)`. |
| `src/domain/exceptions.py` | `ZeciError` -> `AvedraError` (clase, docstring). 5 subclases: `ReglaDeNegocioError(ZeciError, ...)` -> `ReglaDeNegocioError(AvedraError, ...)`. `DependenciaNoDisponibleError(ZeciError, ...)` -> idem. |

**Impacto de las clases:**
- `ZeciModel` se importa directamente solo en `base.py` y
  `tests/unit/domain/test_model_config.py`. Los modelos heredan de
  `EntidadDominio` o `DTODominio`, no de `ZeciModel` directo.
- `ZeciError` se importa directamente en `tests/unit/domain/test_exceptions.py`.
  Los servicios importan las subclases por nombre
  (`NoEncontradoError`, `ConflictoError`, etc.), no `ZeciError`.
- Los tests se ajustan en Paso 4.

### C4 — Docstrings de modulo (~35 archivos)

Patron: `"""... ZECI Manager v2.0."""` -> `"""... AVEDRA v2.0."""`

Archivos afectados:
- `src/domain/models/`: base.py, dtos.py, nivelacion.py, clock.py
- `src/domain/exceptions.py`
- `src/infrastructure/db/`: schema.py, seed.py (solo docstring, no data),
  queries.py, connection.py
- `src/infrastructure/db/repositories/`: base.py, sqla_acudiente_repo.py,
  sqla_alerta_repo.py, sqla_asignacion_repo.py, sqla_asistencia_repo.py,
  sqla_cierre_repo.py, sqla_configuracion_repo.py, sqla_estadisticos_repo.py,
  sqla_estudiante_repo.py, sqla_habilitacion_repo.py, sqla_institucion_repo.py,
  sqla_nivelacion_repo.py, sqla_periodo_repo.py, sqla_plan_mejoramiento_repo.py,
  sqla_preferencias_repo.py, sqla_siee_repo.py, sqla_usuario_repo.py
- `src/interface/pages/academico/`: horarios_hub.py, estudiantes.py,
  registro_asistencia.py
- `src/interface/pages/convivencia/`: categorias.py, comportamiento.py,
  configuracion_convivencia.py, notas_convivencia.py, observaciones.py,
  plantillas.py, seguimiento.py

## Riesgo

- **ContextVars:** nulo, los nombres son strings de depuracion.
- **Loggers:** bajo, cambiar el nombre del logger no afecta comportamiento
  si los tests usan el mismo nombre. Tests se ajustan en Paso 4.
- **Clases:** medio. `ZeciModel` y `ZeciError` son importados en tests.
  Los tests QUEBRARAN hasta que Paso 4 los actualice. Alternativa: hacer
  Paso 2 y Paso 4 atomicamente. Recomendacion: ejecutar Paso 4
  inmediatamente despues de Paso 2 en el mismo commit.
