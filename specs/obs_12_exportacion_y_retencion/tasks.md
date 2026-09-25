# Tasks: Exportación verificable y retención de la bitácora (obs_12)

- [ ] T1: Añadir a `src/domain/models/auditoria.py`: `HojaVerificacionDTO` y
      `ResultadoArchivadoDTO` según §2 y §4 del diseño, y los valores
      `AUDITORIA_EXPORTADA` y `AUDITORIA_PURGADA` en `TipoEventoSesion`.
      Ampliar el `CHECK` de `tipo_evento` en `src/infrastructure/db/schema.py`
      con esos dos valores.
  Verifica: `python -m pytest tests/unit/domain/ -q -k auditoria`
  Produce: `src/domain/models/auditoria.py` y `src/infrastructure/db/schema.py` modificados

- [ ] T2: Añadir al puerto `IAuditoriaRepository` y al repo SQLite:
      `rango_de(tabla, filtro) -> tuple[int, int] | None` (ids extremos del
      tramo) y `listar_cambios_tramo(id_desde, id_hasta, scope)` como
      iterador por lotes, para no materializar el tramo completo en memoria.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k tramo`
  Produce: puerto y repo modificados

- [ ] T3: Crear `src/services/auditoria_export_service.py` con
      `exportar(tabla, filtro, scope, formato, actor)`: delimita el tramo,
      verifica su cadena, serializa reutilizando `diff_cambio` de `obs_09`
      (R6), compone la `HojaVerificacionDTO` y delega en `IExporterService`
      (`exportar_csv` / `exportar_pdf`).
  Verifica: `python -m pytest tests/unit/services/ -q -k export`
  Produce: `src/services/auditoria_export_service.py`

- [ ] T4: Implementar el tope de filas (R7): antes de exportar, `contar_*` de
      `obs_08`; si supera `settings.AUDITORIA_EXPORT_MAX_FILAS` (default
      50 000), lanzar `ReglaDeNegocioError` con código estable. Añadir el
      ajuste a `config.py` y a `.env.example`.
  Verifica: `python -m pytest tests/unit/services/ -q -k export_tope`
  Produce: servicio, `config.py` y `.env.example` modificados

- [ ] T5: Emitir el evento `AUDITORIA_EXPORTADA` al completar una exportación,
      con actor, rango, formato y número de filas (R5), usando el constructor
      único de eventos de `obs_06`.
  Verifica: exportar y consultar `auditoria` → aparece la fila del evento
  Produce: `src/services/auditoria_export_service.py` modificado

- [ ] T6: Crear los tests del servicio de exportación: la hoja lleva los dos
      `hash_cadena` extremos y el hash del contenido; un campo sensible no
      aparece en el CSV; con la cadena rota la exportación se produce y
      `integridad_ok` es `False` (R4); superar el tope lanza el error.
  Verifica: `python -m pytest tests/unit/services/ -q -k export`
  Produce: test verde

- [ ] T7: Escribir `docs/verificacion_bitacora.md`: procedimiento paso a paso,
      ejecutable por un tercero sin la aplicación, para recomputar
      `hash_contenido` y reconstruir la cadena del tramo partiendo de
      `hash_primera_fila`, con la forma canónica exacta del payload
      (claves ordenadas, separadores `(",", ":")`, sin `id`).
  Verifica: un lector ajeno puede seguirlo sin abrir el código
  Produce: `docs/verificacion_bitacora.md`

- [ ] T8: Crear el test que **ejecuta** el procedimiento documentado: exporta
      un tramo, recomputa la cadena siguiendo literalmente `docs/
      verificacion_bitacora.md` y confronta con la hoja. Si el documento y el
      código divergen, este test lo detecta.
  Verifica: `python -m pytest tests/unit/services/ -q -k verificacion_tramo`
  Produce: test verde

- [ ] T9: Añadir `eliminar_hasta(tabla, id_hasta, scope) -> int` al puerto y al
      repo SQLite, documentando en el docstring del puerto que el invariante
      append-only se mantiene: no hay `UPDATE`, y el único `DELETE` admisible
      es el del archivado, que deja constancia.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k eliminar_hasta`
  Produce: puerto y repo modificados

- [ ] T10: Crear `src/services/auditoria_retencion_service.py` con
      `archivar_y_purgar(...)` en los seis pasos de §4, abortando sin borrar
      ante cualquier fallo previo al paso 5, y reanclando el checkpoint de
      `obs_08` a `(k, hash_de_k)` (R11).
  Verifica: `python -m pytest tests/unit/services/ -q -k retencion`
  Produce: `src/services/auditoria_retencion_service.py`

- [ ] T11: Tests del servicio de retención: (a) si la escritura del archivo
      falla, no se borra ninguna fila; (b) si el hash releído no cuadra, no se
      borra ninguna fila; (c) tras una purga correcta, la verificación
      incremental sigue en verde y el evento `AUDITORIA_PURGADA` contiene
      ruta, hash, rango y número de filas.
  Verifica: `python -m pytest tests/unit/services/ -q -k retencion`
  Produce: test verde

- [ ] T12: Añadir `retencion_auditoria_meses: int | None` a las preferencias
      por institución (default 60, `None` = sin purga). La preferencia solo
      precarga la fecha propuesta; no dispara nada por sí sola.
  Verifica: `python -m pytest tests/unit/services/ -q -k preferencias`
  Produce: `src/services/preferencias_institucion_service.py` y su modelo modificados

- [ ] T13: Ampliar `src/domain/policies/rbac_auditoria.py` con
      `puede_exportar_bitacora` (admin, director, coordinador) y
      `puede_purgar_bitacora` (solo admin, R13), con sus tests.
  Verifica: `python -m pytest tests/unit/domain/test_rbac_auditoria.py -q`
  Produce: política y test modificados

- [ ] T14: Registrar `auditoria_export_service` y `auditoria_retencion_service`
      en `container.py`, y añadirlos a la lista de `Container.diagnostico()`.
  Verifica: `python -c "from container import Container; print(Container.diagnostico())"`
  Produce: `container.py` modificado

- [ ] T15: Añadir los controles a `src/interface/pages/admin/auditoria.py`:
      «Exportar» (CSV / PDF) y «Archivar y purgar» con `confirm_dialog` que
      muestre fecha de corte, filas afectadas y ruta destino antes de ejecutar
      (R12). Ambos gateados por la política.
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/pages/admin/auditoria.py` modificado

- [ ] T16: Añadir «Exportar» —y solo eso— a
      `src/interface/pages/institucion/auditoria.py`, respetando el scope del
      director.
  Verifica: exportar como director → el archivo solo contiene su institución
  Produce: `src/interface/pages/institucion/auditoria.py` modificado

- [ ] T17: Recrear la base (el `CHECK` cambió) y verificar el entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Exportar un rango a CSV como director → el archivo trae la hoja de
  verificación con los dos hashes extremos, el hash del contenido y el
  veredicto; los datos son solo de su institución.
- Seguir `docs/verificacion_bitacora.md` a mano sobre ese archivo → la cadena
  recomputada coincide.
- Alterar una fila por SQL y volver a exportar → la hoja dice `integridad_ok:
  false` y señala el `id` roto, y la exportación se produce igualmente.
- Intentar exportar un filtro de más de 50 000 filas → aviso claro, sin archivo
  truncado.
- Como admin: archivar y purgar un tramo antiguo → el archivo existe, su hash
  cuadra, las filas desaparecen, el evento `AUDITORIA_PURGADA` las explica y
  «Verificar integridad» sigue en verde.
- Como director: el control de purga no aparece.
- `python scripts/init.py` completamente verde.
