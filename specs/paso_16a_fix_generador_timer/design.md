# Diseño: Reparar la ejecución del generador (paso_16a_fix_generador_timer)

## 0. Causa raíz (diagnóstico técnico)

En `src/interface/pages/academico/horario_generar.py:98` se precrea un
temporizador de un solo disparo **inactivo**:

```python
_generar_config_timer = ui.timer(0.1, lambda: None, active=False, once=True)
```

Según `nicegui/timer.py`, un `once=True` lanza su única corrutina `_run_once()`
en el momento de construirse. Esa corrutina: duerme `interval` (0.1 s), comprueba
`if self.active and not self._should_stop()`, y como `active` es `False` **no
invoca el callback** y entra en `finally: self._cleanup()`, que pone
`callback = None` y **termina la corrutina para siempre**.

Cuando el usuario pulsa «Generar horario» segundos/minutos después,
`_generar_config()` hace `timer.callback = _trabajo` y `timer.active = True`, pero
ya no hay ninguna corrutina viva observando esos atributos → `_trabajo()` nunca
se ejecuta. Visiblemente: el spinner «Generando horario…» se queda fijo y el
motor jamás corre.

## 1. Archivos a modificar

- `src/interface/pages/academico/horario_generar.py` — eliminar el temporizador
  pre-creado y programar el trabajo diferido con un temporizador creado en el
  momento del clic.

**No se crean archivos nuevos. No se toca ningún servicio, modelo ni el
`parrilla_widget.py`.**

## 2. Métodos de Container a usar (sin cambios)

- `Container.generador_horario_service().generar(config.id, crear_escenario=True, optimizar=True)`
  → `ResultadoGeneracionDTO` (atributos `valido`, `escenario_id`, `total_requeridos`,
  `colocados`, `no_colocados`, `incidencias`, `metricas`).
- `Container.horario_service().datos_parrilla(escenario_id)` → dict de parrilla
  para la vista previa.

## 3. Cambio concreto

**Eliminar** la línea 98:

```python
_generar_config_timer = ui.timer(0.1, lambda: None, active=False, once=True)
```

**Reescribir** el final de `_generar_config()` para crear un temporizador fresco
en cada clic (un `once=True` recién construido sí arranca su corrutina, porque
nace `active=True`):

```python
def _generar_config() -> None:
    config = _s.get("config_sel")
    if not config or getattr(config, "id", None) is None:
        toast_warning("Selecciona una configuración para generar")
        return
    if _s["generando"]:
        return  # ya hay una corrida en curso
    _s["generando"] = True
    contenido_refreshable.refresh()

    def _trabajo() -> None:
        try:
            resultado = Container.generador_horario_service().generar(
                config.id, crear_escenario=True, optimizar=True,
            )
            _s["resultado"] = resultado
            _s["eje_sel"] = None
            _cargar_configs()
            _cargar_preview()
            if getattr(resultado, "valido", False):
                toast_success("Generación completada")
            else:
                toast_warning("Generación parcial: revisa las incidencias")
        except Exception as exc:
            logger.error("Error ejecutando generador: %s", exc)
            toast_error("Error al generar el horario")
        finally:
            _s["generando"] = False
            contenido_refreshable.refresh()

    # Temporizador de un disparo creado AHORA: su corrutina nace activa y
    # ejecutará _trabajo() tras pintar el spinner.
    ui.timer(0.1, _trabajo, once=True)
```

El patrón "refrescar para pintar el spinner → diferir 0.1 s → ejecutar el trabajo
pesado → refrescar con el resultado" se conserva; lo único que cambia es **dónde**
se crea el temporizador (en el clic, no al construir la página).

## 4. Refreshables y handlers — orden de definición

Sin cambios estructurales. `contenido_refreshable` ya está definida con
`@ui.refreshable` y se referencia desde `_trabajo` mediante cierre, igual que hoy.
El handler `_generar_config` permanece donde está; solo se reescribe su cuerpo.

## 5. Integración con el servicio

Idéntica a la actual (R1–R6 ya cubiertos por `generar()` y `datos_parrilla()`).
La protección `if _s["generando"]: return` cubre R6 evitando corridas solapadas.

## 6. Alternativa descartada

Convertir `horario_generar_page` y `_generar_config` en handlers `async` y usar
`await ui.run.io_bound(...)` para no bloquear el event loop. Se descarta en este
paso por minimizar el alcance: el objetivo es restaurar el comportamiento ya
diseñado (spinner + trabajo diferido) con la corrección puntual del temporizador.
La opción async queda como mejora futura si la generación resulta pesada.

## 7. Manejo de errores

```python
try:
    resultado = Container.generador_horario_service().generar(...)
    ...
    toast_success(...) / toast_warning(...)
except Exception as exc:           # error inesperado del motor
    logger.error("Error ejecutando generador: %s", exc)
    toast_error("Error al generar el horario")
finally:
    _s["generando"] = False        # SIEMPRE se limpia el estado de carga
    contenido_refreshable.refresh()
```

El `finally` garantiza R5: pase lo que pase, el indicador de carga se apaga.
