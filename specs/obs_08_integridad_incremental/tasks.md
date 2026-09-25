# Tasks: Verificación incremental y agregados en SQL (obs_08)

- [x] T1: Añadir la tabla `verificacion_auditoria` (`tabla`, `ultimo_id`,
      `ultimo_hash`, `verificado_en`) al DDL de
      `src/infrastructure/db/schema.py`, con comentario explicando que es
      metadato operativo y que no participa en ninguna cadena.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k schema`
  Produce: `src/infrastructure/db/schema.py` modificado

- [x] T2: Añadir a `IAuditoriaRepository` los métodos **concretos** (no
      abstractos, R3) `contar_eventos(filtro) -> int`,
      `contar_cambios(filtro) -> int` y
      `resumen_eventos(desde, hasta=None, institucion_id="*") -> dict`, con
      defaults neutros (`0`, `0`, `{}`) y docstring del contrato. Cambiar
      `verificar_cadena_eventos` / `verificar_cadena_cambios` a
      `(self, *, completa: bool = False)`.
  Verifica: `python -m pytest tests/unit/domain/ -q -k auditoria_repo`
  Produce: `src/domain/ports/auditoria_repo.py` modificado

- [x] T3: Implementar `contar_eventos` y `contar_cambios` en
      `sqlite_auditoria_repo.py`, reutilizando la construcción de `WHERE` de
      `listar_eventos`/`listar_cambios` para que filtro y conteo no puedan
      divergir (extraer un `_where_eventos(filtro)` / `_where_cambios(filtro)`
      común que devuelva `(sql, params)`), e ignorando `pagina`/`por_pagina`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k auditoria`
  Produce: `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` modificado

- [x] T4: Test de contrato de los conteos: sembrar N filas, aplicar un filtro
      que seleccione M, y comprobar que `contar_*` devuelve M con independencia
      de `pagina` y `por_pagina`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k contar`
  Produce: test verde

- [x] T5: Implementar `resumen_eventos` en el repo SQLite con las tres
      consultas agregadas de §6 del diseño (conteo por tipo, logins de hoy,
      usuarios distintos), respetando el scope de institución.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k resumen_eventos`
  Produce: `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` modificado

- [x] T6: Reescribir `_verificar_cadena` en el repo SQLite: lectura por lotes
      de `_LOTE = 5000`, semilla desde el checkpoint, salida inmediata al
      primer eslabón roto **sin** avanzar el checkpoint (R10), y guardado del
      checkpoint solo al completar el recorrido sin roturas. Añadir
      `_hash_de(tabla, id)` y `_guardar_checkpoint(...)`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k cadena`
  Produce: `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` modificado

- [x] T7: Tests de la verificación incremental:
      (a) cadena íntegra → `None` y checkpoint avanzado;
      (b) alterar una fila **posterior** al checkpoint → devuelve su `id` y el
          checkpoint no se mueve;
      (c) alterar una fila **anterior** al checkpoint → la incremental pasa en
          verde y la completa (`completa=True`) la detecta. Este test
          documenta el compromiso de §2 del diseño; no es un bug.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k cadena`
  Produce: test verde

- [x] T8: Modificar `AuditoriaService.verificar_integridad(completa=False)`
      para propagar el modo y devolver el dict ampliado con `alcance`,
      `desde_id_eventos`, `desde_id_cambios` y `verificado_en` (§7).
  Verifica: `python -m pytest tests/unit/services/ -q -k integridad`
  Produce: `src/services/auditoria_service.py` modificado

- [x] T9: Reescribir `AuditoriaService.resumen_uso(dias, scope)` sobre
      `resumen_eventos`, sin recorrer eventos en Python y sin techo de 500
      (R4, R5). Ajustar `tests/unit/services/test_solo_lectura.py` al contrato
      nuevo.
  Verifica: `python -m pytest tests/unit/services/test_solo_lectura.py -q`
  Produce: `src/services/auditoria_service.py` y su test modificados

- [x] T10: Modificar `AuditoriaPresenter`: claves `"total_cambios"` y
      `"total_sesiones"` en `estado`, con sus setters, alimentadas desde
      `contar_*` en cada carga.
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k auditoria`
  Produce: `src/interface/presenters/admin/auditoria_presenter.py` modificado

- [x] T11: Modificar `src/interface/pages/admin/auditoria.py`: mostrar
      «N resultados» junto a los controles de paginación (R11); texto del badge
      de integridad distinguiendo incremental de completa con su rango y fecha
      (R9); segundo botón «Verificación completa» con aviso de duración.
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [x] T12: Modificar `_render_kpis_admin()` en `src/interface/pages/inicio.py`
      para consumir el `ResumenUsoDTO` nuevo, conservando el comportamiento
      fail-open.
  Verifica: `python -m pytest tests/unit/interface/ -q -k inicio`
  Produce: `src/interface/pages/inicio.py` modificado

- [x] T13: Crear `tests/unit/infrastructure/test_auditoria_volumen.py`: sembrar
      50 000 filas en `audit_log` con cadena válida; medir que la primera
      verificación completa termina y que la segunda (incremental, sin filas
      nuevas) responde por debajo del umbral declarado en el test. Marcarlo
      como test lento según los markers de `pyproject.toml`.
  Verifica: `python -m pytest tests/unit/infrastructure/test_auditoria_volumen.py -q`
  Produce: test verde

- [x] T14: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Con la base sembrada a ~50 000 filas: pulsar «Verificar integridad» → primera
  pasada completa; pulsarlo de nuevo → respuesta inmediata, y el badge dice
  desde qué identificador y con qué fecha.
- Alterar por SQL una fila posterior al checkpoint → la verificación la detecta
  y el badge pasa a «Alterada»; repetir la verificación no «limpia» el estado.
- `/admin/auditoria` muestra el total de resultados y cambia al cambiar de
  filtro.
- El dashboard de admin muestra KPIs que ya no se detienen en 500 eventos.
- `python scripts/init.py` completamente verde.
