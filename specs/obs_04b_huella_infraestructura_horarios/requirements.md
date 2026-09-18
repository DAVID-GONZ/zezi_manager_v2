# Requisitos: Huella en infraestructura, horarios, salas y franjas (obs_04b)

> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §2.
> **Depende de:** `obs_01_huella_actor` (helper `auditar_cambio` disponible) y
> `obs_02_puerta_huella` (la puerta que mide este paso).
> **Nota arquitectural:** este paso incluye `infraestructura_service.py`, que
> tras `mejora_01` es una **fachada de delegación pura**: sus métodos no llaman
> al repositorio directamente sino a sub-servicios (`EscenarioHorarioService`,
> `SalaService`, `FranjaService`, `RestriccionGeneracionService`). La huella va
> en los sub-servicios; la fachada solo necesita propagar `auditoria_repo`.

## Estado actual (2026-09-09)

Los seis archivos del destino_v2 tienen **cero** llamadas a `auditar_cambio`:
- `escenario_horario_service.py` — 7 métodos mutadores.
- `sala_service.py` — 4 métodos mutadores.
- `franja_service.py` — 4 métodos mutadores.
- `restriccion_generacion_service.py` — 17 métodos mutadores (incluyendo
  `bloquear_franjas_docente` y `limpiar_disponibilidad_docente` sin
  `@requiere_escritura`).
- `horario_service.py` — 4 métodos mutadores.
- `infraestructura_service.py` — fachada pura de delegación, 0 llamadas
  directas al repo. Requiere solo la propagación de `auditoria_repo`.

---

R1: CADA MÉTODO MUTADOR de los cinco sub-servicios DEBE llamar a
    `auditar_cambio` conservando el estado anterior y el nuevo cuando aplique.

R2: LOS MÉTODOS QUE ELIMINAN deben capturar el estado anterior antes del
    `repo.eliminar_*` y registrar `AccionCambio.DELETE` con ese estado.

R3: LOS MÉTODOS QUE CREAN deben registrar `AccionCambio.CREATE` con la
    entidad resultante.

R4: LOS MÉTODOS QUE ACTUALIZAN (incluye `renombrar`, `activar`, `cambiar_estado`,
    `asignar_sala_a_grupo`) deben registrar `AccionCambio.UPDATE` con anterior
    y nuevo. El estado anterior se carga desde el repositorio antes de modificar.

R5: MÉTODOS CON `@requiere_escritura` Y MÉTODOS SIN ÉL que muten datos (e.g.,
    `bloquear_franjas_docente`, `limpiar_disponibilidad_docente`) DEBEN auditarse
    igualmente; `@requiere_escritura` no es criterio de auditoría.

R6: PARA OPERACIONES EN LOTE (e.g., `guardar_franjas`, `guardar_disponibilidad_docente`,
    `duplicar_config_generacion`, `duplicar_escenario`) un único `auditar_cambio`
    resumen es suficiente; no se genera una entrada por elemento.

R7: `InfraestructuraService` DEBE aceptar `auditoria_repo` en su constructor y
    pasarlo a los sub-servicios cuando los instancia en `_sala_service()`,
    `_franja_service()`, `_escenario_horario_service()` y
    `_restriccion_generacion_service()`. No se añaden llamadas a
    `auditar_cambio` en la fachada misma.

R8: `SERVICIOS_SIN_HUELLA_DEUDA` en `check_auditoria.py` DEBE reducirse en
    seis entradas al cerrar este paso: `infraestructura_service`,
    `restriccion_generacion_service`, `escenario_horario_service`,
    `sala_service`, `franja_service`, `horario_service`.

R9: UN TEST DE INTEGRACIÓN representativo de cada sub-servicio DEBE afirmar que
    `audit_log` crece con `usuario_id` e `institucion_id` no nulos tras la
    escritura.

## Criterio de done

- `python scripts/check_auditoria.py` no lista ninguno de los seis servicios
  como pendiente fuera de la deuda.
- `SERVICIOS_SIN_HUELLA_DEUDA` ya no contiene ninguna de las seis entradas.
- El test de integración de `obs_02` pasa verde con las entradas nuevas.
- `python scripts/init.py` completamente verde.
