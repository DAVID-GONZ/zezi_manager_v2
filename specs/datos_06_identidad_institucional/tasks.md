# Tareas: datos_06_identidad_institucional

> Orden de menor a mayor dependencia: modelos → repositorios → servicios → tests.
> Cada tarea produce exactamente un artefacto. No avanzar a la siguiente sin que
> el comando de verificación de la actual esté verde.

---

## T1 — Limpiar `InformacionInstitucionalDTO` en `configuracion.py`

**Archivo**: `src/domain/models/configuracion.py`

**Cambios**:
- Cambiar `dane_code: str` → `dane_code: str | None = None` en
  `InformacionInstitucionalDTO` (permite el caso sin institución de R5).
- Eliminar el método de clase `desde_configuracion` (lector de identidad desde
  `ConfiguracionAnio`).
- En `desde_institucion`: sin cambios de lógica; agregar `nota_minima_aprobacion`
  como `NotaDecimal` en lugar de `float` para consistencia de tipos (opcional si
  ya lo acepta vía coerción Pydantic).

**Artefacto**: `src/domain/models/configuracion.py` (modificado).

**Verificación**:
```
python -c "from src.domain.models.configuracion import InformacionInstitucionalDTO; print('ok')"
```

---

## T2 — Eliminar campos de identidad de `ConfiguracionAnio`

**Archivo**: `src/domain/models/configuracion.py`

**Cambios** (sobre el resultado de T1):
- Eliminar de `ConfiguracionAnio` los 9 campos:
  `nombre_institucion`, `dane_code`, `rector`, `direccion`, `municipio`,
  `telefono_institucion`, `logo_path`, `logo_url`, `resolucion_aprobacion`.
- Eliminar los validadores que solo cubren esos campos:
  `validar_nombre_institucion` y `limpiar_campo_opcional`.
- Eliminar el `@computed_field` `tiene_informacion_institucional`.
- Eliminar el campo `nombre_institucion` de `NuevaConfiguracionAnioDTO`
  y su validador `validar_nombre` asociado.
- En `ActualizarInfoInstitucionalDTO`:
  - Eliminar el método `aplicar_a(config: ConfiguracionAnio)`.
  - Añadir el método:
    ```python
    def to_actualizar_institucion_dto(self) -> "ActualizarInstitucionDTO":
        from src.domain.models.institucion import ActualizarInstitucionDTO
        return ActualizarInstitucionDTO(
            nombre_oficial=self.nombre_institucion,
            codigo_dane=self.dane_code,
            rector=self.rector,
            direccion=self.direccion,
            municipio=self.municipio,
            telefono=self.telefono_institucion,
            logo_path=self.logo_path,
            resolucion_aprobacion=self.resolucion_aprobacion,
        )
    ```

**Artefacto**: `src/domain/models/configuracion.py` (modificado, completado).

**Verificación**:
```
python -c "
from src.domain.models.configuracion import (
    ConfiguracionAnio, NuevaConfiguracionAnioDTO, ActualizarInfoInstitucionalDTO
)
c = ConfiguracionAnio(anio=2025)
assert not hasattr(c, 'dane_code'), 'dane_code sigue en el modelo'
assert not hasattr(c, 'logo_url'), 'logo_url sigue en el modelo'
dto = ActualizarInfoInstitucionalDTO(dane_code='123456789012')
inst_dto = dto.to_actualizar_institucion_dto()
assert inst_dto.codigo_dane == '123456789012'
print('ok')
"
```

---

## T3 — Fijar `SELECT` explícito en `SqliteConfiguracionRepository`

**Archivo**: `src/infrastructure/db/repositories/sqlite_configuracion_repo.py`

**Cambios**:
- Definir al inicio del módulo:
  ```python
  _COLS_ACADEMICOS = (
      "id, anio, institucion_id, fecha_inicio_clases, fecha_fin_clases, "
      "nota_minima_aprobacion, nota_minima_escala, nota_maxima_escala, activo"
  )
  ```
- Reemplazar `SELECT *` por `SELECT {_COLS_ACADEMICOS}` en `get_activa`,
  `get_by_id`, `get_by_anio` y `listar`.
