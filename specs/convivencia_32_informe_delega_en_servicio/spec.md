# convivencia_32_informe_delega_en_servicio — Spec

## Contexto

`InformeService.convivencia_boletin` (líneas 123-145 de
`src/services/informe_service.py`) accede DIRECTAMENTE al repo de
convivencia (`self._convivencia_repo.get_nota(...)` y
`self._convivencia_repo.listar_observaciones_por_estudiante(...)`), saltándose
`ConvivenciaService`. Esto:

1. Viola la política de capas del proyecto (servicio→servicio, no
   servicio→repo ajeno).
2. Repite el conocimiento sobre qué son "observaciones públicas del periodo",
   que ya vive en `ConvivenciaService.listar_observaciones(...)`.
3. Rompe la posibilidad de que `ConvivenciaService` añada lógica (p.ej.
   filtros por preferencias del tenant, expansión de observaciones vinculadas
   a registros) sin que Informes lo herede.

Con `convivencia_28` (anual) y `convivencia_29` (registros) el problema
crece: cada extensión repite lógica en dos lugares. Esta spec centraliza la
composición del "paquete convivencia para boletín" en `ConvivenciaService`.

Scope:
- `src/services/convivencia_service.py` (MODIFICAR — expone métodos de
  composición para boletines).
- `src/services/informe_service.py` (MODIFICAR — delega en el servicio de
  convivencia; elimina la dependencia directa a `_convivencia_repo`).
- `container.py` (MODIFICAR — inyecta `convivencia_service` en
  `InformeService`; retira `convivencia_repo` como dependencia de Informes).
- `tests/unit/services/` (EXTENDER).

## Requisitos (EARS)

- **R1** — `ConvivenciaService` DEBE exponer:
  - `paquete_boletin_periodo(estudiante_id, periodo_id) -> dict` (mismo
    contenido que `InformeService.convivencia_boletin` hoy, extendido por
    `convivencia_29`).
  - `paquete_boletin_anual(estudiante_id, anio_id) -> dict` (idéntico a lo
    definido en `convivencia_28`).
- **R2** — `InformeService.convivencia_boletin` y `convivencia_boletin_anual`
  DEBEN ser thin wrappers que delegan al servicio (o eliminarse y llamar al
  servicio directamente desde los generadores). No mantienen lógica propia.
- **R3** — `InformeService` NO DEBE tener `_convivencia_repo` en su `__init__`
  después de este paso. Sustituido por `_convivencia_svc_provider` (lazy,
  siguiendo el patrón de `catalogo_academico_svc_provider` en
  `ConvivenciaService`) para evitar ciclos de wiring en `Container`.
- **R4** — El wiring en `Container` se actualiza: `informe_service()` recibe
  un provider a `convivencia_service()`; `convivencia_service()` NO recibe
  informe (no hay dependencia inversa).

## Diseño

### 1. Métodos en `ConvivenciaService`

```
def paquete_boletin_periodo(
    self, estudiante_id: int, periodo_id: int
) -> dict:
    """
    Retorna dict con:
      nota:             float | None
      nota_observacion: str   | None
      observaciones_por_categoria: [
          {"categoria": str,
           "items": [{"fecha": str, "autor": str, "texto": str}, ...]},
          ...
      ]
      registros:        list[dict]        (política de convivencia_29)
    """
    nota = self._repo.get_nota(estudiante_id, periodo_id)
    obs  = self._repo.listar_observaciones_por_estudiante(
        estudiante_id, periodo_id, solo_publicas=True
    )
    excluir_ids = {o.registro_comportamiento_id for o in obs
                   if o.registro_comportamiento_id is not None}
    return {
        "nota":             nota.valor if nota else None,
        "nota_observacion": nota.observacion if nota else None,
        "observaciones_por_categoria": self._agrupar_obs_por_categoria(obs),
        "registros":        self._registros_informables_periodo(
                                estudiante_id, periodo_id, excluir_ids),
    }

def paquete_boletin_anual(
    self, estudiante_id: int, anio_id: int
) -> dict:
    """
    Estructura definida en convivencia_28 + 'registros' agregados (convivencia_29).
    'observaciones_por_categoria' aquí usa items con clave 'periodo' (nombre
    del periodo) en vez de 'fecha'. Requiere periodo_svc_provider.
    """
```

