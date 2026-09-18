# Diseño: Huella en infraestructura, horarios, salas y franjas (obs_04b)

> **Requisitos:** `requirements.md` de esta misma carpeta.
> **Patrón de referencia:** `src/services/evaluacion_service.py` — servicio que
> ya usa `auditar_cambio` correctamente tras `obs_01`.

## 1. Contexto arquitectural — la fachada

`InfraestructuraService` (`infraestructura_service.py`) fue refactorizado en
`mejora_01` como fachada de delegación pura: cada uno de sus ~40 métodos llama
a un sub-servicio (`_sala_service()`, `_franja_service()`, etc.), no al repo
directamente. Por eso:

- **Ningún `auditar_cambio` va en `infraestructura_service.py`** — añadirlo allí
  duplicaría la auditoría con lo que hacen los sub-servicios.
- La fachada solo necesita recibir `auditoria_repo` y pasarlo cuando construye los
  sub-servicios en sus métodos `_X_service()`.

## 2. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/services/infraestructura_service.py` | Aceptar `auditoria_repo` en `__init__`; almacenarlo; pasarlo en los 4 factorías lazy de sub-servicios. |
| `src/services/escenario_horario_service.py` | Aceptar `auditoria_repo`; añadir `auditar_cambio` en 7 métodos (ver §4). |
| `src/services/sala_service.py` | Aceptar `auditoria_repo`; añadir `auditar_cambio` en 4 métodos (ver §5). |
| `src/services/franja_service.py` | Aceptar `auditoria_repo`; añadir `auditar_cambio` en 4 métodos (ver §6). |
| `src/services/restriccion_generacion_service.py` | Aceptar `auditoria_repo`; añadir `auditar_cambio` en 17 métodos (ver §7). |
| `src/services/horario_service.py` | Aceptar `auditoria_repo`; añadir `auditar_cambio` en 4 métodos (ver §8). |
| `container.py` | Inyectar `auditoria_repo=Container.auditoria_repo()` en `InfraestructuraService` y en `HorarioService`. |
| `scripts/check_auditoria.py` | Retirar las 6 entradas de `SERVICIOS_SIN_HUELLA_DEUDA`. |
| `tests/integration/test_huella_cobertura.py` | Añadir test representativo por cada sub-servicio. |

## 3. Propagación en la fachada (R7)

```python
# infraestructura_service.py — __init__
def __init__(
    self,
    repo: IInfraestructuraRepository,
    auditoria_repo: IAuditoriaRepository | None = None,
) -> None:
    self._repo = repo
    self._auditoria_repo = auditoria_repo
    self._subservicios: dict = {}

# Los 4 factorías lazy — ejemplo con SalaService
def _sala_service(self):
    svc = self._subservicios.get("sala")
    if svc is None:
        from src.services.sala_service import SalaService
        svc = SalaService(repo=self._repo, auditoria_repo=self._auditoria_repo)
        self._subservicios["sala"] = svc
    return svc
# Idem para _franja_service, _escenario_horario_service, _restriccion_generacion_service
```

## 4. Inventario — EscenarioHorarioService (7 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear_escenario` | `escenarios_horario` | CREATE | |
| 2 | `crear_escenario_simple` | `escenarios_horario` | CREATE | llama `self._repo` directamente, no `self.crear_escenario()` |
| 3 | `actualizar_escenario` | `escenarios_horario` | UPDATE | |
| 4 | `renombrar_escenario` | `escenarios_horario` | UPDATE | sin `@requiere_escritura`; el objeto anterior se recibe como parámetro `esc_existente` |
| 5 | `activar_escenario` | `escenarios_horario` | UPDATE | sin estado previo cargable en el método; `nuevo={"escenario_id": ..., "activo": True}` |
| 6 | `eliminar_escenario` | `escenarios_horario` | DELETE | no hay `get` previo; usar `nuevo=None, anterior={"escenario_id": escenario_id}` como resumen |
| 7 | `duplicar_escenario` | `escenarios_horario` | CREATE | anotar `nuevo=resultado.model_dump()` si disponible |

## 5. Inventario — SalaService (4 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear_sala` | `salas` | CREATE | |
| 2 | `actualizar_sala` | `salas` | UPDATE | anterior ya cargado con `self._repo.get_sala(sala.id)` (línea 97) |
| 3 | `eliminar_sala` | `salas` | DELETE | anterior disponible vía `_verificar_pertenencia_obj(self._repo.get_sala(...))` |
| 4 | `asignar_sala_a_grupo` | `grupos` | UPDATE | `nuevo={"grupo_id": grupo_id, "sala_id": sala_id}` |

