# Requirements — paso_10f_informes
## Páginas: informes y boletines (5 páginas)

Notación EARS. Todos los requisitos asumen usuario autenticado (guard activo).

---

### R1 — Guard universal
WHEN a user navigates to any `/informes/*` route WITHOUT an active session,  
the system SHALL redirect to `/login`.

---

### R2 — consolidado_notas: formulario de filtros
WHEN user is on `/informes/consolidado-notas`,  
the system SHALL display a filter form with: grupo (select), asignacion (select — filtered by grupo), periodo (select — filtered by grupo), fecha_desde (date), fecha_hasta (date), formato (Excel | PDF).

### R3 — consolidado_notas: descarga
WHEN user submits the filter form on `/informes/consolidado-notas`,  
the system SHALL call `InformeService.generar_notas(InformeNotasDTO)` and trigger `ui.download()` with the returned bytes.

---

### R4 — consolidado_asistencia: formulario de filtros
WHEN user is on `/informes/consolidado-asistencia`,  
the system SHALL display the same filter structure as R2.

### R5 — consolidado_asistencia: descarga
WHEN user submits the form on `/informes/consolidado-asistencia`,  
the system SHALL call `InformeService.generar_asistencia(InformeAsistenciaDTO)` and trigger `ui.download()`.

---

### R6 — boletin_periodo: lista de estudiantes
WHEN user is on `/informes/boletin-periodo` with grupo and periodo selected,  
the system SHALL list all active students of the group, each with an individual download button.

### R7 — boletin_periodo: descarga individual
WHEN user clicks the download button for a student on `/informes/boletin-periodo`,  
the system SHALL call `InformeService.generar_boletin_periodo(estudiante_id, grupo_id, periodo_id, "pdf")` and trigger `ui.download()`.

### R8 — boletin_periodo: generación masiva
WHEN user clicks "Generar todos" on `/informes/boletin-periodo`,  
the system SHALL generate individual PDFs for each student sequentially, downloading each one.

---

### R9 — boletin_anual: misma lógica, scope anual
WHEN user is on `/informes/boletin-anual`,  
the system SHALL work identically to R6–R8 but use `InformeService.generar_boletin_anual(estudiante_id, grupo_id, anio_id, "pdf")`.

---

### R10 — estadisticos: gráficas ECharts
WHEN user is on `/informes/estadisticos` with grupo, asignacion y periodo seleccionados,  
the system SHALL render at minimum these 3 gráficas con datos de `EstadisticosService`:
  - Distribución de desempeños (pie/bar) — `distribucion_desempenos()`
  - Comparativo entre periodos (line) — `comparativo_periodos()`
  - Ranking del grupo (bar horizontal) — `ranking_grupo()`

### R11 — estadisticos: ECharts vars
ALL ECharts option dicts on `/informes/estadisticos` SHALL be defined as module-level constants prefixed `_EC_` (e.g. `_EC_PIE_OPTIONS`, `_EC_LINE_OPTIONS`). No ECharts dict literals inside function bodies.

---

### R12 — NullExporter error claro
WHEN `InformeService.generar_*()` raises `ValueError` due to missing exporter (NullExporter),  
the system SHALL display `ui.notify("Exportador no disponible …", type="negative")` and SHALL NOT crash.

### R13 — Sin imports de dominio
NO page in `src/interface/pages/informes/` SHALL import from `src.domain.*`.  
DTOs e inputs se pasan como primitivos (int, str, date); las páginas importan DTOs desde `src.services.informe_service`.

---

### R14 — Extensión de InformeService (Opción A aprobada)
`InformeService` SHALL expose two new public methods:

```
generar_boletin_periodo(
    estudiante_id: int,
    grupo_id: int,
    periodo_id: int,
    formato: str = "pdf",   # Pydantic coerciona → FormatoInforme
) -> bytes
```

```
generar_boletin_anual(
    estudiante_id: int,
    grupo_id: int,
    anio_id: int,
    formato: str = "pdf",
) -> bytes
```

Both methods SHALL use `_estadisticos_repo.consolidado_notas_grupo()`,  
`_estadisticos_repo.consolidado_asistencia_grupo()` / `_estadisticos_repo.consolidado_anual_grupo()`,  
filter by `estudiante_id`, and export via `_get_exporter_o_lanzar()`.

### R15 — Re-exports desde informe_service
`src/services/informe_service.py` SHALL re-export `InformeNotasDTO`, `InformeAsistenciaDTO`, `FormatoInforme`  
so interface pages can import them without touching `src.domain.*`.
