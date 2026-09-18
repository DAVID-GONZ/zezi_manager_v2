# Diseño: Huella en config, catálogos y planes (obs_04c)

> **Requisitos:** `requirements.md` de esta misma carpeta.
> **Patrón de referencia:** `src/services/evaluacion_service.py` — servicio que
> ya usa `auditar_cambio` correctamente tras `obs_01`.

## 1. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/services/catalogo_academico_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 11 métodos (ver §3). |
| `src/services/configuracion_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 8 métodos (ver §4). |
| `src/services/plan_estudios_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 4 métodos (ver §5). |
| `src/services/institucion_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 3 métodos (ver §6). |
| `src/services/plan_mejoramiento_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 4 métodos (ver §7). |
| `src/services/nivelacion_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 3 métodos (ver §8). |
| `src/services/aprovisionamiento_institucion_service.py` | Aceptar `auditoria_repo` en `__init__`; añadir `auditar_cambio` en 1 método (ver §9). |
| `container.py` | Inyectar `auditoria_repo=Container.auditoria_repo()` en los siete constructores. |
| `scripts/check_auditoria.py` | Vaciar `SERVICIOS_SIN_HUELLA_DEUDA` (retirar todas las entradas restantes). |
| `tests/integration/test_huella_cobertura.py` | Añadir test representativo por cada uno de los siete servicios. |

## 2. Patrón de llamada (igual en todos los servicios)

```python
# En __init__
from src.domain.ports.auditoria_repo import IAuditoriaRepository

def __init__(self, repo: ..., auditoria_repo: IAuditoriaRepository | None = None):
    self._auditoria_repo = auditoria_repo
    ...

# CREATE
from src.services.auditoria_helpers import auditar_cambio
from src.domain.models.auditoria import AccionCambio

resultado = self._repo.guardar_area(area)
auditar_cambio(
    self._auditoria_repo,
    accion=AccionCambio.CREATE,
    tabla="areas",
    registro_id=resultado.id,
    nuevo=resultado.model_dump(),
)

# UPDATE — cargar anterior ANTES de modificar
anterior = self._repo.get_area(area_id)
resultado = self._repo.actualizar_area(actualizada)
auditar_cambio(
    self._auditoria_repo,
    accion=AccionCambio.UPDATE,
    tabla="areas",
    registro_id=area_id,
    anterior=anterior.model_dump() if anterior else None,
    nuevo=resultado.model_dump(),
)

# DELETE — capturar anterior ANTES del eliminar
anterior = self._repo.get_area(area_id)
ok = self._repo.eliminar_area(area_id)
auditar_cambio(
    self._auditoria_repo,
    accion=AccionCambio.DELETE,
    tabla="areas",
    registro_id=area_id,
    anterior=anterior.model_dump() if anterior else None,
)
```

## 3. Inventario — CatalogoAcademicoService (11 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `guardar_area` | `areas` | CREATE | |
| 2 | `actualizar_area` | `areas` | UPDATE | cargar anterior antes de modificar |
| 3 | `eliminar_area` | `areas` | DELETE | cargar anterior antes de eliminar |
| 4 | `set_color_area` | `areas` | UPDATE | `nuevo={"area_id": ..., "color": color}` |
| 5 | `guardar_asignatura` | `asignaturas` | CREATE | |
| 6 | `actualizar_asignatura` | `asignaturas` | UPDATE | cargar anterior antes de modificar |
| 7 | `eliminar_asignatura` | `asignaturas` | DELETE | cargar anterior antes de eliminar |
| 8 | `guardar_grupo` | `grupos` | CREATE | |
| 9 | `actualizar_grupo` | `grupos` | UPDATE | cargar anterior antes de modificar |
| 10 | `eliminar_grupo` | `grupos` | DELETE | cargar anterior antes de eliminar |
| 11 | `asignar_director_grupo` | `grupos` | UPDATE | `nuevo={"grupo_id": ..., "director_id": director_id}` |

## 4. Inventario — ConfiguracionService (8 mutadores propios)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear_anio` | `configuracion_anio` | CREATE | el objeto `config` resultante de `self._repo.guardar()` |
| 2 | `activar_anio` | `configuracion_anio` | UPDATE | `nuevo={"anio_id": anio_id, "activo": True}` |
| 3 | `configurar_niveles` | `niveles_desempeno` | UPDATE | batch replace; `nuevo={"anio_id": anio_id, "n_niveles": len(entidades)}` (R6) |
| 4 | `agregar_nivel` | `niveles_desempeno` | CREATE | el `guardado` resultante |
| 5 | `actualizar_nivel` | `niveles_desempeno` | UPDATE | cargar `actual` antes (ya disponible en el método en la variable `actual`) |
| 6 | `eliminar_nivel` | `niveles_desempeno` | DELETE | cargar nivel antes de eliminar; `anterior=nivel_obj.model_dump()` |
| 7 | `guardar_criterios` | `criterios_promocion` | CREATE | UPSERT — usar CREATE siempre |
| 8 | `actualizar_configuracion_academica` | `configuracion_anio` | UPDATE | cargar `config` antes (ya disponible vía `self.get_by_id(anio_id)`) |

