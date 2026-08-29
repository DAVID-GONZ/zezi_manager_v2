# tenant_05_desnormalizacion_transitivas — institucion_id directo en tablas transitivas

> **Fase 2A del plan de aislamiento multi-tenant.**
> Agrega `institucion_id` como columna directa en tablas que hoy solo heredan
> el tenant transitivamente (via FK a un padre que si tiene la columna).
> Prerequisito para el filtro automatico del ORM (tenant_06).
>
> **Alineacion con roadmap:** Extiende `backend_04_metadata_schema`.
> Se ejecuta DURANTE la migracion a SQLAlchemy, no antes.

## Principio: desnormalizacion controlada

La redundancia del `institucion_id` en tablas transaccionales es el estandar
para multi-tenant en bases de datos compartidas (shared schema). Beneficios:
- `WHERE institucion_id = ?` sin JOIN → queries mas simples y rapidas.
- El ORM puede inyectar el filtro automaticamente via `with_loader_criteria`.
- Cada tabla se audita independientemente por tenant.

La 3ra forma normal NO aplica aqui: la seguridad prevalece sobre la normalizacion.

## Tablas a desnormalizar

| Tabla | Hoy hereda de | Columna a agregar | Backfill |
|-------|---------------|-------------------|----------|
| `asignaciones` | `grupos.institucion_id` (JOIN) | `institucion_id INT REFERENCES instituciones(id)` | `UPDATE asignaciones SET institucion_id = (SELECT g.institucion_id FROM grupos g WHERE g.id = asignaciones.grupo_id)` |
| `disponibilidad_docente` | `usuarios.institucion_id` (JOIN) | idem | via JOIN a `usuarios` |
| `limites_docente` | `usuarios.institucion_id` (JOIN) | idem | via JOIN a `usuarios` |
| `niveles_desempeno` | `configuracion_anio.institucion_id` | idem | via JOIN a `configuracion_anio` |
| `periodos` | `configuracion_anio.institucion_id` | idem | via JOIN |
| `franjas` | `plantillas_franja.institucion_id` | idem | via JOIN |

### Tablas a evaluar (alto volumen, beneficio marginal)

| Tabla | Decision pendiente |
|-------|--------------------|
| `notas` | Volumen alto. El filtro siempre pasa por `estudiante_id` o `actividad_id` que ya estan scopeados. Evaluar costo/beneficio. |
| `control_diario` | Similar a notas. |
| `observaciones_periodo` | Similar. |

**Regla:** si una tabla se consulta frecuentemente con un `SELECT * FROM tabla WHERE ...` sin JOIN a su padre, merece la columna directa. Si siempre se accede via su FK padre, la redundancia no aporta.

## Tareas

### T1 — Definir TenantMixin en el schema SQLAlchemy  [ ]

Al crear el metadata de SQLAlchemy (`backend_04`), definir:

```python
class TenantMixin:
    """Mixin: toda tabla transaccional lleva institucion_id indexado."""
    @declared_attr
    def institucion_id(cls):
        return Column(
            Integer,
            ForeignKey("instituciones.id"),
            nullable=False,
            index=True,
        )
```

**Aplicar a:** TODAS las tablas que hoy tienen `institucion_id` (20 tablas
del schema actual) + las 6 tablas nuevas de esta spec.

**Verificacion:** `metadata.create_all()` genera schema con la columna en las
26+ tablas.

### T2 — Migracion de datos: backfill de las 6 tablas  [ ]

Script de migracion (o paso en el seed/init):
1. `ALTER TABLE <t> ADD COLUMN institucion_id INTEGER REFERENCES instituciones(id)`
   (si no existe — `PRAGMA table_info` para verificar).
2. `UPDATE <t> SET institucion_id = (SELECT padre.institucion_id FROM <padre> ...)`.
3. Verificar: `SELECT COUNT(*) FROM <t> WHERE institucion_id IS NULL` = 0.

**NOTA:** No agregar `NOT NULL` de golpe sobre BD poblada. Backfill primero,
verificar, y luego en el schema SQLAlchemy definir como `nullable=False`.

**Verificacion:** Todas las filas tienen `institucion_id` no nulo.

### T3 — Actualizar modelos Pydantic de dominio  [ ]

Para cada tabla desnormalizada, agregar `institucion_id: int` (no opcional)
al modelo Pydantic correspondiente:
- `Asignacion` en `src/domain/models/asignacion.py`
- `DisponibilidadDocente`, `LimitesDocente` en `src/domain/models/infraestructura.py`
- `NivelDesempeno` en `src/domain/models/configuracion.py`
- `Periodo` en `src/domain/models/configuracion.py`
- `Franja` en `src/domain/models/infraestructura.py`

**Verificacion:** `python init.py` verde; tests existentes pasan con el campo nuevo.

### T4 — Actualizar repos para usar la columna directa  [ ]

Los repos que hoy hacen JOIN para filtrar por tenant ahora pueden usar
`WHERE institucion_id = ?` directamente:
- `sqlite_asignacion_repo.listar_por_grupo` — eliminar JOIN a grupos.
- `sqlite_infraestructura_repo.listar_limites_docente` — filtro directo.
- `sqlite_infraestructura_repo.listar_ventanas_grupo` — filtro directo.
- etc.

**Verificacion:** Queries simplificadas; tests verdes.

### T5 — Evaluar tablas de alto volumen  [ ]

Para `notas`, `control_diario`, `observaciones_periodo`:
- Medir: cuantas queries las acceden sin JOIN al padre?
- Si > 50% → agregar columna.
- Si < 50% → documentar decision de no desnormalizar y por que.

Documentar decision en este spec (actualizar este archivo).

## Criterio de done
- [ ] TenantMixin definido y aplicado en schema SQLAlchemy
- [ ] 6 tablas transitivas con `institucion_id` directo
- [ ] Backfill completo (0 nulls)
- [ ] Modelos Pydantic actualizados
- [ ] Repos simplificados (sin JOINs innecesarios para tenant)
- [ ] Decision documentada para tablas de alto volumen
- [ ] `python init.py` verde
