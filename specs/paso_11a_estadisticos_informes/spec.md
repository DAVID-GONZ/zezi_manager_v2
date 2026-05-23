# Spec — paso_11a_estadisticos_informes

## Módulo: Estadísticos e Informes exportables (`/informes/estadisticos`)
**Versión:** 1.0 — 2026-05-21  
**Roles:** `director`, `coordinador`, `profesor`  
**Notación:** EARS (Event-Action-Response System)

---

## Contexto y motivación

La página actual (`estadisticos.py`) muestra 3 gráficas fijas con filtros básicos
(grupo, asignación, periodo) y no tiene ninguna capacidad de exportación. La
infraestructura de exportación ya existe en `InformeService` y `EstadisticosService`
pero no está expuesta en la UI.

El objetivo de este paso es **rediseñar completamente** la página para convertirla
en el centro unificado de generación de informes exportables, con gráficas de
preview y descarga en xlsx o PDF.

---

## Arquitectura de la página

```
/informes/estadisticos
├── [Panel de configuración]          ← siempre visible arriba
│   ├── Selector: Tipo de Informe     ← primer selector, determina el resto
│   ├── Selectores dinámicos          ← varían según el Tipo seleccionado
│   └── Botón "Previsualizar"
│
├── [Panel de preview]                ← se muestra tras Previsualizar
│   ├── Gráfica ECharts (si aplica)
│   ├── Tabla resumen (ag-Grid o HTML)
│   └── Contador de filas
│
└── [Panel de exportación]            ← activo solo cuando hay datos en preview
    ├── Botón "Descargar Excel (.xlsx)"
    └── Botón "Descargar PDF"         ← solo si el tipo admite PDF
```

---

## Catálogo de tipos de informe

| ID | Nombre en UI | Filtros requeridos | Preview | Excel | PDF |
|---|---|---|---|---|---|
| `consolidado_notas` | Consolidado de Notas | grupo + periodo | Tabla ag-Grid | ✅ | ✅ |
| `consolidado_asistencia` | Consolidado de Asistencia | grupo + periodo | Tabla ag-Grid | ✅ | ✅ |
| `ranking_grupo` | Ranking del Grupo | grupo + periodo | Tabla ag-Grid | ✅ | ✅ |
| `distribucion_desempenos` | Distribución de Desempeños | grupo + asignatura + periodo | Donut ECharts | ✅ | ❌ |
| `comparativo_periodos` | Comparativo por Periodos | grupo + asignatura | Line ECharts | ✅ | ❌ |
| `promedios_area` | Promedios por Área | grupo + periodo | Bar ECharts | ✅ | ❌ |
| `tendencia_asistencia` | Tendencia de Asistencia | grupo + asignatura + periodo | Line ECharts | ✅ | ❌ |
| `estados_asistencia` | Estados de Asistencia | grupo + asignatura + periodo | Pie ECharts | ✅ | ❌ |
| `consolidado_anual` | Consolidado Anual | grupo | Tabla ag-Grid | ✅ | ✅ |

---

## Requisitos funcionales

### Panel de configuración

**R1** WHEN la página carga, THE SYSTEM SHALL renderizar el panel de configuración
con el selector `Tipo de Informe` pre-poblado con los 9 tipos del catálogo,
sin valor seleccionado. Los demás selectores NO se muestran hasta elegir el tipo.

**R2** WHEN el usuario selecciona un `Tipo de Informe`, THE SYSTEM SHALL:
- Ocultar todos los selectores anteriores (si había selección previa).
- Mostrar únicamente los selectores requeridos por ese tipo (ver catálogo).
- Limpiar los valores de los selectores y el panel de preview.

**R3** Selectores dinámicos — comportamiento por campo:

| Campo | Poblar con | Dependencia |
|---|---|---|
| Grupo | `Container.infraestructura_service().listar_grupos()` | Independiente |
| Asignatura | `Container.asignacion_service().listar_con_info(FiltroAsignacionesDTO(grupo_id=...))` | Requiere Grupo |
| Periodo | `Container.periodo_service().listar_por_anio(ctx.anio_id)` | Independiente |