## 6. Inventario — FranjaService (4 mutadores)

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear_plantilla_simple` | `plantillas_franja` | CREATE | |
| 2 | `guardar_franjas` | `franjas` | UPDATE | lote completo; `nuevo={"plantilla_id": plantilla_id, "n_franjas": n}` (R6: un resumen, no N entradas) |
| 3 | `activar_plantilla` | `plantillas_franja` | UPDATE | `nuevo={"plantilla_id": plantilla_id, "activa": True}` |
| 4 | `eliminar_plantilla` | `plantillas_franja` | DELETE | anterior disponible vía `_verificar_pertenencia_obj(self._repo.get_plantilla_franja(...))` |

## 7. Inventario — RestriccionGeneracionService (17 mutadores)

| # | Método | Tabla | Acción | @r/e | Notas |
|---|---|---|---|---|---|
| 1 | `bloquear_franjas_docente` | `disponibilidad_docente` | CREATE | ✗ | resumen: `nuevo={"usuario_id": ..., "n_slots": len(slots)}` |
| 2 | `limpiar_disponibilidad_docente` | `disponibilidad_docente` | DELETE | ✗ | resumen: `anterior={"usuario_id": usuario_id}` |
| 3 | `guardar_disponibilidad_docente` | `disponibilidad_docente` | UPDATE | ✓ | reemplaza; `nuevo={"usuario_id": ..., "n_slots": len(slots)}` |
| 4 | `crear_config_generacion` | `config_generacion` | CREATE | ✓ | |
| 5 | `actualizar_config_generacion` | `config_generacion` | UPDATE | ✓ | anterior cargado en método (línea 136) |
| 6 | `eliminar_config_generacion` | `config_generacion` | DELETE | ✓ | |
| 7 | `cambiar_estado_config` | `config_generacion` | UPDATE | ✓ | `nuevo={"config_id": ..., "estado": nuevo_estado}` |
| 8 | `duplicar_config_generacion` | `config_generacion` | CREATE | ✓ | |
| 9 | `crear_ventana_grupo` | `ventanas_grupo` | CREATE | ✓ | |
| 10 | `eliminar_ventana_grupo` | `ventanas_grupo` | DELETE | ✓ | |
| 11 | `crear_bloque_anclado` | `bloques_anclados` | CREATE | ✓ | |
| 12 | `eliminar_bloque_anclado` | `bloques_anclados` | DELETE | ✓ | |
| 13 | `crear_franja_reunion` | `franjas_reunion` | CREATE | ✓ | |
| 14 | `actualizar_franja_reunion` | `franjas_reunion` | UPDATE | ✓ | |
| 15 | `eliminar_franja_reunion` | `franjas_reunion` | DELETE | ✓ | |
| 16 | `set_limites_docente` | `limites_docente` | UPSERT | ✓ | usar CREATE |
| 17 | `set_limites_docente_simple` | `limites_docente` | UPSERT | ✓ | llama `self._repo` directamente; no delega en `set_limites_docente()` |

## 8. Inventario — HorarioService (4 mutadores)

`HorarioService` recibe `infra_repo` (el repositorio, no la fachada). El
parámetro `auditoria_repo` se inyecta directamente desde `container.py`.

| # | Método | Tabla | Acción | Notas |
|---|---|---|---|---|
| 1 | `crear_bloque` | `horarios` | CREATE | |
| 2 | `mover_bloque` | `horarios` | UPDATE | anterior cargado con `self._infra.get_horario()` (línea 161) |
| 3 | `actualizar_bloque` | `horarios` | UPDATE | anterior cargado con `self._infra.get_horario()` (línea 196) |
| 4 | `eliminar_bloque` | `horarios` | DELETE | leer el bloque antes de eliminar si se quiere capturar anterior |

## 9. Sobre la entrada `infraestructura_service` en SERVICIOS_SIN_HUELLA_DEUDA

Tras `mejora_01`, `infraestructura_service.py` no llama directamente al repo;
`check_auditoria.py` puede o no haberlo identificado como mutador dependiendo de si
razona sobre delegación interna:

- **Si check_auditoria la marca como mutadora sin huella:** retirarla de la lista
  tras verificar que los sub-servicios sí tienen huella basta (la cobertura real
  la tienen los sub-servicios).
- **Si check_auditoria NO la marca como mutadora:** la entrada ya no existe en la
  lista; retirar solo las 5 entradas de los sub-servicios y `horario_service`.

Verificar con `python scripts/check_auditoria.py` antes de tocar la lista, para no
activar el doble filo en ninguna dirección.

## 10. Orden de implementación recomendado

1. `infraestructura_service.py` — solo `__init__` + 4 factorías lazy (mínimo riesgo).
2. `container.py` — cablear el auditoria_repo.
3. `escenario_horario_service.py` (7 métodos — cohesivos, sin dependencias cruzadas).
4. `sala_service.py` (4 métodos — los más simples del lote).
5. `franja_service.py` (4 métodos).
6. `restriccion_generacion_service.py` (17 métodos — mayor volumen; hacer de una vez).
7. `horario_service.py` (4 métodos — ya tiene la lógica de carga del estado anterior).
8. Retirar entradas de `SERVICIOS_SIN_HUELLA_DEUDA` tras verificar que la puerta pasa.
9. Tests de integración.

## 11. Alternativa descartada

**Añadir `auditar_cambio` en `InfraestructuraService` además de en los sub-servicios.**
Produciría doble auditoría: cuando la UI llama a `Container.infraestructura_service().crear_sala()`,
la huella se registraría dos veces (una en la fachada y otra en `SalaService`). El
beneficio de auditar en la fachada es cero porque la fachada no añade lógica; la
huella en el sub-servicio es suficiente.
