# Diseño: Aislamiento multi-tenant en datos (mejora_02_multitenant_datos)

> **Gate de decisión:** implementar solo si multi-tenant real es objetivo (ver
> requirements.md). Este design asume que sí.

## 1. Alcance del cambio (grande — tocar schema)

A diferencia de `mejora_01`, este spec **sí toca `schema.py`** (DDL) y los repos.
Es la razón por la que se dejó "fuera de alcance" en paso_24. Superficie:

- **Schema:** añadir columna `institucion_id INTEGER REFERENCES instituciones(id)`
  a las tablas académicas raíz. Candidatas (a confirmar en T1 con el schema real):
  `configuracion_anio` / años, `grupos`, `estudiantes`, `asignaciones`,
  `usuarios` (ya lo tiene el modelo). Las tablas hijas heredan el tenant por su FK
  al padre (no necesitan la columna si su raíz ya la lleva) — decidir por tabla.
- **Migración de datos:** backfill de todos los registros existentes a la
  institución #1.
- **Repos:** los métodos de listado y de get-by-id de las tablas afectadas aceptan
  `institucion_id` por parámetro y lo aplican en el `WHERE`.
- **Servicios:** resuelven el scope con `contexto_tenant.institucion_actual()` y lo
  pasan al repo (patrón ya establecido, ver `docs/conventions.md` §11); en las
  operaciones por id, llaman `verificar_pertenencia(obj.institucion_id)`.

## 2. Estrategia de migración de schema

`schema.py` es idempotente (crea si no existe). Para columnas nuevas en una BD ya
poblada se requiere un paso de migración explícito:

1. `ALTER TABLE <t> ADD COLUMN institucion_id INTEGER` (si no existe) — guardar en
   una función de migración versionada.
2. `UPDATE <t> SET institucion_id = 1 WHERE institucion_id IS NULL` (backfill R5).
3. A partir de aquí, los INSERT incluyen `institucion_id`.

No se añade `NOT NULL` de golpe sobre BD poblada; se backfilla primero y se valida
en la capa de servicio.

## 3. Patrón en repos (ejemplo)

```python
# Listado tenant-aware
def listar_grupos(self, institucion_id: int | None = None) -> list[Grupo]:
    if institucion_id is None:
        df = fetch_df("SELECT * FROM grupos")
    else:
        df = fetch_df("SELECT * FROM grupos WHERE institucion_id = ?", (institucion_id,))
    return [Grupo(**r) for r in df.to_dict("records")]
```

`institucion_id=None` ⇒ admin cross-tenant (sin filtro), coherente con la regla
existente.

## 4. Patrón en servicios (ejemplo)

```python
from src.services.contexto_tenant import institucion_actual, verificar_pertenencia

def listar_grupos(self):
    return self._repo.listar_grupos(institucion_id=institucion_actual())

def get_grupo(self, grupo_id: int) -> Grupo:
    g = self._repo.get_grupo(grupo_id)          # lee sin filtro por id
    verificar_pertenencia(g.institucion_id)     # cierra la dimensión por-id (R3)
    return g
```

## 5. Alternativa descartada

Se consideró **filtrar por institución solo en la UI** (sin columna en datos). Se
descartó porque no es aislamiento real: un id forjado o una consulta cruzada
saltaría el filtro. El aislamiento debe vivir en los datos + servicios (defensa en
profundidad).

## 6. Manejo de errores

`verificar_pertenencia` lanza `OperacionFueraDeInstitucionError` (subclase de
`PermissionError`). La capa de interfaz la captura como acceso denegado (toast +
navegación), igual que los demás `PermissionError`.

## Nota de implementación (riesgo conocido)

Alto riesgo de regresión: muchas queries y tests asumen un espacio de datos único.
Mitigación: migrar **una tabla raíz a la vez** (grupos → estudiantes → …), con
tests de aislamiento entre dos instituciones por cada una, y la suite verde antes
de la siguiente. El backfill a la institución #1 mantiene el comportamiento actual
para el tenant existente.