**R4** WHEN el usuario cambia el valor de `Grupo`, THE SYSTEM SHALL recargar el
selector de `Asignatura` con las asignaciones del nuevo grupo y limpiar el valor
actual de Asignatura.

**R5** WHEN todos los filtros requeridos por el tipo seleccionado tienen valor,
THE SYSTEM SHALL habilitar el botón "Previsualizar". IF algún filtro requerido
falta, THE SYSTEM SHALL mantener el botón deshabilitado.

**R6** WHEN el usuario hace clic en "Previsualizar" con todos los filtros válidos,
THE SYSTEM SHALL llamar al método de servicio correspondiente al tipo de informe,
guardar los datos en `_s["datos"]` y refrescar el panel de preview y el panel
de exportación.

**R7** IF una llamada de servicio en R6 falla con excepción, THE SYSTEM SHALL
mostrar `ui.notify` de error con el mensaje exacto y dejar el panel de preview
vacío con un estado `tablero-empty`.

---

### Panel de preview

**R8** IF `_s["datos"]` está vacío o `None`, THE SYSTEM SHALL mostrar el estado
vacío con el texto "Selecciona un tipo de informe y haz clic en Previsualizar".

**R9** IF `_s["datos"]` tiene filas pero la lista está vacía, THE SYSTEM SHALL
mostrar el estado vacío con el texto "Sin datos para los filtros seleccionados".

**R10** WHEN los datos están disponibles, THE SYSTEM SHALL renderizar la vista
correspondiente al tipo de informe activo:

| Tipo | Vista de preview |
|---|---|
| `consolidado_notas` | `ui.aggrid` con columnas: Estudiante, una col por asignatura, Promedio Periodo |
| `consolidado_asistencia` | `ui.aggrid` con columnas: Estudiante, Asignatura, P, FJ, FI, R, E, % |
| `ranking_grupo` | `ui.aggrid` con columnas: #, Estudiante, Promedio; badge de desempeño en Promedio |
| `distribucion_desempenos` | `ui.echart` tipo donut con colores de `_NIVEL_COLORES` |
| `comparativo_periodos` | `ui.echart` tipo línea con periodos en X y promedio en Y |
| `promedios_area` | `ui.echart` tipo barras horizontales, área en Y, promedio en X |
| `tendencia_asistencia` | `ui.echart` tipo línea con semanas en X y % en Y, markLine en 70% |
| `estados_asistencia` | `ui.echart` tipo pie/donut con colores de `AsistenciaColors` (tokens.py) |
| `consolidado_anual` | `ui.aggrid` con columnas: Estudiante, nota por periodo, Definitiva, Estado |

**R11** Todos los options dicts de ECharts deben declararse como constantes de
módulo con prefijo `_EC_` (nunca dentro de funciones). Para personalizar con datos
usar `copy.deepcopy(_EC_*)`.

**R12** Todos los colores ECharts deben provenir de `tokens.py` (`Colors`,
`AsistenciaColors`, `DesempenoColors`). No usar strings de color literales
fuera del bloque `_EC_*` al inicio del módulo.

**R13** THE SYSTEM SHALL mostrar debajo de la gráfica/tabla un texto:
`f"Vista previa: {n} filas"` (o `f"Vista previa: {n} registros"` para gráficas).

---

### Panel de exportación

**R14** WHEN hay datos en el panel de preview, THE SYSTEM SHALL mostrar el panel
de exportación con los botones activos del catálogo (Excel siempre; PDF solo si
el tipo lo admite).

**R15** WHEN el usuario hace clic en "Descargar Excel (.xlsx)", THE SYSTEM SHALL:
1. Llamar al método de exportación correspondiente de `InformeService` o construir
   el dict de datos para pasar a `IExporterService.exportar_excel()`.
2. Llamar a `ui.download(bytes_contenido, filename)` donde `filename` sigue el
   patrón `{tipo}_{grupo}_{periodo}_{AAAAMMDD}.xlsx`.
3. IF la generación falla, mostrar `ui.notify` de error.

**R16** WHEN el usuario hace clic en "Descargar PDF", THE SYSTEM SHALL:
1. Llamar al método de exportación PDF de `InformeService`.
2. Llamar a `ui.download(bytes_contenido, filename)` con extensión `.pdf`.
3. IF la generación falla, mostrar `ui.notify` de error.

