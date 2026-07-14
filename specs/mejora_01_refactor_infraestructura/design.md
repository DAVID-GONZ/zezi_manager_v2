# Diseño: Descomposición de InfraestructuraService (mejora_01_refactor_infraestructura)

## Estrategia general

Refactor **incremental y reversible**: se extrae un subdominio a la vez, se cablea
en `Container`, se re-apunta a los consumidores y se corre `python init.py` verde
antes de pasar al siguiente. `IInfraestructuraRepository` **no se parte en esta
mejora** (partir el puerto es un cambio de contrato mayor); los nuevos servicios
siguen recibiendo el mismo repo por inyección. El objetivo de esta mejora es
descomponer la **capa de servicios** (el punto de dolor de mantenibilidad), no los
repositorios.

## 1. Servicios resultantes (target)

Partiendo de los grupos de métodos ya documentados en `docs/dominio.md`:

| Servicio nuevo | Subdominio | Métodos que absorbe (grupos) |
|---|---|---|
| `EscenarioHorarioService` | Escenarios de horario | get/listar/crear/actualizar/activar/eliminar/duplicar escenario; listar_horario_*_escenario |
| `FranjaService` | Plantillas y franjas | plantillas de franja + franjas + activar/eliminar plantilla |
| `CatalogoAcademicoService` | Áreas, asignaturas, grupos | CRUD de `AreaConocimiento`, `Asignatura`, `Grupo` |
| `SalaService` | Salas | CRUD de salas + asignar sala a grupo |
| `RestriccionGeneracionService` | Restricciones + config de generación | config_generacion, ventanas de grupo, bloques anclados, franjas de reunión, límites docente, disponibilidad docente |

`InfraestructuraService` queda como **fachada delgada** (o se retira al final) que,
durante la transición (R4), delega en los nuevos servicios para no romper páginas
que aún llamen a la API previa.

**Horarios (R8):** los métodos de bloques horarios de `InfraestructuraService`
(`guardar_horario`, `eliminar_horario`, `listar_horario_grupo/docente`,
`existe_conflicto_horario`, `get_estadisticas`) se consolidan en el
`HorarioService` existente, que ya es el dueño canónico de los bloques. Si hay
duplicación exacta, se elimina la copia de `InfraestructuraService` y se re-apunta
el consumidor al `HorarioService`.

## 2. Métodos de Container a añadir

Uno por servicio nuevo, con el patrón lazy existente:

```python
@classmethod
def escenario_horario_service(cls):
    from src.services.escenario_horario_service import EscenarioHorarioService
    return cls._get_or_create(
        "escenario_horario_service",
        lambda: EscenarioHorarioService(repo=cls.infraestructura_repo()),
    )
# ... franja_service, catalogo_academico_service, sala_service,
#     restriccion_generacion_service (cada uno recibe infraestructura_repo())
```

`Container.diagnostico()` debe incluir los nuevos nombres en su lista de métodos.

## 3. Reglas del movimiento (MOVER, no reescribir)

- Cortar el método de `InfraestructuraService` y pegarlo **idéntico** en el nuevo
  servicio; cambiar solo el `self._repo` si el nombre del atributo difiere.
- No tocar la lógica interna ni las firmas (R5, R6).
- Cada método movido sigue decorado con `@requiere_escritura` si mutaba (respeta el
  modo "Ver como").
- Re-apuntar los consumidores en `src/interface/pages/**` de
  `Container.infraestructura_service().X()` a `Container.<nuevo>_service().X()`.
- No apilar código: cuando un método se mueve, se borra del origen (o el origen
  delega explícitamente durante la transición).

## 4. Orden de extracción (dependencia mínima primero)

1. `SalaService` (autocontenido, pocas dependencias).
2. `FranjaService` (plantillas/franjas).
3. `EscenarioHorarioService`.
4. `RestriccionGeneracionService`.
5. `CatalogoAcademicoService`.
6. Consolidación de horarios en `HorarioService` (R8) y retiro/adelgazamiento de
   `InfraestructuraService`.

Cada paso deja la suite verde antes del siguiente.

## 5. Alternativa descartada

Se consideró **partir también `IInfraestructuraRepository`** en varios puertos. Se
descartó en esta mejora porque es un cambio de contrato de gran superficie (100
métodos, todos los tests de integración) con beneficio marginal frente al de la
capa de servicios; se puede abordar como mejora posterior si el dolor persiste.

## 6. Manejo de errores

Sin cambios: los métodos movidos conservan su manejo de errores actual (los
`ValueError` de validación de integridad referencial se propagan igual). La capa de
interfaz sigue capturándolos como hoy.

## Nota de implementación (riesgo conocido)

El mayor riesgo es dejar consumidores apuntando al servicio viejo tras mover un
método (llamada rota). Mitigación: tras cada extracción, `grep` de
`infraestructura_service().<método_movido>` en `src/interface/` debe dar 0
coincidencias antes de marcar la task.
