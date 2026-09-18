# Requisitos: Huella en config, catálogos y planes (obs_04c)

> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §2.
> **Depende de:** `obs_01_huella_actor` (helper `auditar_cambio` disponible) y
> `obs_02_puerta_huella` (la puerta que mide este paso).
> **Posición en la serie:** último tranche — al cerrar este paso,
> `SERVICIOS_SIN_HUELLA_DEUDA` queda vacío y `check_auditoria.py` es el
> guardián completo de cobertura universal.

## Estado actual (2026-09-09)

Los siete archivos del destino_v2 tienen **cero** llamadas a `auditar_cambio`:

- `catalogo_academico_service.py` — 11 métodos mutadores propios.
- `configuracion_service.py` — 8 métodos mutadores propios (2 extra-service
  tienen @requiere_escritura pero no son mutadores propios — ver nota §2 del
  diseño).
- `plan_estudios_service.py` — 4 métodos mutadores propios (`set_horas` delega
  en `actualizar`; no se cuenta por separado).
- `institucion_service.py` — 3 métodos mutadores propios.
- `plan_mejoramiento_service.py` — 4 métodos mutadores propios.
- `nivelacion_service.py` — 3 métodos mutadores propios.
- `aprovisionamiento_institucion_service.py` — 1 método mutador propio
  (`finalizar_configuracion_inicial` delega enteramente; no se cuenta).

> **Nota sobre conteos:** el `step_list.json` registra conteos de una snapshot
> anterior. Los conteos reales verificados en código son los de esta spec;
> los de plan_mejoramiento (4, no 1) y nivelacion (3, no 1) difieren
> significativamente porque esos servicios crecieron tras la snapshot.

---

R1: CADA MÉTODO MUTADOR PROPIO de los siete servicios DEBE llamar a
    `auditar_cambio` conservando el estado anterior y el nuevo cuando aplique.

R2: LOS MÉTODOS QUE ELIMINAN deben capturar el estado anterior antes del
    `repo.eliminar_*` y registrar `AccionCambio.DELETE` con ese estado.

R3: LOS MÉTODOS QUE CREAN deben registrar `AccionCambio.CREATE` con la
    entidad resultante.

R4: LOS MÉTODOS QUE ACTUALIZAN deben registrar `AccionCambio.UPDATE` con
    anterior y nuevo. El estado anterior se carga desde el repositorio
    antes de modificar.

R5: MÉTODOS DELEGADORES Y NOOP no se auditan en este servicio:
    - `actualizar_info_institucional` (ConfiguracionService) delega en
      `Container.institucion_service().actualizar()`; la auditoría va en
      `InstitucionService`.
    - `sincronizar_snapshot_desde_institucion` (ConfiguracionService) está
      marcado como obsoleto desde `datos_06` y no realiza escritura real;
      no requiere `auditar_cambio`.
    - `set_horas` (PlanEstudiosService) delega en `self.actualizar()`;
      la auditoría va en `actualizar`, no en `set_horas`.
    - `finalizar_configuracion_inicial` (AprovisionamientoInstitucionService)
      delega en `Container.preferencias_service().set()` y
      `Container.institucion_service().marcar_configuracion_inicial_completa()`;
      no realiza escritura directa al repo.

R6: PARA OPERACIONES EN LOTE o con múltiples entidades generadas por un
    solo caso de uso (e.g., `ejecutar_corte` genera CortePlan + N registros
    de NotaCortePlan) se registra UN ÚNICO `auditar_cambio` resumen, no
    una entrada por registro generado.

R7: TODOS LOS SERVICIOS DEBEN aceptar `auditoria_repo: IAuditoriaRepository
    | None = None` en su constructor y almacenarlo en `self._auditoria_repo`.
    Ningún caller existente se rompe (parámetro opcional con default None).

R8: `container.py` DEBE inyectar `auditoria_repo=Container.auditoria_repo()`
    en los siete constructores afectados.

R9: `SERVICIOS_SIN_HUELLA_DEUDA` en `check_auditoria.py` DEBE quedar VACÍO
    al cerrar este paso: este tranche es el último, y todas las entradas
    anteriores (obs_04a, obs_04b) ya se retiraron en sus pasos respectivos.

R10: UN TEST DE INTEGRACIÓN representativo por cada servicio DEBE afirmar que
     `audit_log` crece con `usuario_id` e `institucion_id` no nulos tras la
     escritura.

## Criterio de done

- `python scripts/check_auditoria.py` termina sin listar ningún servicio
  como pendiente fuera de la deuda.
- `SERVICIOS_SIN_HUELLA_DEUDA` es un dict vacío `{}`.
- El test de integración de `obs_02` pasa verde con las entradas nuevas.
- `python scripts/init.py` completamente verde.
