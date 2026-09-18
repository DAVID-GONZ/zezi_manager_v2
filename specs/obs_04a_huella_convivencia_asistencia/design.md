# Diseño: Huella en convivencia y asistencia (obs_04a)

> **Requisitos:** `requirements.md` de esta misma carpeta.
> **Patrón de referencia:** `src/services/evaluacion_service.py` y
> `src/services/periodo_service.py` — servicios que ya usan `auditar_cambio`
> correctamente tras `obs_01`.

## 1. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/services/convivencia_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 19 métodos mutadores propios (ver §3). |
| `src/services/asistencia_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 2 métodos propios (ver §4). |
| `src/services/alerta_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 4 métodos (ver §5). |
| `container.py` | Inyectar `auditoria_repo=Container.auditoria_repo()` en los tres constructores. |
| `scripts/check_auditoria.py` | Retirar `convivencia_service`, `asistencia_service`, `alerta_service` de `SERVICIOS_SIN_HUELLA_DEUDA`. |
| `tests/integration/test_huella_cobertura.py` | Añadir test representativo por cada uno de los tres servicios. |

## 2. Patrón de llamada (igual en los tres servicios)

```python
# En __init__
from src.domain.ports.auditoria_repo import IAuditoriaRepository

def __init__(self, repo: ..., auditoria_repo: IAuditoriaRepository | None = None, ...):
    self._auditoria_repo = auditoria_repo
    ...

# En un método CREATE
from src.services.auditoria_helpers import auditar_cambio
from src.domain.models.auditoria import AccionCambio

def crear_categoria(self, dto, ...) -> CategoriaObservacion:
    ...
    resultado = self._repo.guardar_categoria(categoria)
    auditar_cambio(
        self._auditoria_repo,
        accion=AccionCambio.CREATE,
        tabla="categorias_observacion",
        registro_id=resultado.id,
        nuevo=resultado.model_dump(),
    )
    return resultado

# En un método UPDATE — cargar anterior ANTES de modificar
def actualizar_categoria(self, categoria_id, dto) -> CategoriaObservacion:
    anterior = self._repo.get_categoria(categoria_id)  # ya cargado por _get_o_lanzar
    ...
    resultado = self._repo.actualizar_categoria(actualizada)
    auditar_cambio(
        self._auditoria_repo,
        accion=AccionCambio.UPDATE,
        tabla="categorias_observacion",
        registro_id=categoria_id,
        anterior=anterior.model_dump() if anterior else None,
        nuevo=resultado.model_dump(),
    )
    return resultado

# En un método DELETE — capturar anterior ANTES del eliminar
def eliminar_observacion(self, observacion_id) -> bool:
    anterior = self._get_observacion_o_lanzar(observacion_id)  # ya disponible
    resultado = self._repo.eliminar_observacion(observacion_id)
    auditar_cambio(
        self._auditoria_repo,
        accion=AccionCambio.DELETE,
        tabla="observaciones_periodo",
        registro_id=observacion_id,
        anterior=anterior.model_dump(),
    )
    return resultado
```

## 3. Inventario de métodos mutadores — ConvivenciaService

