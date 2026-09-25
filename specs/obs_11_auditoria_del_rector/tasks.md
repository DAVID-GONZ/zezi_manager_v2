# Tasks: Bitácora institucional para el equipo directivo (obs_11)

- [ ] T1: Cambiar la firma de `AuditoriaService.listar_cambios` y
      `listar_eventos_sesion` para que reciban `scope: TenantScope`
      **obligatorio** (sin default), y añadir el helper privado
      `_filtro_con_scope(filtro, scope)` de §2 del diseño, que fuerza
      `institucion_id` y apaga `sin_institucion` cuando el scope es un entero.
      Usar `model_copy(update=...)`, nunca `.dict()`.
  Verifica: `python -m pytest tests/unit/services/ -q -k auditoria`
  Produce: `src/services/auditoria_service.py` modificado

- [ ] T2: Actualizar los llamadores existentes:
      `src/interface/pages/admin/auditoria.py` pasa `scope="*"` explícito en
      `_cargar_cambios` y `_cargar_sesiones`. Buscar cualquier otro llamador y
      actualizarlo; el arranque debe fallar si queda alguno sin migrar.
  Verifica: `python scripts/init.py` (sin TypeError de arranque)
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T3: Añadir a `tests/unit/services/test_tenant_isolation.py` el test del
      **filtro hostil**: `listar_cambios(FiltroAuditoriaDTO(institucion_id=2),
      scope=1)` no devuelve ninguna fila de la institución 2. Añadir el
      equivalente para `listar_eventos_sesion`. Escribirlos antes del resto:
      deben fallar en rojo hasta que T1 esté completo.
  Verifica: `python -m pytest tests/unit/services/test_tenant_isolation.py -q`
  Produce: test verde

- [ ] T4: Ampliar `src/domain/policies/rbac_auditoria.py` con
      `puede_ver_bitacora_institucional(actor_rol)`: cierta para `director` y
      `coordinador`, falsa para el resto (el admin tiene su propia vista).
  Verifica: `python -m pytest tests/unit/domain/test_rbac_auditoria.py -q`
  Produce: `src/domain/policies/rbac_auditoria.py` modificado

- [ ] T5: Crear `src/interface/presenters/institucion/auditoria_presenter.py`
      con `AuditoriaInstitucionalPresenter` según §3: `institucion_id` privado
      por constructor, propiedad `scope` de solo lectura, y un `estado` que
      **no** contiene `institucion_id` ni `sin_institucion`. No hereda del
      presenter de admin.
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k institucional`
  Produce: `src/interface/presenters/institucion/auditoria_presenter.py`

- [ ] T6: Crear
      `tests/unit/interface/presenters/test_auditoria_institucional_presenter.py`
      que importe y llame al presenter real: `scope` devuelve la institución
      del constructor; `estado` no tiene las dos claves prohibidas;
      `construir_filtro()` nunca emite `institucion_id` distinto del scope.
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k institucional`
  Produce: test verde

- [ ] T7: Crear `src/interface/pages/institucion/auditoria.py` como
      page-delegate: comprueba sesión, corta con estado vacío si
      `ctx.institucion_id is None` (R12), y renderiza las dos pestañas con
      filtros de fecha, usuario, entidad, acción y tipo de evento, la
      paginación con total y el diálogo de detalle de `obs_09`. Sin filtro de
      institución, sin verificación de integridad, sin exportación.
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/pages/institucion/auditoria.py`

- [ ] T8: Usar el catálogo `tablas_auditables` para todos los encabezados y
      selectores de entidad de la página (R7): ningún nombre de tabla ni
      identificador interno visible al usuario.
  Verifica: revisión de la página — ningún literal de tabla física en textos
  Produce: `src/interface/pages/institucion/auditoria.py` modificado

- [ ] T9: Registrar la ruta en `main.py`:
      `registrar_pagina("/institucion/auditoria",
      auditoria_institucional_page, roles=_DIR_COORD)`, junto a las demás
      rutas de institución.
  Verifica: `python -m pytest tests/unit/interface/auth/ -q`
  Produce: `main.py` modificado

- [ ] T10: Actualizar `ACCESO_ESPERADO` en
      `tests/unit/interface/auth/test_matriz_rutas_completa.py` con la ruta
      nueva y sus roles (R10).
  Verifica: `python -m pytest tests/unit/interface/auth/test_matriz_rutas_completa.py -q`
  Produce: test verde

- [ ] T11: Añadir la entrada «Auditoría» al NAV de
      `src/interface/design/layout.py` en la sección de Dirección, derivando la
      visibilidad del registro central de rutas (R9). Si el coordinador no debe
      ver el resto de entradas del bloque, crear un bloque propio en vez de
      ensanchar el existente.
  Verifica: entrar como director y como coordinador → la entrada aparece; como profesor → no
  Produce: `src/interface/design/layout.py` modificado

- [ ] T12: Añadir el caso de ruta a `tests/e2e/test_matriz_rbac.py` si la suite
      cubre navegación por rol.
  Verifica: `python -m pytest tests/e2e/test_matriz_rbac.py -q`
  Produce: test verde o constancia de que la suite no aplica

- [ ] T13: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Como director: `/institucion/auditoria` muestra cambios y sesiones de la
  propia institución, con detalle y diff, y sin filtro de institución ni botón
  de integridad.
- Como coordinador: mismo acceso.
- Como profesor: navegar a la URL produce el aviso de acceso no autorizado y la
  vuelta a `/inicio`.
- Sembrar cambios en dos instituciones y entrar como director de la primera →
  ninguna fila de la segunda, tampoco forzando el filtro desde el DOM.
- Una sesión sin `institucion_id` ve el estado vacío explicativo, no una tabla
  con datos de todos.
- `python scripts/init.py` completamente verde.