- En `guardar`: eliminar del INSERT los 9 campos de identidad
  (`nombre_institucion`, `dane_code`, `rector`, `direccion`, `municipio`,
  `telefono_institucion`, `logo_path`, `resolucion_aprobacion`) y sus
  correspondientes posiciones en la tupla de valores. `logo_url` no estaba en
  el INSERT previo, nada que hacer ahí.
- En `actualizar`: ídem, eliminar los 9 campos del SET.

**Artefacto**: `src/infrastructure/db/repositories/sqlite_configuracion_repo.py` (modificado).

**Verificación** (requiere BD de desarrollo existente):
```
python -c "
from src.infrastructure.db.repositories.sqlite_configuracion_repo import SqliteConfiguracionRepository
repo = SqliteConfiguracionRepository()
configs = repo.listar('*')
for c in configs:
    assert not hasattr(c, 'dane_code'), 'dane_code cargada desde BD'
print(f'ok: {len(configs)} configuraciones leidas sin campos de identidad')
"
```

---

## T4 — Redirigir `actualizar_info_institucional` en `ConfiguracionService`

**Archivo**: `src/services/configuracion_service.py`

**Cambios**:
- Reescribir `actualizar_info_institucional`:
  ```python
  @requiere_escritura
  def actualizar_info_institucional(
      self,
      anio_id: int,
      dto: ActualizarInfoInstitucionalDTO,
  ) -> ConfiguracionAnio:
      config = self.get_by_id(anio_id)
      if config.institucion_id is None:
          raise ReglaDeNegocioError(
              "El año lectivo no tiene institución asociada. "
              "Asigne una institución antes de actualizar la identidad institucional."
          )
      from container import Container
      inst_dto = dto.to_actualizar_institucion_dto()
      Container.institucion_service().actualizar(config.institucion_id, inst_dto)
      return config
  ```
- En `crear_anio`: eliminar el bloque etiquetado "Auto-snapshot (mejora_06)"
  (las líneas desde el `try` que llama a `Container.institucion_service().snapshot_institucional`
  hasta el `except Exception: pass  # best-effort`).

**Artefacto**: `src/services/configuracion_service.py` (modificado).

**Verificación** (test unitario rápido en memoria):
```
python -c "
from unittest.mock import MagicMock
from src.domain.models.configuracion import ActualizarInfoInstitucionalDTO, ConfiguracionAnio
from src.domain.exceptions import ReglaDeNegocioError
from src.services.configuracion_service import ConfiguracionService

repo = MagicMock()
svc = ConfiguracionService(repo)

# R8: sin institucion_id debe lanzar
config_sin_inst = ConfiguracionAnio(id=1, anio=2025, institucion_id=None)
repo.get_by_id.return_value = config_sin_inst
try:
    svc.actualizar_info_institucional(1, ActualizarInfoInstitucionalDTO())
    assert False, 'debia lanzar'
except ReglaDeNegocioError:
    pass
print('ok R8')
"
```

---

## T5 — Redirigir `get_info_institucional` en `ConfiguracionService`

**Archivo**: `src/services/configuracion_service.py`

**Cambios** (sobre el resultado de T4):
- Reescribir `get_info_institucional`:
  ```python
  def get_info_institucional(self, anio_id: int) -> InformacionInstitucionalDTO:
      config = self.get_by_id(anio_id)
      if config.institucion_id is None:
          # R5: sin institución, retorna defaults sin fallar
          return InformacionInstitucionalDTO(
              anio=config.anio,
              nombre_institucion="Institución Educativa",
              dane_code=None,
              rector=None,
              nota_minima_aprobacion=config.nota_minima_aprobacion,
          )
      from container import Container
      inst = Container.institucion_service().get(config.institucion_id)
      return InformacionInstitucionalDTO.desde_institucion(
          inst, config.anio, config.nota_minima_aprobacion
      )
  ```

**Artefacto**: `src/services/configuracion_service.py` (modificado, completado).

**Verificación**:
```
python -c "
from unittest.mock import MagicMock, patch
from src.domain.models.configuracion import ConfiguracionAnio, InformacionInstitucionalDTO
from src.services.configuracion_service import ConfiguracionService

repo = MagicMock()
svc = ConfiguracionService(repo)

# R5: sin institucion retorna defaults
config_sin_inst = ConfiguracionAnio(id=1, anio=2025, institucion_id=None)
repo.get_by_id.return_value = config_sin_inst
with patch('src.services.contexto_tenant.verificar_pertenencia'):
    info = svc.get_info_institucional(1)
assert info.nombre_institucion == 'Institución Educativa'
assert info.dane_code is None
print('ok R5')
"
```

