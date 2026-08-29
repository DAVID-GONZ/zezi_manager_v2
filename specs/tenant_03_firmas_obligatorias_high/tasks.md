# tenant_03_firmas_obligatorias_high — Migrar 28 metodos HIGH a TenantScope obligatorio

> **Fase 1B (continuacion) del plan de aislamiento multi-tenant.**
> Tras cerrar los 10 criticos (tenant_02), migrar los 28 metodos que hoy tienen
> `institucion_id: int | None = None` — un default silencioso que causa fuga
> si el caller olvida pasar el scope.

## Principio

Misma mecanica que tenant_02: cambiar `institucion_id: int | None = None`
a `institucion_id: TenantScope` (obligatorio, sin default). Los servicios
resuelven el scope con `institucion_actual() or "*"` (donde `"*"` = admin
cross-tenant).

El patron `_aplicar_scope(filtro)` en los servicios ya existe
(`usuario_service.py:495`). Solo hay que hacer que retorne `"*"` en vez de
dejar `None` cuando `institucion_actual()` es None (admin).

## Scope

Puertos, repos y servicios de los siguientes modulos:

| Modulo | Metodos a migrar | Puerto | Repo |
| -------- | ----------------- | -------- | ------ |
| usuario | `listar_filtrado`, `listar_resumenes`, `listar_docentes_info`, `get_docente_info` | `usuario_repo.py` | `sqlite_usuario_repo.py` |
| estudiante | `get_by_documento`, `existe_documento`, `listar_filtrado`, `listar_resumenes`, `listar_por_grupo`, `contar_por_grupo` | `estudiante_repo.py` | `sqlite_estudiante_repo.py` |
| asignacion | `listar` (DTO), `listar_info` (DTO), `listar_por_grupo`, `listar_por_docente` | `asignacion_repo.py` | `sqlite_asignacion_repo.py` |
| configuracion | `get_activa`, `get_by_anio`, `listar` | `configuracion_repo.py` | `sqlite_configuracion_repo.py` |
| acudiente | `listar`, `buscar_por_documento` | `acudiente_repo.py` | `sqlite_acudiente_repo.py` |
| convivencia | `listar_registros`, `contar_registros`, `listar_categorias`, `listar_plantillas`, `listar_tipos_situacion`, `listar_medidas` | `convivencia_repo.py` | `sqlite_convivencia_repo.py` |
| infraestructura | `listar_areas`, `listar_asignaturas`, `listar_grupos`, `listar_plantillas_franja`, `get_plantilla_activa`, `listar_salas`, `listar_franjas_reunion`, `listar_plan_estudios`, `get_plan_estudios_por_grado` | `infraestructura_repo.py` | `sqlite_infraestructura_repo.py` |

## Tareas

### T1 — Actualizar _aplicar_scope en servicios  [ ]

En todos los servicios que usan el patron `_aplicar_scope`:

- Cuando `institucion_actual()` retorna None (admin), setear `"*"` en el filtro
  en vez de dejar None.
- Esto hace que los repos reciban siempre un `TenantScope` valido.

Servicios a tocar:

- `usuario_service.py` — `_aplicar_scope` y `_resolver_institucion`
- `estudiante_service.py` — equivalente
- `catalogo_academico_service.py` — si existe _aplicar_scope
- `convivencia_service.py` — equivalente
- `configuracion_service.py` — equivalente
- Cualquier otro servicio que lea `institucion_actual()` para pasarlo a repos.

**Patron:**

```python
@staticmethod
def _aplicar_scope(filtro: FiltroDTO) -> FiltroDTO:
    if filtro.institucion_id is not None:
        return filtro
    scope: TenantScope = institucion_actual() or "*"
    return filtro.model_copy(update={"institucion_id": scope})
```

**Verificacion:** `python init.py` verde tras cada servicio modificado.

### T2 — Migrar puertos del modulo usuario  [ ]

En `src/domain/ports/usuario_repo.py`:

- `listar_filtrado`: verificar que `FiltroUsuariosDTO.institucion_id` sea
  `TenantScope` (no `int | None`).
- `listar_resumenes`: idem.
- `listar_docentes_info`: cambiar `institucion_id: int | None = None`
  → `institucion_id: TenantScope`.
- `get_docente_info`: idem.

Repo `sqlite_usuario_repo.py`: implementar rama `"*"` (sin WHERE) / int (con WHERE).

**Verificacion:** `python init.py` verde; tests de usuario pasan.

### T3 — Migrar puertos del modulo estudiante  [ ]

En `src/domain/ports/estudiante_repo.py`:

- 6 metodos: cambiar firma a `TenantScope`.
- Para `FiltroEstudiantesDTO.institucion_id`: cambiar tipo.

Repo `sqlite_estudiante_repo.py`: implementar ramas.

**Verificacion:** `python init.py` verde.

### T4 — Migrar puertos del modulo asignacion  [ ]

En `src/domain/ports/asignacion_repo.py`:

- `FiltroAsignacionesDTO.institucion_id`: cambiar tipo.
- `listar_por_grupo`: agregar `institucion_id: TenantScope`.
- `listar_por_docente`: agregar `institucion_id: TenantScope`.

Repo `sqlite_asignacion_repo.py`: implementar. NOTA: `asignaciones` no tiene
`institucion_id` directo — filtrar via JOIN a `grupos.institucion_id`.

**Verificacion:** `python init.py` verde.

### T5 — Migrar puertos del modulo configuracion  [ ]

En `src/domain/ports/configuracion_repo.py`:

- `get_activa`: `institucion_id: TenantScope` (CRITICO: sin esto, un director
  puede obtener la config de otro tenant).
- `get_by_anio`: idem.
- `listar`: idem.

Repo `sqlite_configuracion_repo.py`: implementar.

**Verificacion:** `python init.py` verde.

### T6 — Migrar puertos del modulo acudiente  [ ]

En `src/domain/ports/acudiente_repo.py`:

- `listar`: `institucion_id: TenantScope`.
- `buscar_por_documento`: `institucion_id: TenantScope`.

Repo `sqlite_acudiente_repo.py`: implementar.

**Verificacion:** `python init.py` verde.

### T7 — Migrar puertos del modulo convivencia  [ ]

En `src/domain/ports/convivencia_repo.py`:

- 6 metodos: cambiar firma a `TenantScope`.

Repo `sqlite_convivencia_repo.py`: implementar.

**Verificacion:** `python init.py` verde.

### T8 — Migrar puertos del modulo infraestructura (9 metodos)  [ ]

En `src/domain/ports/infraestructura_repo.py`:

- 9 metodos: cambiar `int | None = None` → `TenantScope`.

Repo `sqlite_infraestructura_repo.py`: implementar ramas `"*"` / int.

**Verificacion:** `python init.py` verde.

### T9 — Test estructural: cero defaults None en repos  [ ]

Ampliar el test de `tenant_02/T7`:

- Escanear TODOS los puertos en `src/domain/ports/`.
- Para cada metodo que tenga parametro `institucion_id`, verificar que
  NO tiene default (o que el default es `Field(...)` en DTOs).
- El test debe fallar si alguien agrega `institucion_id: int | None = None`
  en cualquier puerto.

**Verificacion:**

```
python -m pytest tests/unit/domain/test_tenant_scope.py -v
```

## Criterio de done

- [ ] 28 metodos HIGH migrados (puertos + repos)
- [ ] Todos los `_aplicar_scope` retornan `"*"` para admin
- [ ] Test estructural cubre TODOS los puertos
- [ ] `python init.py` completamente verde
- [ ] Admin cross-tenant sigue funcionando
