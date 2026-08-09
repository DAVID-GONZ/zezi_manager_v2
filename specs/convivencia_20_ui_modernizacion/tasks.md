# convivencia_20_ui_modernizacion — Tasks

## Scope

Archivos a MODIFICAR (no crear archivos nuevos):
- `src/interface/pages/convivencia/observaciones.py`
- `src/interface/pages/convivencia/seguimiento.py`

## T1 — observaciones.py: Reemplazar ag-Grid + row-actions por config-list con acciones inline

- [ ] Eliminar el bloque `ui.aggrid(...)` y el bloque `.row-actions` debajo.
- [ ] Reemplazar con patrón `config-list` (`.config-list-header` + `.config-list-row` por observacion):
  - Columna nombre: `.config-col-name` con nombre del estudiante
  - Columna badge categoría: usar `_cargar_categorias()` para resolver el nombre, mostrarlo como `.badge .badge-info` (o el badge de convivencia adecuado si hay mapeo)
  - Columna badge visibilidad: `.badge .badge-success` para "Publica", `.badge .badge-neutral` para "Privada"
  - Columna texto: texto truncado, con tooltip o expand usando `ui.tooltip()` para ver `texto_completo`
  - Columna fecha: texto secondary
  - Columna acciones: `.config-col-actions` con los botones inline (toggle visibilidad, promover plantilla, promover comportamiento, eliminar) — misma logica actual pero como `btn_ghost`/`btn_danger` size="sm"
- [ ] Mantener el `empty_state()` cuando no hay filas.

## T2 — observaciones.py: Agregar filtro de categoria en toolbar

- [ ] En el `panel-toolbar` agregar un `ui.select` para filtro de categoría (opciones desde `_cargar_categorias()`, con opcion "Todas" = None).
- [ ] Cuando cambie, filtrar `_s["observaciones"]` por `categoria_id` (filtro client-side sobre la lista ya cargada, o re-llamar al servicio si acepta el param).
- [ ] El selector de estudiante del toolbar ya pre-llena el form de creacion (esto ya funciona via `_s["sel_estudiante_id"]`). Verificar que no se duplique en el form_dialog innecesariamente — el form_dialog DEBE seguir teniendo el selector de estudiante porque el usuario puede querer crear para otro.

## T3 — seguimiento.py: Layout dos columnas con auto-load 360

- [ ] Cambiar de layout vertical (3 panel-cards apilados) a `page-body` con:
  - `.page-col-main` (flex:3): panel de alertas con cards coloreadas
  - `.page-col-side` (flex:2): panel 360 que auto-carga
- [ ] Auto-carga: en `on_estudiante_change`, si hay estudiante Y periodo seleccionados, llamar `_ver_360()` automaticamente (sin boton manual). Mantener el boton como fallback por si quiere refrescar.

## T4 — seguimiento.py: Alertas como cards coloreadas en vez de ag-Grid

- [ ] Eliminar `ui.aggrid(...)` para alertas.
- [ ] Reemplazar con lista de `.alerta-item` coloreadas por severidad:
  - `.alerta-critica` para nivel "critica"
  - `.alerta-advertencia` para nivel "advertencia"
  - `.alerta-info` para nivel "info"
- [ ] Cada card muestra: fecha (`.text-xs-meta`), descripcion (`.alerta-item-text`), destinatario, estado con badge (`.badge-success` Resuelta / `.badge-warning` Pendiente).
- [ ] Mantener `empty_state()` cuando no hay alertas.

## T5 — seguimiento.py: Vista 360 mejorada

- [ ] En la columna lateral, mejorar la vista 360:
  - Stat cards arriba (nota comportamiento + promedio) — ya existen, solo verificar que esten.
  - Observaciones: en vez de `<ul>/<li>`, usar items con `.config-list-row` estilo, cada observacion como una fila con texto.
  - Alertas activas: usar `.alerta-item` con el badge de severidad.
- [ ] Si `resultado_360` es None, mostrar `empty_state` con texto guia.

## Verificacion

Despues de cada task:
```
python scripts/check_design.py --file src/interface/pages/convivencia/observaciones.py
python scripts/check_design.py --file src/interface/pages/convivencia/seguimiento.py
```

Al final:
```
python scripts/check_design.py --all
python scripts/sync_tokens.py --check
python init.py
```