---

## T6 — Añadir `get_informacion_institucional` a `InformeService`

**Archivo**: `src/services/informe_service.py`

**Cambios**:
- Añadir al `__init__` el parámetro:
  ```python
  config_svc_provider: Callable[[], "ConfiguracionService"] | None = None,
  ```
  y guardar como `self._config_svc_provider = config_svc_provider`.
- Añadir el método público:
  ```python
  def get_informacion_institucional(self, anio_id: int) -> "InformacionInstitucionalDTO":
      """
      Punto de acceso único a la información institucional para
      boletines e informes (R16).
      Lanza DependenciaNoDisponibleError si no hay config_svc_provider.
      Lanza ReglaDeNegocioError/ValueError si faltan DANE o rector (R15).
      """
      if self._config_svc_provider is None:
          raise DependenciaNoDisponibleError(
              "No hay un ConfiguracionService configurado. "
              "Proporcione config_svc_provider al construir InformeService.",
              codigo=CodigoError.EXPORTADOR_NO_DISPONIBLE,
          )
      from src.domain.models.configuracion import InformacionInstitucionalDTO
      svc = self._config_svc_provider()
      return svc.get_info_institucional(anio_id)
  ```
- Actualizar `__all__` si es necesario (no expone el método directamente, solo la clase).

**Artefacto**: `src/services/informe_service.py` (modificado).

**Verificación**:
```
python -c "
from unittest.mock import MagicMock
from src.services.informe_service import InformeService
from src.domain.exceptions import DependenciaNoDisponibleError

svc = InformeService(estadisticos_repo=MagicMock(), config_svc_provider=None)
try:
    svc.get_informacion_institucional(1)
    assert False, 'debia lanzar'
except DependenciaNoDisponibleError:
    pass
print('ok: lanza sin provider')
"
```

---

## T7 — Eliminar `snapshot_institucional` de `InstitucionService`

**Archivo**: `src/services/institucion_service.py`

**Cambios**:
- Eliminar el método `snapshot_institucional` (era el mecanismo de duplicación
  que viola R12).
- Eliminar de `__all__` la exportación si está listada (no lo está actualmente).

**Artefacto**: `src/services/institucion_service.py` (modificado).

**Verificación**:
```
python -c "
from src.services.institucion_service import InstitucionService
assert not hasattr(InstitucionService, 'snapshot_institucional'), \
    'snapshot_institucional sigue presente'
print('ok')
"
```

---

## T8 — Suite de tests unitarios

**Archivo**: `tests/unit/services/test_identidad_institucional.py` (nuevo)

**Cobertura mínima** (un test por requisito clave):

| Test | Requisito |
|---|---|
| `test_get_info_institucional_sin_institucion_retorna_defaults` | R5 |
| `test_get_info_institucional_con_institucion_lee_de_institucion` | R4 |
| `test_actualizar_info_institucional_sin_institucion_lanza` | R8 |
| `test_actualizar_info_institucional_delega_en_institucion_service` | R7 |
| `test_dane_invalido_lanza_en_dominio` | R9 |
| `test_informe_service_get_informacion_institucional_delega` | R16 |
| `test_informe_service_get_informacion_institucional_sin_provider_lanza` | R16 |
| `test_configuracion_anio_no_tiene_campos_identidad` | R2/R3 |

Todos los tests usan `MagicMock` / repositorios en memoria; ninguno toca BD real.

**Artefacto**: `tests/unit/services/test_identidad_institucional.py` (nuevo).

**Verificación**:
```
python -m pytest tests/unit/services/test_identidad_institucional.py -v
```

---

## T9 — Verificación de integridad global

**Archivos**: ninguno nuevo. Confirma que todos los archivos del paso son
coherentes entre sí y con el harness.

**Verificación** (ejecutar en orden):
```
python -m pytest tests/unit/services/test_identidad_institucional.py -v
python -m ruff check src/domain/models/configuracion.py src/infrastructure/db/repositories/sqlite_configuracion_repo.py src/services/configuracion_service.py src/services/informe_service.py src/services/institucion_service.py
python init.py
```

El harness (`init.py`) debe finalizar completamente verde antes de declarar el
paso como `done`.