**R17** Los botones de exportación deben mantenerse habilitados mientras el
usuario no cambie los filtros. IF el usuario cambia cualquier filtro después de
previsualizar, THE SYSTEM SHALL ocultar el panel de exportación y limpiar
`_s["datos"]` hasta que se vuelva a hacer clic en "Previsualizar".

---

### Mapeo tipo → método de servicio (datos)

| Tipo | Método de datos | Parámetros |
|---|---|---|
| `consolidado_notas` | `EstadisticosService.consolidado_notas_grupo(grupo_id, periodo_id)` | grupo, periodo |
| `consolidado_asistencia` | `EstadisticosService.consolidado_asistencia_grupo(grupo_id, periodo_id)` | grupo, periodo |
| `ranking_grupo` | `EstadisticosService.ranking_grupo(grupo_id, periodo_id)` | grupo, periodo |
| `distribucion_desempenos` | `EstadisticosService.distribucion_desempenos(grupo_id, asignacion_id, periodo_id, anio_id=ctx.anio_id)` | grupo, asignatura, periodo |
| `comparativo_periodos` | `EstadisticosService.comparativo_periodos(grupo_id, asignacion_id, anio_id=ctx.anio_id)` | grupo, asignatura |
| `promedios_area` | `EstadisticosService.promedios_por_area(grupo_id, periodo_id)` | grupo, periodo |
| `tendencia_asistencia` | `EstadisticosService.tendencia_asistencia(grupo_id, asignacion_id, periodo_id)` | grupo, asignatura, periodo |
| `estados_asistencia` | `EstadisticosService.distribucion_estados_asistencia(grupo_id, asignacion_id, periodo_id)` | grupo, asignatura, periodo |
| `consolidado_anual` | `EstadisticosService.consolidado_anual_grupo(grupo_id, anio_id=ctx.anio_id)` | grupo |

### Mapeo tipo → método de exportación

| Tipo | Excel | PDF |
|---|---|---|
| `consolidado_notas` | `InformeService.generar_notas(InformeNotasDTO(grupo_id, periodo_id, formato=EXCEL))` | ídem con `formato=PDF` |
| `consolidado_asistencia` | `InformeService.generar_asistencia(InformeAsistenciaDTO(grupo_id, periodo_id, formato=EXCEL))` | ídem con `formato=PDF` |
| `ranking_grupo` | `IExporterService.exportar_excel(datos_ranking, nombre_hoja="Ranking")` | `IExporterService.exportar_pdf(html_generado)` |
| `distribucion_desempenos` | `IExporterService.exportar_excel(datos_dist)` | — |
| `comparativo_periodos` | `IExporterService.exportar_excel(datos_comp)` | — |
| `promedios_area` | `IExporterService.exportar_excel(datos_area)` | — |
| `tendencia_asistencia` | `IExporterService.exportar_excel(datos_tend)` | — |
| `estados_asistencia` | `IExporterService.exportar_excel([{"estado": k, "cantidad": v} for k,v in datos_est.items()])` | — |
| `consolidado_anual` | `InformeService.generar_consolidado_anual(grupo_id, anio_id, formato=EXCEL)` | ídem con `formato=PDF` |

Para acceder a `IExporterService` directamente: `Container.informe_service()._get_exporter_o_lanzar()`.
Si el exportador no está configurado, `generar_*` lanza `ValueError` — capturar y notificar con R7/R16.

---

### Reglas de rol

**R18** WHEN `ctx.usuario_rol == "profesor"`, THE SYSTEM SHALL pre-seleccionar
el grupo del contexto en el selector Grupo y no permitir cambiarlo (campo readonly).
Solo podrá cambiar la asignatura y el periodo.

**R19** WHEN `ctx.usuario_rol in ["coordinador", "director"]`, todos los selectores
son libremente modificables.

**R20** Los tipos `consolidado_anual` y `consolidado_notas` son visibles para
todos los roles. Los tipos de asistencia son visibles para todos. No hay tipos
exclusivos de director en esta página.

---

### Reglas de estilo (arquitectura)

**R21** La página usa ÚNICAMENTE clases CSS de `styles.css`. Está prohibido
`style=""` con valores estáticos en cualquier elemento.

