# Tasks: Plantilla integrada y robusta en el generador (paso_16c_generador_plantilla_unificada)

> Requiere `paso_16a` y `paso_16b` en estado done.

- [ ] T1: Crear `src/interface/pages/academico/plantilla_editor_widget.py` con
          `render_plantilla_form`, `render_franjas_editor` y
          `render_plantilla_preview`, reutilizando el patrón de franjas de
          `plantillas_franja.py` y produciendo `filas` para `guardar_franjas`.
  Verifica: `python scripts/check_imports.py --layer interface`
  Produce: `src/interface/pages/academico/plantilla_editor_widget.py`

- [ ] T2: Design system en el widget nuevo (clases CSS, iconos vía ThemeManager).
  Verifica: `python scripts/check_design.py --file src/interface/pages/academico/plantilla_editor_widget.py`
  Produce: exit code 0

- [ ] T3: En `horario_generar.py`, introducir las tres pestañas
          (Plantillas / Configuraciones / Resultado) en `contenido_refreshable`
          y la clave `_s["tab"]`, conservando lista/detalle/resultado actuales en
          la pestaña Configuraciones/Resultado.
  Verifica: `python scripts/check_imports.py --layer interface`
  Produce: `src/interface/pages/academico/horario_generar.py`

- [ ] T4: Añadir la pestaña Plantillas: listar, crear (con editor de franjas),
          preview de rejilla, y borrado con guarda de "plantilla en uso" (R7).
  Verifica: `python scripts/check_design.py --file src/interface/pages/academico/horario_generar.py`
  Produce: exit code 0

- [ ] T5: En `_config_dialog`, permitir "elegir o crear plantilla" (R3) y
          deshabilitar «Generar horario» cuando la plantilla no sea generable
          (R5) mostrando el motivo.
  Verifica: `python scripts/check_design.py --file src/interface/pages/academico/horario_generar.py`
  Produce: exit code 0

- [ ] T6: Verificar entorno completo.
  Verifica: `python init.py`
  Produce: todos los checks verdes, sin regresiones de tests
