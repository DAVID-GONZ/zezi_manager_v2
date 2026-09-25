# Tasks: Denegaciones con actor y clasificación por severidad (obs_07)

- [ ] T1: Diagnóstico P1 — instrumentar temporalmente
      `solo_lectura.verificar_escritura` y el guard de `contexto_tenant` para
      volcar el contexto y el stack al denegar; reproducir una denegación desde
      la UI con sesión activa; anotar por qué `actor_actual()` es `None`.
      Retirar la instrumentación al terminar.
  Verifica: `progress/diagnostico_obs_07.md` contiene la traza y la conclusión
  Produce: sección P1 de `progress/diagnostico_obs_07.md`

- [ ] T2: Diagnóstico P2 — sustituir temporalmente los `except Exception: pass`
      de `pagina_logout`, `_auditar_ver_como` y el emisor de `route_guard` por
      `logger.exception`; ejecutar logout y un ciclo completo de «Ver como»;
      anotar si hay excepción tragada o si el camino no se ejecuta.
  Verifica: `progress/diagnostico_obs_07.md` contiene la causa de las 0 filas
  Produce: sección P2 de `progress/diagnostico_obs_07.md`

- [ ] T3: Diagnóstico P3 — correlacionar por `fecha_hora` las 379 denegaciones
      cross-tenant con los logins y con `audit_log` para identificar la sesión
      y la pantalla de origen. Concluir de forma explícita: flujo legítimo mal
      enfocado, o acceso cruzado real. Si es lo segundo, **parar y reportar a
      David** (R9): no se arregla aquí.
  Verifica: `progress/diagnostico_obs_07.md` nombra el flujo de origen
  Produce: sección P3 de `progress/diagnostico_obs_07.md`

- [ ] T4: Crear `src/domain/policies/severidad_evento.py` con las constantes de
      motivo y la función pura `severidad_de(tipo_evento, motivo=None)` según
      §3 del diseño. Solo stdlib y modelos de dominio.
  Verifica: `python -m pytest tests/unit/domain/ -q -k severidad`
  Produce: `src/domain/policies/severidad_evento.py`

- [ ] T5: Crear `tests/unit/domain/test_severidad_evento.py`: denegación por
      solo lectura → `ADVERTENCIA`; denegación por rol → `ADVERTENCIA`;
      denegación cross-tenant → `CRITICA`; motivo desconocido → `CRITICA`
      (falla hacia el lado seguro); login exitoso → `INFO`.
  Verifica: `python -m pytest tests/unit/domain/test_severidad_evento.py -q`
  Produce: test verde

- [ ] T6: Aplicar el arreglo de `ContextVar` que T1 haya identificado, en
      `src/interface/context/event_context.py` y/o
      `src/interface/context/session_context.py`. El alcance exacto depende del
      diagnóstico; si exigiera tocar archivos fuera del scope del paso, **parar
      y reportar a David**.
  Verifica: provocar una denegación con sesión activa → la fila lleva `usuario_id`
  Produce: archivo(s) de contexto modificados

- [ ] T7: Modificar los emisores para que pasen el motivo y deriven la
      severidad: `src/services/solo_lectura.py` (`MOTIVO_SOLO_LECTURA`),
      `src/services/contexto_tenant.py` (`MOTIVO_CROSS_TENANT`),
      `src/interface/auth/route_guard.py` (`MOTIVO_ROL`).
  Verifica: `python -m pytest tests/unit/services/ -q -k "solo_lectura or tenant"`
  Produce: tres archivos modificados

- [ ] T8: Sustituir los `except Exception: pass` que rodean la escritura de
      auditoría por `except Exception as exc: logger.warning(...)` en
      `main.py` (`pagina_logout`), `session_context._auditar_ver_como`,
      `solo_lectura.py` y `contexto_tenant.py` (R5). La auditoría sigue sin
      bloquear la operación.
  Verifica: `python -m pytest tests/unit/ -q -k "logout or ver_como"`
  Produce: cuatro archivos modificados

- [ ] T9: Modificar `src/interface/context/eventos_sesion.py` para que
      `construir_evento` reciba `motivo: str | None` y derive la severidad con
      `severidad_de(...)`, en vez de aceptar la severidad ya calculada.
  Verifica: `python -m pytest tests/unit/interface/context/ -q`
  Produce: `src/interface/context/eventos_sesion.py` modificado

- [ ] T10: Añadir `severidad` a `FiltroAuditoriaDTO`
      (`src/domain/models/auditoria.py`) y su cláusula `WHERE severidad = ?` en
      `listar_eventos` de `sqlite_auditoria_repo.py`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k auditoria`
  Produce: dos archivos modificados

- [ ] T11: Modificar `AuditoriaPresenter`: clave `"severidad": None` en
      `estado`, método `set_severidad(valor)` y campo en `construir_filtro()`.
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k auditoria`
  Produce: `src/interface/presenters/admin/auditoria_presenter.py` modificado

- [ ] T12: Modificar `src/interface/pages/admin/auditoria.py`: `filter_select`
      de severidad en la pestaña Sesiones y columna de badge por fila con las
      variantes `neutral`/`warning`/`error` de `status_badge`. Sin CSS nuevo.
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T13: Modificar `AuditoriaService.resumen_uso` para contar como accesos
      denegados solo los de severidad `CRITICA` (R7), y ajustar
      `tests/unit/services/test_solo_lectura.py::test_resumen_uso_agrega_logins_y_denegados`
      al criterio nuevo.
  Verifica: `python -m pytest tests/unit/services/test_solo_lectura.py -q`
  Produce: `src/services/auditoria_service.py` y su test modificados

- [ ] T14: Crear el test de regresión de R8: con actor activo en el contexto,
      una denegación de escritura y una cross-tenant producen eventos con
      `usuario_id` no nulo y con la severidad esperada.
  Verifica: `python -m pytest tests/unit/services/ -q -k denegacion`
  Produce: test verde

- [ ] T15: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Leer `progress/diagnostico_obs_07.md`: las tres preguntas tienen respuesta con
  evidencia, no hipótesis.
- Con sesión de admin, iniciar «Ver como» y pulsar un botón de guardado → la
  fila nueva de `auditoria` lleva username, `usuario_id`, IP y
  `severidad = 'ADVERTENCIA'`.
- Provocar un acceso cross-tenant → fila con `severidad = 'CRITICA'`.
- Cerrar sesión → aparece la fila `LOGOUT` (hoy hay cero).
- En `/admin/auditoria`, pestaña Sesiones: filtrar por `CRITICA` deja fuera las
  denegaciones esperadas; cada fila muestra su badge de color.
- El KPI «Accesos denegados (7 d)» del dashboard de admin ya no cuenta las
  denegaciones esperadas.
- `python scripts/init.py` completamente verde.