`_agrupar_obs_por_categoria(obs)` resuelve el nombre de la categoría vía
`self._repo.listar_categorias(solo_activas=False)` (una consulta), mapea
`categoria_id → nombre`, agrupa y ordena (activas alfabético, inactivas
después, "Sin categoría" al final). El nombre del autor se resuelve vía
`self._usuario_svc_provider` (nuevo, opcional) o queda como `""` si no está
disponible. En periodo, `fecha` es `str(obs.fecha)`; en anual, `periodo` es
`periodo.nombre`.

- `_registros_informables_periodo(...)` implementa la política de
  `convivencia_29` (constante `_TIPOS_INFORMABLES_SIEMPRE`, deduplicación por
  `excluir_ids`, orden por fecha).

### 2. `InformeService` simplificado

```
def __init__(self, estadisticos_repo, exporter=None, estudiante_repo=None,
             convivencia_svc_provider=None):
    ...
    self._convivencia_svc_provider = convivencia_svc_provider

def _conv_svc(self):
    if self._convivencia_svc_provider is None:
        return None
    return self._convivencia_svc_provider()

def convivencia_boletin(self, estudiante_id, periodo_id) -> dict:
    svc = self._conv_svc()
    if svc is None:
        return {"nota": None, "nota_observacion": None,
                "observaciones": [], "registros": []}
    return svc.paquete_boletin_periodo(estudiante_id, periodo_id)

def convivencia_boletin_anual(self, estudiante_id, anio_id) -> dict:
    svc = self._conv_svc()
    if svc is None:
        return {"periodos": [], "notas_por_periodo": {},
                "definitiva": None, "concepto": None,
                "observaciones": [], "registros": []}
    return svc.paquete_boletin_anual(estudiante_id, anio_id)
```

- Retirar `convivencia_repo` del `__init__` y todos sus usos.
- No cambia la firma pública (`generar_boletin_periodo`, `generar_boletin_anual`,
  etc.) — los generadores siguen llamando a `self.convivencia_boletin(...)`.

### 3. `Container`

- `convivencia_service()`: sin cambios (no depende de informe).
- `informe_service()`: se construye con
  `convivencia_svc_provider=Container.convivencia_service` (referencia sin
  invocar, lazy). Retirar el parámetro `convivencia_repo` de la construcción.

### 4. Retrocompatibilidad de tests

Los tests que hoy inyectan `convivencia_repo=FakeConvivenciaRepo(...)` en
`InformeService` DEBEN migrar a inyectar
`convivencia_svc_provider=lambda: ConvivenciaService(FakeConvivenciaRepo(...))`
o un `FakeConvivenciaService` con los dos métodos nuevos. Añadir un helper
en `tests/support/` si evita boilerplate.

## Tareas

- **T1** — Extraer política de `convivencia_29` (`_TIPOS_INFORMABLES_SIEMPRE`,
  `_registros_informables_periodo`) a `ConvivenciaService`. Si aún no está
  implementada, este spec asume la spec 29 previa.
- **T2** — Añadir `paquete_boletin_periodo` y `paquete_boletin_anual` en
  `ConvivenciaService` + tests unitarios (nominal, sin nota, sin obs, con
  deduplicación de registros).
- **T3** — Refactorizar `InformeService`: nuevo parámetro
  `convivencia_svc_provider`; borrar `convivencia_repo`; `convivencia_boletin*`
  delegan.
- **T4** — Actualizar `container.py` (wiring).
- **T5** — Migrar tests de `InformeService` a `FakeConvivenciaService`.
- **T6** — `grep -n "self._convivencia_repo" src/services/informe_service.py`
  → 0 resultados como criterio de done.

## Verificación

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/services/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer services
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

`InformeService.__init__` ya no menciona `convivencia_repo`. Los boletines de
periodo y anual se generan idénticamente. `init.py` verde.

## Dependencias

- `convivencia_28` (anual) y `convivencia_29` (registros) — sin ellos, los
  métodos `paquete_*` sólo mueven la lógica actual. Con ellos, quedan como
  una única fuente de verdad.