**Métodos excluidos (R5):**
- `actualizar_info_institucional` → delega en `Container.institucion_service().actualizar()`.
- `sincronizar_snapshot_desde_institucion` → NOOP desde `datos_06`; no realiza escritura.

## 5. Inventario — PlanEstudiosService (4 mutadores propios)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `guardar_grado` | `grados` | CREATE | UPSERT — usar CREATE |
| 2 | `eliminar_grado` | `grados` | DELETE | cargar grado antes de eliminar |
| 3 | `actualizar` | `plan_estudios` | CREATE | UPSERT de horas; usar CREATE |
| 4 | `eliminar` | `plan_estudios` | DELETE | `anterior={"grado": grado, "asignatura_id": asignatura_id}` |

**Método excluido (R5):**
- `set_horas` → delega en `self.actualizar(dto)`.

## 6. Inventario — InstitucionService (3 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear` | `instituciones` | CREATE | el `inst` retornado |
| 2 | `actualizar` | `instituciones` | UPDATE | anterior cargado vía `self._repo.get_by_id(institucion_id)` en el método |
| 3 | `marcar_configuracion_inicial_completa` | `instituciones` | UPDATE | `nuevo={"institucion_id": institucion_id, "configuracion_inicial_completa": True}` |

## 7. Inventario — PlanMejoramientoService (4 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `ejecutar_corte` | `cortes_plan` | CREATE | crea CortePlan + N NotaCortePlan; un resumen: `nuevo={"asignacion_id": ..., "periodo_id": ..., "n_estudiantes": len(estudiantes)}` (R6) |
| 2 | `agregar_actividad` | `actividades_plan` | CREATE | el `actividad` resultante |
| 3 | `calificar_nota` | `notas_plan` | CREATE | UPSERT de nota; usar CREATE |
| 4 | `cerrar_plan_estudiante` | `notas_corte_plan` | UPDATE | el cierre del estudiante |

> El nombre exacto de las tablas (`cortes_plan`, `actividades_plan`, etc.) puede
> verificarse en `src/infrastructure/database/schema.py` o en el repo correspondiente.
> Usar los nombres de tabla que use el repositorio en su SQL.

## 8. Inventario — NivelacionService (3 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `agregar_actividad` | `actividades_nivelacion` | CREATE | el `actividad` resultante; también crea N `NotaNivelacion` vacías — un único `auditar_cambio` resumen es suficiente (R6): `nuevo={"asignacion_id": ..., "n_estudiantes": len(estudiante_ids)}` |
| 2 | `calificar_nota` | `notas_nivelacion` | CREATE | UPSERT — usar CREATE |
| 3 | `cerrar_nivelacion` | `cierres_nivelacion` | UPDATE | el cierre resultante |

## 9. Inventario — AprovisionamientoInstitucionService (1 mutador)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear_institucion_con_director` | `instituciones` | CREATE | registrar la `inst` creada; el seed de catálogos y la creación del director se auditan en sus respectivos servicios |

**Método excluido (R5):**
- `finalizar_configuracion_inicial` → delega en `Container.preferencias_service().set()` y
  `Container.institucion_service().marcar_configuracion_inicial_completa()`.

## 10. Sobre SERVICIOS_SIN_HUELLA_DEUDA (R9)

Este es el **último tranche**. Al completar obs_04c, la lista debe quedar vacía `{}`.
Antes de tocarla, verificar que:
1. `python scripts/check_auditoria.py` no lista ninguno de los siete servicios como
   mutadores sin huella (solo así se puede retirar su entrada sin activar el doble filo).
2. Si algún servicio sigue apareciendo en la lista de la puerta después de instrumentarlo,
   el bug está en la instrumentación, no en la lista.

## 11. Orden de implementación recomendado

1. `catalogo_academico_service.py` — 11 métodos, patrón CRUD repetitivo (bajo riesgo).
2. `institucion_service.py` — 3 métodos simples.
3. `configuracion_service.py` — 8 métodos (cuidar los delegate/noop excluidos de §4).
4. `plan_estudios_service.py` — 4 métodos (cuidar que `set_horas` es delegador).
5. `plan_mejoramiento_service.py` — 4 métodos (ejecutar_corte es complejo: resumen).
6. `nivelacion_service.py` — 3 métodos (agregar_actividad crea entidades hijas: resumen).
7. `aprovisionamiento_institucion_service.py` — 1 método.
8. Cablear `container.py`.
9. Vaciar `SERVICIOS_SIN_HUELLA_DEUDA` tras verificar que la puerta pasa.
10. Tests de integración.

## 12. Alternativa descartada

**Auditar `actualizar_info_institucional` en ConfiguracionService además de en
InstitucionService.** Produciría doble auditoría: el delegate ya instruye a
InstitucionService.actualizar() que registra la huella. El precedente de la fachada
`InfraestructuraService` en obs_04b aplica igualmente aquí.
