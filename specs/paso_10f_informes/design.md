# Design — paso_10f_informes

## Archivos y responsabilidades

### Scope ampliado (aprobado por David — Opción A)
```
src/services/informe_service.py          ← agregar métodos + re-exports
src/interface/pages/informes/__init__.py ← ya existe (vacío)
src/interface/pages/informes/consolidado_notas.py
src/interface/pages/informes/consolidado_asistencia.py
src/interface/pages/informes/boletin_periodo.py
src/interface/pages/informes/boletin_anual.py
src/interface/pages/informes/estadisticos.py
```

---

## InformeService — nuevos métodos

```python
def generar_boletin_periodo(
    self,
    estudiante_id: int,
    grupo_id: int,
    periodo_id: int,
    formato: str = "pdf",
) -> bytes:
    exporter = self._get_exporter_o_lanzar()
    # Obtener notas del grupo y filtrar por estudiante
    notas_grupo = self._estadisticos_repo.consolidado_notas_grupo(grupo_id, periodo_id)
    fila_notas  = next((r for r in notas_grupo if r["estudiante_id"] == estudiante_id), {})
    nombre      = fila_notas.get("nombre_completo", f"Estudiante {estudiante_id}")
    # Obtener asistencia del grupo y filtrar por estudiante
    asist_grupo = self._estadisticos_repo.consolidado_asistencia_grupo(grupo_id, periodo_id)
    filas_asist = [r for r in asist_grupo if r["estudiante_id"] == estudiante_id]
    # Combinar en tabla plana
    datos = []
    for r in filas_asist:
        asig = r["nombre_asignatura"]
        datos.append({
            "Asignatura":    asig,
            "Nota":          fila_notas.get(asig, "—"),
            "Asistencia %":  r.get("porcentaje", 0),
            "Faltas Inj.":   r.get("faltas_injustificadas", 0),
        })
    fmt = FormatoInforme(formato)
    if fmt == FormatoInforme.EXCEL:
        return exporter.exportar_excel(datos, nombre_hoja="Boletín Periodo")
    html = self._datos_a_html(datos, titulo=f"Boletín Periodo — {nombre}")
    return exporter.exportar_pdf(html)


def generar_boletin_anual(
    self,
    estudiante_id: int,
    grupo_id: int,
    anio_id: int,
    formato: str = "pdf",
) -> bytes:
    exporter   = self._get_exporter_o_lanzar()
    datos_anual = self._estadisticos_repo.consolidado_anual_grupo(grupo_id, anio_id)
    filas = [r for r in datos_anual if r.get("estudiante_id") == estudiante_id]
    if not filas:
        raise ValueError(f"Sin datos anuales para estudiante {estudiante_id} en grupo {grupo_id}.")
    nombre = filas[0].get("nombre_completo", f"Estudiante {estudiante_id}")
    fmt = FormatoInforme(formato)
    if fmt == FormatoInforme.EXCEL:
        return exporter.exportar_excel(filas, nombre_hoja="Boletín Anual")
    html = self._datos_a_html(filas, titulo=f"Boletín Anual — {nombre}")
    return exporter.exportar_pdf(html)
```

Re-exports al final de `informe_service.py`:
```python
__all__ = [
    "InformeService",
    "InformeNotasDTO",
    "InformeAsistenciaDTO",
    "FormatoInforme",
]
```

---

## Estructura de cada página (patrón canónico)

```python
@ui.page("/informes/<ruta>")
def <nombre>_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s: dict = { ... }   # estado mutable de la página

    @ui.refreshable
    def contenido() -> None:
        ...

    app_layout(
        titulo_pagina="...",
        icono_pagina=Icons.XXX,
        subtitulo_pagina="...",
        ctx=ctx,
        ruta_activa="/informes/...",
        contenido=contenido,
    )
```

---

## consolidado_notas.py

**Ruta:** `/informes/consolidado-notas`

**Estado:** `{"grupo_id": None, "asignacion_id": None, "periodo_id": None, "fecha_desde": None, "fecha_hasta": None, "formato": "excel"}`

