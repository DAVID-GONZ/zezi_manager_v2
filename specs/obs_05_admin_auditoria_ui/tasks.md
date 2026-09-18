# Tasks: Auditoría en admin — filtro institución, paginación y KPIs (obs_05)

- [ ] T1: Modificar `AuditoriaPresenter.__init__` para añadir las claves nuevas al
      estado: `"institucion_id": None`, `"hay_siguiente_cambios": False`,
      `"hay_siguiente_sesiones": False`.
      Añadir el método `set_institucion(valor)` que asigna
      `self.estado["institucion_id"] = self.a_int(valor)`.
      Modificar `construir_filtro()` para incluir
      `institucion_id=self.estado["institucion_id"]`.
  Verifica: `python -m pytest tests/unit/ -q -k auditoria_presenter`
  Produce: `src/interface/presenters/admin/auditoria_presenter.py` modificado

- [ ] T2: En `auditoria.py`:
      (a) Cambiar `_POR_PAGINA = 100` a `_POR_PAGINA = 50`.
      (b) Reescribir `_cargar_cambios()` y `_cargar_sesiones()` con la
          estrategia look-ahead: solicitar `_POR_PAGINA + 1` registros,
          actualizar `presenter.estado["hay_siguiente_*"]`, truncar a
          `_POR_PAGINA` antes de llamar a `presenter.set_cambios()`/
          `presenter.set_sesiones()`.
  Verifica: `python scripts/init.py` (sin errores de import)
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T3: En `auditoria.py`, añadir la función `_ir_pagina(nueva, tab)` y
      los controles Anterior / Siguiente al final del bloque renderizable de
      `tabla_cambios()` y `tabla_sesiones()`, condicionados a `pagina > 1 or
      hay_siguiente`.
  Verifica: abrir `/admin/auditoria` en un entorno con >50 registros en
      `audit_log` → el botón "Siguiente" aparece y la página 2 carga
      correctamente. Con < 50 registros los controles no se muestran.
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T4: En `auditoria.py`, añadir el filtro de institución en
      `_render_filtros_comunes()`. Cargar la lista de instituciones vía
      `Container.institucion_service().listar()` dentro de un `try/except`.
      El `filter_select` solo se renderiza cuando `ctx.usuario_rol == "admin"`.
      Al cambiar la selección, llamar a `presenter.set_institucion(e.value)`
      y a `_on_filtros_cambio()`.
  Verifica: como admin, seleccionar una institución → solo aparecen cambios
      de ese tenant. Seleccionar "Todas las instituciones" (None) → vuelven
      todos los registros.
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T5: En `inicio.py`, añadir la función privada `_render_kpis_admin()` que
      llama a `Container.auditoria_service().resumen_uso(dias=7)` y renderiza
      los tres KPIs con `stats_grid([...])`. Envolver en
      `contextlib.suppress(Exception)` (R7).
      En `contenido()`, insertar `_render_kpis_admin()` ANTES del bucle
      `for c in _ADMIN_CARDS` en la rama `rol == "admin"`.
  Verifica: abrir `/` como admin → se muestran tres stats antes de las cuatro
      tarjetas de navegación. Si el servicio de auditoría falla, la página
      carga sin esa sección (fail-open).
  Produce: `src/interface/pages/inicio.py` modificado

- [ ] T6: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Iniciar sesión como admin y abrir `/` → ver las tres stats de uso (logins
  hoy, usuarios activos 7 d, accesos denegados 7 d) antes de las tarjetas.
- Abrir `/admin/auditoria` → confirmar que el filtro "Institución" aparece
  en la barra de filtros comunes. Elegir una institución → la tabla de cambios
  muestra solo registros de ese tenant.
- Generar más de 50 cambios (ejecutar obs_04a o poblar la base con seeds) y
  recargar `/admin/auditoria` → el botón "Siguiente" aparece y carga la
  página 2; "Anterior" vuelve a la página 1.
- Cambiar cualquier filtro → la paginación vuelve a la página 1 (reset_pagina).
- `python scripts/init.py` completamente verde.
