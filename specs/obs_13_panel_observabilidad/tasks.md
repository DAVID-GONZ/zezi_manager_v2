# Tasks: Panel de observabilidad de plataforma (obs_13)

- [ ] T1: Crear `src/domain/models/observabilidad.py` con `SaludDTO`
      (integridad, versión, uptime en segundos, tamaño de base en bytes,
      último backup `datetime | None`), `EntradaLogDTO`, `AlertaIPDTO`
      (ip, fallos, segundos restantes) y `PuntoUsoDTO` (fecha, logins,
      denegados). Heredan de `ZeciModel` / `DTODominio` como el resto.
  Verifica: `python -m pytest tests/unit/domain/ -q -k observabilidad`
  Produce: `src/domain/models/observabilidad.py`

- [ ] T2: Crear el puerto `src/domain/ports/log_reader.py` con `ILogReader`
      (`leer_ultimos`, `disponible`) y sus docstrings de contrato.
  Verifica: `python -c "from src.domain.ports.log_reader import ILogReader"`
  Produce: `src/domain/ports/log_reader.py`

- [ ] T3: Crear `src/infrastructure/logging/jsonl_log_reader.py` según §4 del
      diseño: lectura de cola con `_TOPE_BYTES`, descarte de la primera línea
      cuando hay `seek`, descarte silencioso de líneas ilegibles y filtrado
      contra `_CAMPOS_PERMITIDOS` (R8).
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k log_reader`
  Produce: `src/infrastructure/logging/jsonl_log_reader.py`

- [ ] T4: Tests del lector: archivo ausente → `[]` y `disponible() is False`;
      línea a medio escribir → se descarta sin excepción; archivo mayor que el
      tope → devuelve las últimas n y no carga el archivo entero; campo fuera
      de la whitelist → no aparece en la salida.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k log_reader`
  Produce: test verde

- [ ] T5: Añadir `alertas_activas()` a `src/domain/policies/alerta_ip.py`
      según §6, **sin mutar** `_estados`.
  Verifica: `python -m pytest tests/unit/ -q -k alerta_ip`
  Produce: `src/domain/policies/alerta_ip.py` modificado

- [ ] T6: Test de `alertas_activas()`: tras N fallos aparece la IP con su
      conteo; llamarla dos veces no altera el conteo ni la ventana; una
      entrada caducada no se lista y tampoco se borra.
  Verifica: `python -m pytest tests/unit/ -q -k alerta_ip`
  Produce: test verde

- [ ] T7: Capturar el instante de arranque en `main.py` y exponerlo de forma
      legible por el servicio, para calcular el uptime sin inferirlo del
      proceso ni de la fecha de ningún archivo.
  Verifica: `python -c "import main; print(main.INICIADO_EN)"` (o equivalente)
  Produce: `main.py` modificado

- [ ] T8: Crear `src/services/observabilidad_service.py` con `salud()`,
      `eventos_seguridad()`, `alertas_ip()` y `uso_diario(dias)`. `salud()`
      reutiliza `verify_db_integrity()` —el mismo criterio que `/health`, no
      uno paralelo— y devuelve `None` en el último backup cuando no hay
      ninguno (R3).
  Verifica: `python -m pytest tests/unit/services/ -q -k observabilidad`
  Produce: `src/services/observabilidad_service.py`

- [ ] T9: Implementar `uso_diario` como agregación SQL con
      `GROUP BY date(fecha_hora)` apoyada en lo que `obs_08` expone, sin
      recuento en Python (R12). Si hace falta, añadir el método al puerto de
      auditoría con default neutro.
  Verifica: `python -m pytest tests/unit/services/ -q -k uso_diario`
  Produce: servicio (y puerto/repo si aplica) modificados

- [ ] T10: Tests del servicio: base íntegra → salud OK; base corrupta →
      veredicto en rojo; log ausente → lista vacía con la marca de no
      disponible; `uso_diario` devuelve un punto por día de la ventana,
      incluidos los días sin actividad (con ceros).
  Verifica: `python -m pytest tests/unit/services/ -q -k observabilidad`
  Produce: test verde

- [ ] T11: Registrar `log_reader` y `observabilidad_service` en
      `container.py`, y añadirlos a la lista que recorre
      `Container.diagnostico()`.
  Verifica: `python -c "from container import Container; print(Container.diagnostico())"`
  Produce: `container.py` modificado

- [ ] T12: Crear
      `src/interface/presenters/admin/observabilidad_presenter.py` con el
      `estado` por bloque de §7 y sus transiciones. Sin NiceGUI, sin cálculos
      (R14).
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k observabilidad`
  Produce: `src/interface/presenters/admin/observabilidad_presenter.py`

- [ ] T13: Crear
      `tests/unit/interface/presenters/test_observabilidad_presenter.py` que
      importe y llame al presenter real: un bloque con error no borra los
      datos de los demás; los filtros de log se reflejan en el estado.
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k observabilidad`
  Produce: test verde

- [ ] T14: Crear `src/interface/pages/admin/observabilidad.py` como
      page-delegate con las cuatro secciones, cada una fail-open por separado
      (R13), reutilizando `stats_grid`, `data_table`, `alerts_panel`,
      `mini_chart` y `empty_state`. Sin clases ni CSS nuevos. Incluir el aviso
      de que las alertas de IP son del proceso actual (§6).
  Verifica: `python scripts/check_design.py --all && python scripts/audit_design.py`
  Produce: `src/interface/pages/admin/observabilidad.py`

- [ ] T15: Añadir el control de limpieza de alerta por IP, que llama a
      `alerta_ip.reset_ip(ip)` y **audita** la acción con el actor y la IP
      como `objetivo` (R11), usando el constructor único de eventos de
      `obs_06`.
  Verifica: limpiar una alerta → desaparece y aparece la fila en `auditoria`
  Produce: `src/interface/pages/admin/observabilidad.py` modificado

- [ ] T16: Registrar la ruta en `main.py`
      (`registrar_pagina("/admin/observabilidad", observabilidad_page,
      roles=_ADMIN)`), añadir la entrada al NAV de `layout.py` en la sección
      Administración, añadir la quinta tarjeta a `_ADMIN_CARDS` de
      `inicio.py`, y actualizar `ACCESO_ESPERADO` en
      `test_matriz_rutas_completa.py`.
  Verifica: `python -m pytest tests/unit/interface/auth/ -q`
  Produce: `main.py`, `layout.py`, `inicio.py` y el test modificados

- [ ] T17: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Abrir `/admin/observabilidad` como admin: salud, versión, uptime, tamaño de
  base y último backup («sin backup registrado» si no hay ninguno). Recargar →
  el uptime avanza.
- Corromper la base de pruebas → el bloque de salud pasa a rojo y coincide con
  el 503 de `/health`.
- Fallar el login cinco veces desde la misma IP → aparece la alerta con su
  conteo y su tiempo restante; limpiarla la retira y deja la fila de auditoría.
- Renombrar el archivo de log → esa sección muestra su estado vacío con la ruta
  configurada, y el resto de la página sigue funcionando.
- La serie de uso diario muestra un punto por día, incluidos los días vacíos.
- `/diagnostico` sigue existiendo, con su diagnóstico de Container y su «Ver
  como» intactos.
- `python scripts/init.py` completamente verde.