**Flujo:**
1. Selección de grupo → recarga opciones de asignación y periodo.
2. "Generar" → construye `InformeNotasDTO(grupo_id=_s["grupo_id"], asignacion_id=_s["asignacion_id"], periodo_id=_s["periodo_id"], fecha_desde=_s["fecha_desde"], fecha_hasta=_s["fecha_hasta"], formato=_s["formato"])`.
3. Llama `Container.informe_service().generar_notas(dto)`.
4. `ui.download(content=bytes, filename=f"consolidado_notas_grupo{_s['grupo_id']}.{'xlsx' if _s['formato']=='excel' else 'pdf'}")`.
5. Errores: captura `ValueError` → `ui.notify(..., type="negative")`.

**Servicios:** `Container.informe_service()`, `Container.infraestructura_service().listar_grupos()`, `Container.asignacion_service().listar_con_info()`, `Container.periodo_service().listar_por_anio()`.

---

## consolidado_asistencia.py

**Ruta:** `/informes/consolidado-asistencia`

Idéntico a consolidado_notas pero usa `InformeAsistenciaDTO` y `generar_asistencia()`.

---

## boletin_periodo.py

**Ruta:** `/informes/boletin-periodo`

**Estado:** `{"grupo_id": None, "periodo_id": None, "estudiantes": [], "generando": False}`

**Flujo:**
1. Filtros: grupo + periodo → al cambiar grupo/periodo, recarga lista de estudiantes con `Container.estudiante_service().listar_por_grupo(grupo_id)`.
2. Por cada estudiante: botón "Descargar PDF" → `Container.informe_service().generar_boletin_periodo(est.id, grupo_id, periodo_id, "pdf")` → `ui.download()`.
3. Botón "Generar todos" → itera la lista, descarga cada uno.
4. Captura `ValueError` (NullExporter) → `ui.notify`.

---

## boletin_anual.py

**Ruta:** `/informes/boletin-anual`

Como boletin_periodo pero el segundo filtro es `anio` (desde `Container.periodo_service().listar_por_anio()` para obtener los años disponibles, o un select de año numérico), y llama `generar_boletin_anual(est.id, grupo_id, anio_id, "pdf")`.

---

## estadisticos.py

**Ruta:** `/informes/estadisticos`

**Módulo-level `_EC_*` constants (OBLIGATORIO — R11):**
```python
_EC_PIE_OPTIONS: dict = {
    "tooltip": {"trigger": "item"},
    "series": [{"type": "pie", "radius": "60%", "data": []}],
}
_EC_BAR_OPTIONS: dict = {
    "tooltip": {},
    "xAxis": {"type": "category", "data": []},
    "yAxis": {"type": "value"},
    "series": [{"type": "bar", "data": []}],
}
_EC_LINE_OPTIONS: dict = {
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": []},
    "yAxis": {"type": "value"},
    "series": [{"type": "line", "smooth": True, "data": []}],
}
```

**Flujo:**
1. Filtros: grupo, asignacion, periodo.
2. Al confirmar filtros → carga datos con `EstadisticosService`.
3. Para cada gráfica, copia el option base `_EC_*`, inyecta los datos, y renderiza con `ui.echart(options)`.
4. Renderiza también `ranking_grupo()` como tabla (`ui.aggrid` o lista simple).

**Servicios:** `Container.estadisticos_service()` — métodos `distribucion_desempenos`, `comparativo_periodos`, `ranking_grupo`, `tendencia_asistencia`.

---

## Alternativa descartada

**Opción B: multi-servicio directo en la UI para boletines.**  
La UI combinaría `EvaluacionService.obtener_planilla()` + `CierreService.get_cierre_periodo()` para construir el boletín sin pasar por InformeService. Descartada porque:
- Rompe el patrón canónico "filtros → servicio → bytes → download".
- La lógica de combinación terminaría duplicada en ambas páginas de boletín.
- InformeService ya tiene acceso al `_estadisticos_repo` correcto.
