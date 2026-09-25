# Tasks: Detalle del cambio, diff y filtros legibles (obs_09)

- [ ] T1: Crear `src/domain/tablas_auditables.py` con `ETIQUETAS_TABLA` y
      `etiqueta_de_tabla(tabla)` con fallback al nombre físico (R5). Poblar el
      catálogo con las tablas que aparecen como argumento `tabla=` en las
      llamadas a `auditar_cambio` de los 23 servicios.
  Verifica: `python -m pytest tests/unit/domain/test_tablas_auditables.py -q`
  Produce: `src/domain/tablas_auditables.py`

- [ ] T2: Crear `tests/unit/domain/test_tablas_auditables.py`: toda clave del
      catálogo existe como tabla en `schema.py`; una tabla desconocida devuelve
      su nombre físico. El test protege contra entradas muertas, no exige
      exhaustividad.
  Verifica: `python -m pytest tests/unit/domain/test_tablas_auditables.py -q`
  Produce: test verde

- [ ] T3: Añadir a `src/domain/models/auditoria.py`: enum `TipoCambioCampo`,
      DTOs `CampoDiffDTO` y `DetalleCambioDTO`, y los campos
      `registro_id: int | None` y `sin_institucion: bool = False` en
      `FiltroAuditoriaDTO`.
  Verifica: `python -m pytest tests/unit/domain/ -q -k auditoria`
  Produce: `src/domain/models/auditoria.py` modificado

- [ ] T4: Implementar `AuditoriaService.diff_cambio(cambio,
      incluir_sin_cambio=False)` según §2 del diseño, con la lista negra
      `_CAMPOS_SENSIBLES` y el marcado `oculto=True` (R3).
  Verifica: `python -m pytest tests/unit/services/test_auditoria_diff.py -q`
  Produce: `src/services/auditoria_service.py` modificado

- [ ] T5: Crear `tests/unit/services/test_auditoria_diff.py`: CREATE → todo
      añadido; DELETE → todo eliminado; UPDATE con un campo cambiado y dos
      iguales → un solo campo devuelto; `password_hash` presente → `oculto=True`
      y ambos valores `None`; JSON malformado → lista vacía sin excepción.
  Verifica: `python -m pytest tests/unit/services/test_auditoria_diff.py -q`
  Produce: test verde

- [ ] T6: Implementar `AuditoriaService.detalle_cambio(cambio_id)` que consuma
      `repo.get_cambio()` —hoy sin consumidores— y componga el
      `DetalleCambioDTO` con diff, etiqueta de tabla y nombre del actor.
      Devuelve `None` si el cambio no existe.
  Verifica: `python -m pytest tests/unit/services/ -q -k detalle_cambio`
  Produce: `src/services/auditoria_service.py` modificado

- [ ] T7: Implementar `AuditoriaService.resolver_actores(cambios)` con una sola
      consulta (R8). Si el repositorio de usuarios no expone un método de
      lectura por conjunto de ids, añadir `get_varios(ids)` al puerto
      `usuario_repo` y su implementación SQLite. Prohibido resolver por fila.
  Verifica: `python -m pytest tests/unit/services/ -q -k resolver_actores`
  Produce: `src/services/auditoria_service.py` (+ puerto y repo de usuario) modificados

- [ ] T8: Añadir los filtros `registro_id` y `sin_institucion` al `WHERE` de
      `listar_cambios` y `listar_eventos` en `sqlite_auditoria_repo.py`, con la
      exclusión mutua de §6. Propagarlos al `_where_*` común que introdujo
      `obs_08` para que conteo y listado no diverjan.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k auditoria`
  Produce: `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` modificado

- [ ] T9: Test del filtro `sin_institucion`: con filas de institución 1, de
      institución 2 y con `institucion_id IS NULL`, cada modo del filtro
      devuelve exactamente su subconjunto.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k institucion`
  Produce: test verde

- [ ] T10: Modificar `AuditoriaPresenter`: claves `registro_id`,
      `sin_institucion`, `detalle` y `actores` en `estado`; métodos
      `set_registro`, `abrir_detalle`, `cerrar_detalle`, `set_actores`;
      `set_institucion` reconoce el centinela «sin institución»;
      `construir_filtro()` propaga los dos filtros nuevos. El presenter no
      calcula diff ni etiquetas (R13).
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k auditoria`
  Produce: `src/interface/presenters/admin/auditoria_presenter.py` modificado

- [ ] T11: Ampliar el test del presenter (`tests/unit/interface/presenters/`)
      para los filtros y transiciones nuevos. El test importa y llama al
      presenter real; no reimplementa su lógica.
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k auditoria`
  Produce: test verde

- [ ] T12: Modificar `src/interface/pages/admin/auditoria.py`: sustituir el
      `filter_input` de tabla por un `filter_select` alimentado por
      `ETIQUETAS_TABLA` (R10); añadir el filtro de `registro_id` (R11) y la
      opción «Sin institución» (R12); cambiar la columna «Usuario ID» por
      «Usuario» con el nombre resuelto y la cascada de fallback de R9.
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T13: Añadir el diálogo de detalle en la misma página: la fila de la
      pestaña Cambios es activable (también por teclado, patrón `_activable` de
      `inicio.py`) y abre un `custom_dialog` de solo lectura con la cabecera de
      identidad y la rejilla del diff, usando las variantes de badge
      `success`/`info`/`error`. Sin acciones de escritura (R7).
  Verifica: `python scripts/check_design.py --all && python scripts/audit_design.py`
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T14: Si el diálogo requiere clases nuevas, añadirlas a
      `src/interface/design/styles/CLASS_CONTRACT.md` y su CSS a
      `styles/components/`, con tokens (nada de hex ni px literales) y sin
      tocar `styles/adapter/`.
  Verifica: `python scripts/check_design.py --all && python scripts/sync_tokens.py --check`
  Produce: contrato y CSS actualizados, o ningún cambio si se reutilizó todo

- [ ] T15: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Editar una observación y abrir `/admin/auditoria` → la fila del cambio se
  puede activar con el ratón y con el teclado, y el diálogo muestra qué campos
  cambiaron con su valor antes y después.
- Resetear la contraseña de un usuario → el campo sensible aparece como
  «oculto», sin valor en ninguno de los dos lados.
- El filtro de tabla es un desplegable con etiquetas en español.
- Filtrar por `registro_id` deja solo los cambios de esa entidad.
- «Sin institución» muestra filas que antes desaparecían al filtrar por tenant.
- La columna de actor muestra nombres; un usuario borrado muestra su username.
- `python scripts/init.py` completamente verde.
