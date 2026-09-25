# Tasks: Historial de cambios en la ficha de negocio (obs_10)

- [ ] T1: Crear `src/domain/policies/rbac_auditoria.py` con
      `puede_ver_historial(actor_rol)` y `_ROLES_AUDITORES`, siguiendo el
      contrato de `rbac_usuarios.py` (acepta string o enum, normaliza a
      minúsculas).
  Verifica: `python -m pytest tests/unit/domain/ -q -k rbac_auditoria`
  Produce: `src/domain/policies/rbac_auditoria.py`

- [ ] T2: Crear `tests/unit/domain/test_rbac_auditoria.py`: admin, director y
      coordinador → `True`; profesor, estudiante, apoderado, `None` y cadena
      vacía → `False`; acepta tanto `Rol.DIRECTOR` como `"director"`.
  Verifica: `python -m pytest tests/unit/domain/test_rbac_auditoria.py -q`
  Produce: test verde

- [ ] T3: Implementar `AuditoriaService.historial_de(tabla, registro_id, scope)`
      según §3 del diseño, reutilizando `_componer_detalle` y
      `resolver_actores` de `obs_09`. Incluye las filas con `institucion_id`
      nulo; excluye las de otra institución cuando `scope != "*"`.
  Verifica: `python -m pytest tests/unit/services/ -q -k historial`
  Produce: `src/services/auditoria_service.py` modificado

- [ ] T4: Crear el test de `historial_de`: orden cronológico ascendente; un
      director con `scope=1` no recibe cambios de la institución 2; las filas
      sin institución sí se incluyen; registro sin cambios → lista vacía.
  Verifica: `python -m pytest tests/unit/services/ -q -k historial`
  Produce: test verde

- [ ] T5: Crear `src/interface/presenters/admin/historial_presenter.py` con el
      `estado` y las transiciones de §5 (`abrir`, `cerrar`, `set_items`,
      `set_error`). Sin NiceGUI, sin reglas de negocio (R12).
  Verifica: `python -m pytest tests/unit/interface/presenters/ -q -k historial`
  Produce: `src/interface/presenters/admin/historial_presenter.py`

- [ ] T6: Crear `tests/unit/interface/presenters/test_historial_presenter.py`
      que importe y llame al presenter real: abrir fija tabla/registro y
      `cargando=True`; `set_items` lo apaga; `cerrar` limpia el estado.
  Verifica: `python -m pytest tests/unit/interface/presenters/test_historial_presenter.py -q`
  Produce: test verde

- [ ] T7: Crear `src/interface/design/components/historial_cambios.py` con el
      dataclass `HistorialItem` y la función `historial_cambios(items)`:
      presentación pura, `section_panel` como contenedor, `empty_state` cuando
      la lista está vacía (R8). Sin `Container`, sin servicios (R6).
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/design/components/historial_cambios.py`

- [ ] T8: Si el componente necesitó clases propias, añadirlas a
      `src/interface/design/styles/CLASS_CONTRACT.md` y su CSS a
      `src/interface/design/styles/components/historial.css`, usando solo
      tokens y sin ningún selector de framework (regla N).
  Verifica: `python scripts/check_design.py --all && python scripts/sync_tokens.py --check && python scripts/audit_design.py`
  Produce: contrato y CSS actualizados, o ningún cambio si se reutilizó todo

- [ ] T9: Registrar el componente en
      `src/interface/design/components/__init__.py` siguiendo la convención de
      exportación de los componentes existentes.
  Verifica: `python -c "from src.interface.design.components import historial_cambios"`
  Produce: `__init__.py` modificado

- [ ] T10: Enganchar el historial en
      `src/interface/pages/convivencia/observaciones.py`: control `btn_icon`
      gateado por `puede_ver_historial(ctx.usuario_rol)`, carga perezosa al
      pulsar (R11). **Verificar el nombre de tabla** contra el argumento
      `tabla=` de `auditar_cambio` en `convivencia_service.py`.
  Verifica: abrir una observación como coordinador → el historial lista sus ediciones
  Produce: `src/interface/pages/convivencia/observaciones.py` modificado

- [ ] T11: Enganchar el historial en
      `src/interface/pages/evaluacion/planilla_notas.py`, verificando el
      nombre de tabla contra `evaluacion_service.py`.
  Verifica: editar una nota y abrir su historial → aparece la edición
  Produce: `src/interface/pages/evaluacion/planilla_notas.py` modificado

- [ ] T12: Enganchar el historial en
      `src/interface/pages/academico/estudiantes.py`, verificando el nombre de
      tabla contra `estudiante_service.py`.
  Verifica: editar un estudiante y abrir su historial
  Produce: `src/interface/pages/academico/estudiantes.py` modificado

- [ ] T13: Enganchar el historial en `src/interface/pages/admin/usuarios.py`,
      verificando el nombre de tabla contra `usuario_service.py`. Comprobar
      que los campos sensibles llegan ocultos (garantía de `obs_09`).
  Verifica: resetear una contraseña y abrir el historial → el campo va oculto
  Produce: `src/interface/pages/admin/usuarios.py` modificado

- [ ] T14: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Como coordinador: abrir una observación editada dos veces → el historial
  muestra tres entradas (creación y dos ediciones) en orden cronológico, cada
  una con fecha, actor y los campos que cambiaron.
- Como profesor: el control de historial no aparece en ninguna de las cuatro
  fichas.
- Como director de la institución 1: el historial de un registro de la
  institución 2 no devuelve nada.
- Un registro sin huella muestra el estado vacío explicativo, no una lista
  en blanco.
- Abrir una ficha sin pulsar «Historial» no genera consultas a `audit_log`
  (comprobar con el log de SQL o instrumentando el repo temporalmente).
- `python scripts/init.py` completamente verde, `audit_design.py` incluido.
