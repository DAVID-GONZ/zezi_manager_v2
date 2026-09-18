# Requisitos: Huella en convivencia y asistencia (obs_04a)

> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §2.
> **Depende de:** `obs_01_huella_actor` (helper `auditar_cambio` disponible) y
> `obs_02_puerta_huella` (la puerta que mide este paso).
> **Habilita:** `obs_05_admin_auditoria_ui` — con volumen real de huella la
> paginación tiene sentido.

## Estado actual (2026-09-09)

`convivencia_service` tiene 24 métodos mutadores y **cero** llamadas a
`auditar_cambio`. `asistencia_service` tiene 3 mutadores y cero. `alerta_service`
tiene 5 mutadores (configurar, desactivar configuración, resolver, resolver
masivo, detectar riesgo) y cero. Es decir: todas las observaciones, registros de
comportamiento y controles de asistencia —material de Ley 1620 y posicionamiento
comercial del producto— mutan hoy sin dejar constancia de quién editó qué.

---

R1: CADA MÉTODO MUTADOR de `ConvivenciaService`, `AsistenciaService` y
    `AlertaService` DEBE llamar a `auditar_cambio` conservando el estado
    anterior y el nuevo cuando aplique.

R2: LOS MÉTODOS QUE ELIMINAN deben capturar el estado anterior antes del
    `repo.eliminar_*` y registrar `AccionCambio.DELETE` con ese estado.

R3: LOS MÉTODOS QUE CREAN deben registrar `AccionCambio.CREATE` con el DTO o
    entidad resultante. El estado anterior es None.

R4: LOS MÉTODOS QUE ACTUALIZAN (incluye desactivar y notificar) deben cargar
    el estado previo del repositorio antes de modificar y registrar
    `AccionCambio.UPDATE` con anterior y nuevo.

R5: MÉTODOS DELEGADORES (e.g., `agregar_seguimiento` que delega en
    `agregar_entrada_seguimiento`, `guardar_asistencia_masiva` que delega en
    `registrar_masivo`) NO duplican `auditar_cambio`; la huella la genera el
    método destino.

R6: `auditar_cambio` NUNCA PROPAGA excepciones (ya garantizado en obs_01).
    Ningún método mutador debe protegerse contra fallo del helper con try/except
    extra.

R7: EL CONSTRUCTOR de cada uno de los tres servicios DEBE aceptar un parámetro
    `auditoria_repo: IAuditoriaRepository | None = None` (compat retro con
    scripts/tests sin wiring) y pasarlo al helper.

R8: `SERVICIOS_SIN_HUELLA_DEUDA` en `check_auditoria.py` DEBE reducirse en
    exactamente tres entradas al cerrar este paso:
    `convivencia_service`, `asistencia_service`, `alerta_service`.

R9: UN TEST DE INTEGRACIÓN representativo de cada servicio cubierto DEBE
    afirmar que `audit_log` crece con `usuario_id` e `institucion_id` no nulos
    tras la escritura.

## Criterio de done

- `python scripts/check_auditoria.py` no lista ningún método de los tres
  servicios como pendiente fuera de la deuda.
- `SERVICIOS_SIN_HUELLA_DEUDA` ya no contiene `convivencia_service`,
  `asistencia_service` ni `alerta_service`.
- El test de integración de `obs_02` (`test_huella_cobertura.py`) pasa verde con
  las nuevas entradas de los tres servicios.
- `python scripts/init.py` completamente verde.
