# paso_14c_asistencia_conteo — design

## Puerto `IAsistenciaRepository` — métodos nuevos

```python
def contar_clases_dictadas_docente(self, usuario_id: int, anio: int, mes: int) -> int: ...
def clases_dictadas_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]: ...
```

## Repositorio SQLite (`sqlite_asistencia_repo.py`)

`control_diario` tiene `asignacion_id`, `fecha` (ISO `YYYY-MM-DD`). Se une con
`asignaciones` para filtrar por docente.

```sql
-- total (R1, R2, R5)
SELECT COUNT(*) FROM (
    SELECT cd.asignacion_id, cd.fecha
    FROM control_diario cd
    JOIN asignaciones a ON a.id = cd.asignacion_id
    WHERE a.usuario_id = ?
      AND strftime('%Y', cd.fecha) = ?      -- anio con zfill(4)
      AND strftime('%m', cd.fecha) = ?      -- mes con zfill(2)
    GROUP BY cd.asignacion_id, cd.fecha
)
```

```sql
-- desglose (R6)
SELECT cd.asignacion_id, COUNT(DISTINCT cd.fecha) AS n
FROM control_diario cd
JOIN asignaciones a ON a.id = cd.asignacion_id
WHERE a.usuario_id = ?
  AND strftime('%Y', cd.fecha) = ?
  AND strftime('%m', cd.fecha) = ?
GROUP BY cd.asignacion_id
```

El parámetro de mes se formatea `f"{mes:02d}"` y el año `f"{anio:04d}"`.

## Servicio `AsistenciaService` — métodos nuevos

```python
def contar_clases_mes(self, usuario_id: int, anio: int, mes: int) -> int
def clases_mes_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]
```

Delegan en el repo. Sin lógica adicional salvo validar `1 <= mes <= 12`.

## `container.py`

Sin cambios (los métodos viven en `AsistenciaService`, ya registrado).

### Alternativa descartada

**Contar filas de `control_diario` directamente.** Descartada: inflaría el conteo
por número de estudiantes (un día con 30 registros contaría 30). El `GROUP BY
asignacion_id, fecha` modela "una clase = una asignación dictada en una fecha"
(R5).

## Verificación

- `python -m pytest tests/ -q -k clases_dictadas`.
- `python init.py` exit 0.
- Con `seed_dev`: el conteo de un docente coincide con
  `len({(asignacion_id, fecha)})` de sus registros en el mes.
