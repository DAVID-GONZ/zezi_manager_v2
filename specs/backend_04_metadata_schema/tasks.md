# Tareas: backend_04_metadata_schema

> SCOPE — archivos que pueden editarse:
> `src/infrastructure/db/schema.py` (reescritura),
> `tests/conftest.py` (adaptar _apply_schema),
> `tests/unit/infrastructure/test_schema_integrity.py` (adaptar tests de esquema),
> `requirements.txt` (añadir sqlalchemy).
>
> Fuera de scope: repositorios, servicios, interfaz, container.py.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**
>
> ⚠️ LEER `docs/auditoria_observabilidad_2026-09-08.md` §5.1 ANTES de empezar.

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

---

## T1 — Añadir sqlalchemy a requirements.txt  [ ]

Añadir `sqlalchemy>=2.0` a `requirements.txt` e instalar:

```
.venv/Scripts/pip.exe install sqlalchemy>=2.0
```

**Verificación:**
```
.venv/Scripts/python.exe -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

---

## T2 — Reescribir el módulo 1: Configuración institucional  [ ]

Crear el `MetaData` y declarar las tablas del módulo 1 (`instituciones`,
`configuracion_anio`, `preferencias_institucion`, `siee_*`).

Conservar temporalmente las listas `SCHEMA`, `INDICES`, `TRIGGERS` al
final del archivo para que el resto del sistema siga funcionando mientras
se migran los demás módulos.

**Verificación parcial:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.infrastructure.db.schema import metadata; print([t.name for t in metadata.sorted_tables[:5]])"
```

---

## T3 — Reescribir módulos 2-4: Infraestructura, Usuarios, Periodos  [ ]

Declarar las tablas de infraestructura académica (`grados`, `grupos`,
`salas`, `jornadas`, etc.), usuarios (`usuarios`, `acudientes`), y
periodos/asignaciones.

**Resolver D2:** decidir si `grupos.sala_id` lleva `ForeignKey("salas.id")`
o se elimina. Reportar la decisión al leader.

**Resolver D1:** el orden en el código fuente no necesita respetar FKs
(SQLAlchemy resuelve automáticamente), pero agrupar por módulo.

---

## T4 — Reescribir módulos 5-7: Evaluación, Cierres, Habilitaciones  [ ]

Incluye las tablas de notas con `Numeric(4, 2)` en lugar de `REAL`.
Incluye plan_mejoramiento.

---

## T5 — Reescribir módulos 8-9: Asistencia, Convivencia, Alertas  [ ]

**Resolver D3:** las tablas con `ON CONFLICT REPLACE` pasan a
`UniqueConstraint` estándar.

**Resolver D10:** el trigger de notas cubre `BEFORE UPDATE`.

---

## T6 — Reescribir módulos 10-11: Informes, Auditoría  [ ]

Incluye `audit_log`, `auditoria`, `verificacion_auditoria`.

---

## T7 — Índices y triggers como objetos SQLAlchemy  [ ]

Declarar todos los índices con `Index(...)`.
Declarar los triggers como `DDL(...)` con `event.listen`.

Eliminar las listas `INDICES` y `TRIGGERS`.

---

## T8 — Resolver D4: CHECK constraints de deuda  [ ]

Añadir los 5 `CheckConstraint` faltantes:
- `AccionCambio`
- `Calendario`
- `CategoriaPreferencia`
- `JornadaPrincipal`
- `TipoInstitucion`

Verificar contra `scripts/check_enums.py` que la alineación es correcta.

---

## T9 — Resolver D5: institucion_id NOT NULL  [ ]

En las tablas de scope que tienen `institucion_id` nullable, cambiarlo
a `nullable=False` donde aplique.

**REPORTAR al leader** la lista de tablas afectadas y las que se dejan
nullable con justificación, antes de aplicar.

---

## T10 — Eliminar las listas DDL antiguas  [ ]

Una vez que todas las tablas están declaradas en el `MetaData`:
1. Eliminar `SCHEMA`, `INDICES`, `TRIGGERS`.
2. Exportar solo `metadata` desde el módulo.

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.infrastructure.db.schema import metadata; print(f'{len(metadata.tables)} tablas')"
```
Debe imprimir `65 tablas` (o el total tras D5/tenant_05).

---

## T11 — Adaptar conftest.py a create_all  [ ]

`_apply_schema` pasa a usar `metadata.create_all()` en lugar de ejecutar
strings DDL. Crear un engine SQLAlchemy sobre la conexión SQLite en memoria.

```python
from sqlalchemy import create_engine
from src.infrastructure.db.schema import metadata

def _apply_schema():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine.connect()
```

Adaptar las fixtures para que devuelvan la conexión del engine.

---

## T12 — Adaptar tests de esquema  [ ]

Los tests de `test_schema_integrity.py` que eran `xfail` por D1 y D2
pasan a ser tests normales (sin `xfail`) — los defectos ya están resueltos.

Los tests que parseaban strings DDL ahora introspeccionan el `MetaData`
directamente (tablas, columnas, FKs, índices).

---

## T13 — Verificar equivalencia  [ ]

Comparar el schema generado por `create_all()` contra el anterior:

1. Crear una BD con el schema antiguo (strings DDL, si se conservaron
   en un archivo de referencia o en git).
2. Crear una BD con `create_all()`.
3. Comparar `sqlite_master` de ambas.

Las diferencias deben ser solo las mejoras (D1-D5, D10).

---

## T14 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. Verificar que la puerta de enums sigue verde.

**Artefacto:** `progress/impl_backend_04.md` con los defectos resueltos
y las decisiones tomadas.