Los 19 métodos propios que deben llamar a `auditar_cambio` (los 5 delegadores
y los de solo lectura quedan excluidos):

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `registrar_observacion` | `observaciones_periodo` | CREATE / UPDATE | upsert: CREATE si nueva, UPDATE si actualiza existente |
| 2 | `eliminar_observacion` | `observaciones_periodo` | DELETE | anterior ya cargado por `_get_observacion_o_lanzar` |
| 3 | `registrar_comportamiento` | `registro_comportamiento` | CREATE | |
| 4 | `notificar_acudiente` | `registro_comportamiento` | UPDATE | anterior = registro antes de `registrar_notificacion()` |
| 5 | `agregar_entrada_seguimiento` | `entradas_seguimiento` | CREATE | tabla de la entrada; la actualización legacy de `seguimiento` en el registro es UPDATE secundario |
| 6 | `eliminar_registro` | `registro_comportamiento` | DELETE | anterior ya cargado por `_get_registro_o_lanzar` |
| 7 | `registrar_nota_comportamiento` | `notas_comportamiento` | CREATE / UPDATE | upsert vía `guardar_nota` |
| 8 | `crear_tipo_situacion` | `tipos_situacion` | CREATE | |
| 9 | `actualizar_tipo_situacion` | `tipos_situacion` | UPDATE | |
| 10 | `desactivar_tipo_situacion` | `tipos_situacion` | UPDATE | |
| 11 | `crear_medida_pedagogica` | `medidas_pedagogicas` | CREATE | |
| 12 | `actualizar_medida_pedagogica` | `medidas_pedagogicas` | UPDATE | |
| 13 | `desactivar_medida_pedagogica` | `medidas_pedagogicas` | UPDATE | |
| 14 | `crear_categoria` | `categorias_observacion` | CREATE | |
| 15 | `actualizar_categoria` | `categorias_observacion` | UPDATE | |
| 16 | `desactivar_categoria` | `categorias_observacion` | UPDATE | |
| 17 | `crear_plantilla` | `plantillas_observacion` | CREATE | |
| 18 | `actualizar_plantilla` | `plantillas_observacion` | UPDATE | |
| 19 | `desactivar_plantilla` | `plantillas_observacion` | UPDATE | |
| 20 | `registrar_observacion_desde_plantilla` | `observaciones_periodo` | CREATE / UPDATE | upsert; la llamada a `incrementar_uso_plantilla` no es un cambio de negocio auditable |
| 21 | `promover_observacion_a_plantilla` | `plantillas_observacion` | CREATE | |
| 22 | `promover_a_comportamiento` | `registro_comportamiento` | CREATE | también actualiza `observaciones_periodo` → segundo `auditar_cambio` con UPDATE |
| 23 | `crear_alerta_seguimiento_manual` | `alertas` | CREATE | via `_alerta_repo` |

**Métodos excluidos (delegadores):**
- `agregar_seguimiento` → delega en `agregar_entrada_seguimiento` (método 5).

## 4. Inventario — AsistenciaService

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `registrar` | `control_diario` | CREATE | |
| 2 | `registrar_masivo` | `control_diario` | CREATE | un `auditar_cambio` por control, o un registro resumen con `nuevo={"grupo_id": ..., "fecha": ..., "conteo": n}` |

**Excluido:** `guardar_asistencia_masiva` → delega en `registrar_masivo`.

> **Decisión de diseño para el masivo:** registrar un único `auditar_cambio`
> con la tabla `control_diario`, `accion=CREATE`, `nuevo={"grupo_id": ...,
> "asignacion_id": ..., "fecha": ..., "n_registros": n}` es suficiente para
> tener trazabilidad sin generar N filas por pasada. Alternativa descartada: N
> llamadas individuales saturarían audit_log con grupos de 40+ estudiantes.

## 5. Inventario — AlertaService

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `configurar_alerta` | `configuracion_alertas` | CREATE / UPDATE | upsert |
| 2 | `desactivar_configuracion` | `configuracion_alertas` | UPDATE | anterior no disponible sin get previo; usar `nuevo={"anio_id": anio_id, "tipo": tipo_alerta.value, "activa": False}` |
| 3 | `resolver_alerta` | `alertas` | UPDATE | anterior ya cargado por `_get_alerta_o_lanzar` |
| 4 | `resolver_alertas_de_estudiante` | `alertas` | UPDATE | registro resumen: `nuevo={"estudiante_id": ..., "tipo": ..., "n_resueltas": n}` |
| 5 | `detectar_riesgo_academico` | `alertas` | CREATE | registro resumen: `nuevo={"grupo_id": ..., "n_alertas": n}` |

## 6. Orden de implementación recomendado

1. Modificar `__init__` de los tres servicios (cambio mínimo, no rompe nada).
2. Cablear `container.py`.
3. Añadir llamadas en ConvivenciaService (mayor volumen → mayor beneficio).
4. Añadir llamadas en AsistenciaService.
5. Añadir llamadas en AlertaService.
6. Retirar las tres entradas de `SERVICIOS_SIN_HUELLA_DEUDA`.
7. Añadir tests de integración.

## 7. Alternativa descartada

**Un método privado `_auditar_conv(...)` en ConvivenciaService.** Añade una
indirección que oscurece el flujo sin aportar valor: `auditar_cambio` ya es el
helper único de obs_01. El precedente de 7 copias de `_auditar` —que motivó
obs_01— se repite con una capa de abstracción local.