**R22** La capa de datos está completamente en `EstadisticosService` e
`InformeService`. La página NO importa `src.domain.models.*` ni repositorios.
Solo importa desde `container`, `src.interface.context`, `src.interface.design`
y `src.services` (DTOs).

**R23** El estado de la página se gestiona con un dict mutable `_s` (patrón
existente en el proyecto). Estructura inicial:

```python
def _estado_inicial() -> dict:
    return {
        "tipo":          None,          # str | None
        "grupo_id":      None,          # int | None
        "asignacion_id": None,          # int | None
        "periodo_id":    None,          # int | None
        "grupos":        [],
        "asignaciones":  [],
        "periodos":      [],
        "datos":         None,          # list | dict | None
        "datos_listos":  False,
    }
```

**R24** Los tres `@ui.refreshable` son:
- `filtros_refreshable()` — panel de configuración completo
- `preview_refreshable()` — panel de preview
- `export_refreshable()` — panel de exportación

---

## Layout CSS y clases a usar

| Elemento | Clase CSS |
|---|---|
| Wrapper de página | `page-stack` |
| Panel de configuración | `panel-card` |
| Encabezado del panel | `panel-header` + `panel-title` |
| Grid de selectores | `form-grid-3` o `form-grid-2` según tipo |
| Panel de preview | `panel-card` |
| Gráficas ECharts medianas | `echart-md` |
| Gráficas ECharts grandes | `echart-lg` |
| Estado vacío | `tablero-empty` + `tablero-empty-hint` |
| Panel de exportación | `panel-card` |
| Texto de conteo | clase utilitaria `text-secondary` |

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/interface/pages/informes/estadisticos.py` | Reescritura completa |
| `src/interface/design/layout.py` | *(Ya hecho)* Rename "Estadísticos" → "Tablero" en NAV_ITEMS top-level |

No se requieren cambios en servicios, repositorios ni estilos CSS para este paso.

---

## Tests de aceptación

**T1** La página carga sin error con usuario autenticado.

**T2** Al seleccionar "Consolidado de Notas" aparecen exactamente los selectores
Grupo y Periodo. No aparece Asignatura.

**T3** Al seleccionar "Distribución de Desempeños" aparecen Grupo, Asignatura y
Periodo. La Asignatura está vacía hasta elegir Grupo. Al elegir Grupo, Asignatura
se popula con las asignaciones del grupo.

**T4** Con filtros incompletos el botón "Previsualizar" está deshabilitado.

**T5** Con filtros completos y "Previsualizar" clickeado, aparece la gráfica/tabla
de preview y el texto de conteo de filas.

**T6** El botón "Descargar Excel" llama a `ui.download()` con un archivo `.xlsx`.

**T7** El botón "Descargar PDF" solo aparece para los tipos que admiten PDF
(consolidado_notas, consolidado_asistencia, ranking_grupo, consolidado_anual).

**T8** Al cambiar cualquier filtro tras previsualizar, el panel de exportación
desaparece y los datos se limpian.

**T9** Si el servicio de exportación no está configurado, el clic en Descargar
muestra `ui.notify` de error con el mensaje de la excepción.

**T10** Con `usuario_rol == "profesor"`, el selector de Grupo muestra el grupo
del contexto y está deshabilitado (readonly).

**T11** Con datos vacíos del servicio, el panel de preview muestra el estado
vacío con mensaje "Sin datos para los filtros seleccionados".

---

## Notas de implementación

- `ui.download()` en NiceGUI acepta `bytes` directamente: `ui.download(content_bytes, filename)`.
- El `IExporterService` está disponible vía `Container.informe_service()._get_exporter_o_lanzar()`.
- `InformeNotasDTO` y `InformeAsistenciaDTO` se importan desde `src.domain.models.dtos` — excepción
  permitida para DTOs de capa de interfaz (son structs sin lógica).
- Para el `consolidado_anual`, el `anio_id` viene de `ctx.anio_id`.
- Para los tipos que no tienen método generar_* en `InformeService`, construir el dict de datos
  y pasar directamente a `exporter.exportar_excel(datos, nombre_hoja=...)`.

---

*Spec listo para revisión y aprobación antes de implementar.*
