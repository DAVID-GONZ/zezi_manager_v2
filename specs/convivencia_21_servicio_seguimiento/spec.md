# convivencia_21_servicio_seguimiento — Spec

## Contexto

El hub de Seguimiento (convivencia_25) necesita datos agregados por grupo y la
evolución de la nota de comportamiento por periodos. Hoy las páginas resuelven
esto con un patrón **N+1** (bucle sobre estudiantes llamando
`listar_observaciones` / `listar_alertas` uno por uno). Este paso completa
`ConvivenciaService` con métodos agregados y dos DTOs, para que las páginas pidan
un solo resultado ya compuesto.

Fuente de verdad: `src/domain/models/convivencia.py`, `src/services/convivencia_service.py`,
`src/domain/ports/convivencia_repo.py`.

## Requisitos (EARS)

- **R1** — El sistema DEBE exponer la evolución de la nota de comportamiento de un
  estudiante a lo largo de los periodos del año como una serie ordenada, con un
  punto por periodo y `valor=None` donde no hay nota registrada.
- **R2** — El sistema DEBE exponer, por grupo y periodo, un resumen por estudiante
  con: número de observaciones, número de registros negativos, nota de
  comportamiento, nivel de desempeño y si supera el umbral de alerta configurado.
- **R3** — El resumen (R2) DEBE calcularse con un número acotado de consultas
  (sin una consulta por estudiante).
- **R4** *(opcional)* — `vista_360` DEBERÍA poblar `promedio_notas` con el promedio
  académico si hay un servicio de notas disponible; si no, permanece `None`. Puede
  diferirse si complica el paso (cruza a evaluación).

## Diseño

### DTOs nuevos (`src/domain/models/convivencia.py`, añadir a `__all__`)

```python
class PuntoSerieDTO(BaseModel):
    periodo_id:     int
    periodo_nombre: str
    valor:          float | None = None

class ResumenConvivenciaDTO(BaseModel):
    estudiante_id:            int
    nombre:                   str
    num_observaciones:        int         = 0
    num_registros_negativos:  int         = 0
    nota:                     float | None = None
    nivel_nombre:             str | None  = None
    supera_umbral:            bool        = False
```

### Puerto + repo — nuevo método batch (evita N+1 de observaciones)

`src/domain/ports/convivencia_repo.py` (nuevo abstractmethod) +
`src/infrastructure/db/repositories/sqlite_convivencia_repo.py` (implementación):

```python
def listar_observaciones_por_grupo(
    self, grupo_id: int, periodo_id: int | None = None, solo_publicas: bool = False
) -> list[ObservacionPeriodo]: ...
```

SQL: `observaciones` JOIN `asignaciones` (por `asignacion_id`) filtrando por
`grupo_id` del join y `periodo_id` opcional; respeta `solo_publicas`.

> No se añade `listar_alertas_por_grupo`: en el maestro-detalle el badge de alerta
> sale de `supera_umbral` (contadores), y las alertas-entidad se muestran solo en
> el detalle de UN estudiante (consulta single ya existente en `AlertaService`).

### Métodos de servicio (`ConvivenciaService`)

**`serie_notas_comportamiento(estudiante_id, anio_id) -> list[PuntoSerieDTO]`**
- Requiere `periodo_svc_provider` (si es None → `RuntimeError`, como los demás).
- `periodos = periodo_svc.listar_por_anio(anio_id)`.
- `notas = {n.periodo_id: n for n in self._repo.listar_notas_por_estudiante(estudiante_id)}`.
- Un `PuntoSerieDTO` por periodo (en orden), `valor = notas[pid].valor if pid in notas else None`.

**`resumen_convivencia_grupo(grupo_id, periodo_id) -> list[ResumenConvivenciaDTO]`**
- `conceptos = self.listar_conceptos_grupo(grupo_id, periodo_id)` → nota + nivel por estudiante (ya cubre estudiantes sin nota).
- `estudiantes = self._estudiante_svc_provider().listar_por_grupo(grupo_id)` → nombres.
- `registros = self._repo.listar_registros(FiltroConvivenciaDTO(grupo_id=grupo_id, periodo_id=periodo_id))` → contar `reg.es_negativo` por estudiante (1 consulta).
- `obs = self._repo.listar_observaciones_por_grupo(grupo_id, periodo_id)` → contar por estudiante (1 consulta).
- Umbral: `anio_id = periodo_svc.get_by_id(periodo_id).anio_id`; si `alerta_repo` y
  `cfg = alerta_repo.get_configuracion(anio_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)`
  activa → `supera_umbral = num_registros_negativos >= cfg.umbral`; si no, `False`.
- Combina por estudiante en `ResumenConvivenciaDTO`.

**Reutiliza:** `listar_conceptos_grupo`, `listar_registros`, `_repo.listar_notas_por_estudiante`,
`estudiante_svc_provider`, `periodo_svc_provider`, `alerta_repo`. Todos ya inyectados en `container.py`.

### Alternativa descartada
Añadir `contar_observaciones_por_grupo` / `contar_registros_por_grupo` en el repo
(agregación SQL). Descartada: el volumen por grupo/periodo es pequeño; contar en
Python sobre una lista ya traída evita duplicar lógica de filtrado en el repo.

## Tareas

- **T1** — DTOs `PuntoSerieDTO` y `ResumenConvivenciaDTO` en `convivencia.py` (+ `__all__`).
  Verif: `python -m pytest tests/unit/domain/ -q`.
- **T2** — `listar_observaciones_por_grupo` en el puerto `IConvivenciaRepository`.
- **T3** — Implementación SQLite del método en `sqlite_convivencia_repo.py`.
  Verif: `python -m pytest tests/integration/ -q -k convivencia` (o el test de repos existente).
- **T4** — `serie_notas_comportamiento` en `ConvivenciaService`.
- **T5** — `resumen_convivencia_grupo` en `ConvivenciaService`.
- **T6** — Tests unitarios con FakeRepository (extender el fake con el nuevo método):
  nominal; estudiante sin nota (valor None en la serie y nota None en resumen);
  grupo vacío; sin `alerta_repo` (supera_umbral siempre False).
  Verif: `python -m pytest tests/unit/services/ -q`.

## Verificación final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer domain
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer infrastructure
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```
`init.py` verde; pytest sin regresiones; los 5 métodos/DTOs disponibles vía servicio.
