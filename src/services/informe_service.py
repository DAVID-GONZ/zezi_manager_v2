"""
InformeService
===============
Orquesta la generación y exportación de informes académicos.

Coordina el repositorio de estadísticos (obtención de datos) con el
IExporterService (conversión al formato de salida). No contiene lógica
de presentación ni accede directamente a la BD.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.ports.service_ports import IExporterService
from src.domain.models.dtos import (
    FormatoInforme,
    InformeAsistenciaDTO,
    InformeNotasDTO,
)


# ── Sanitización de datos para exportación ───────────────────────────────────

# Campos que nunca deben aparecer en un documento exportado
_CAMPOS_EXCLUIR: frozenset[str] = frozenset({
    "estudiante_id",
    # Los flags *_perdio del consolidado anual son internos
})

# Renombre de claves de sistema a nombres semánticos en español
_CAMPO_RENOMBRAR: dict[str, str] = {
    "nombre_completo":       "Estudiante",
    "documento":             "Documento",
    "nombre_asignatura":     "Asignatura",
    "promedio_periodo":      "Promedio",
    "promedio":              "Promedio",
    "posicion":              "#",
    "presentes":             "Presentes",
    "faltas_injustificadas": "F. Injustificadas",
    "faltas_justificadas":   "F. Justificadas",
    "retrasos":              "Retrasos",
    "excusas":               "Excusas",
    "porcentaje":            "% Asistencia",
    "estado_promocion":      "Estado",
    "definitiva":            "Definitiva",
    "area_nombre":           "Área",
    "total_asignaturas":     "Asignaturas",
}


@dataclass
class BoletinesGrupoDTO:
    """Resultado de la generación masiva de boletines de un grupo."""
    contenido: bytes | None = None              # PDF/Excel fusionado (None si nada)
    errores: list[str] = field(default_factory=list)   # nombres con fallo


def sanitizar_datos_exportacion(datos: list[dict]) -> list[dict]:
    """
    Prepara datos brutos del repositorio para exportación (Excel / PDF):

    - Elimina ``estudiante_id`` y cualquier columna que termine en ``_perdio``
      (flags internos del consolidado anual).
    - Renombra claves de sistema a nombres semánticos en español usando
      ``_CAMPO_RENOMBRAR``.  Las claves sin mapeo se conservan tal cual
      (típicamente son nombres de asignaturas ya legibles).

    Se aplica solo al exportar; las vistas ag-Grid del navegador usan los
    nombres originales (``field`` en columnDefs).
    """
    if not datos:
        return datos
    resultado: list[dict] = []
    for fila in datos:
        nueva: dict = {}
        for clave, valor in fila.items():
            if clave in _CAMPOS_EXCLUIR or clave.endswith("_perdio"):
                continue
            nueva[_CAMPO_RENOMBRAR.get(clave, clave)] = valor
        resultado.append(nueva)
    return resultado


# ─────────────────────────────────────────────────────────────────────────────

class InformeService:
    """
    Orquesta la generación de informes académicos en diferentes formatos.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        estadisticos_repo: IEstadisticosRepository,
        exporter: IExporterService | None = None,
        estudiante_repo=None,
    ) -> None:
        self._estadisticos_repo = estadisticos_repo
        self._exporter          = exporter
        self._estudiante_repo   = estudiante_repo

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_exporter_o_lanzar(self) -> IExporterService:
        if self._exporter is None:
            raise ValueError(
                "No hay un exportador configurado. "
                "Proporcione una implementación de IExporterService."
            )
        return self._exporter

    # ------------------------------------------------------------------
    # Informe de notas
    # ------------------------------------------------------------------

    def datos_informe_notas(
        self,
        dto: InformeNotasDTO,
    ) -> list[dict]:
        """
        Obtiene los datos del informe de notas para un grupo y periodo.

        Retorna una lista de dicts donde cada fila es un estudiante
        con sus notas definitivas por asignatura.
        """
        return self._estadisticos_repo.consolidado_notas_grupo(
            dto.grupo_id, dto.periodo_id
        )

    def generar_notas(
        self,
        dto: InformeNotasDTO,
    ) -> bytes:
        """
        Genera el informe de notas en el formato especificado (Excel o PDF).

        Obtiene los datos del consolidado y los exporta al formato indicado.
        Retorna el contenido como bytes para descarga directa.

        Lanza:
            ValueError: Si no hay exportador configurado.
        """
        exporter = self._get_exporter_o_lanzar()
        datos = sanitizar_datos_exportacion(self.datos_informe_notas(dto))

        if dto.formato == FormatoInforme.EXCEL:
            return exporter.exportar_excel(
                datos,
                nombre_hoja=f"Notas Periodo {dto.periodo_id}",
            )
        else:
            html = self._datos_a_html(
                datos,
                titulo=f"Informe de Notas — Periodo {dto.periodo_id}",
            )
            return exporter.exportar_pdf(html)

    # ------------------------------------------------------------------
    # Informe de asistencia
    # ------------------------------------------------------------------

    def datos_informe_asistencia(
        self,
        dto: InformeAsistenciaDTO,
    ) -> list[dict]:
        """
        Obtiene los datos del informe de asistencia para un grupo y periodo.

        Retorna una lista de dicts donde cada fila es un registro de
        asistencia por estudiante y asignatura.
        """
        return self._estadisticos_repo.consolidado_asistencia_grupo(
            dto.grupo_id, dto.periodo_id
        )

    def generar_asistencia(
        self,
        dto: InformeAsistenciaDTO,
    ) -> bytes:
        """
        Genera el informe de asistencia en el formato especificado.

        Retorna el contenido como bytes para descarga directa.

        Lanza:
            ValueError: Si no hay exportador configurado.
        """
        exporter = self._get_exporter_o_lanzar()
        datos = sanitizar_datos_exportacion(self.datos_informe_asistencia(dto))

        if dto.formato == FormatoInforme.EXCEL:
            return exporter.exportar_excel(
                datos,
                nombre_hoja=f"Asistencia Periodo {dto.periodo_id}",
            )
        else:
            html = self._datos_a_html(
                datos,
                titulo=f"Informe de Asistencia — Periodo {dto.periodo_id}",
            )
            return exporter.exportar_pdf(html)

    # ------------------------------------------------------------------
    # Informe anual consolidado
    # ------------------------------------------------------------------

    def datos_consolidado_anual(
        self,
        grupo_id: int,
        anio_id: int,
    ) -> list[dict]:
        """
        Obtiene el consolidado anual: notas + estado de promoción.

        Usado para generar el acta final de calificaciones del año.
        """
        return self._estadisticos_repo.consolidado_anual_grupo(grupo_id, anio_id)

    def generar_consolidado_anual(
        self,
        grupo_id: int,
        anio_id: int,
        formato: FormatoInforme = FormatoInforme.EXCEL,
    ) -> bytes:
        """
        Genera el consolidado anual en el formato especificado.

        Retorna el contenido como bytes para descarga directa.

        Lanza:
            ValueError: Si no hay exportador configurado.
        """
        exporter = self._get_exporter_o_lanzar()
        datos = sanitizar_datos_exportacion(self.datos_consolidado_anual(grupo_id, anio_id))

        if formato == FormatoInforme.EXCEL:
            return exporter.exportar_excel(
                datos,
                nombre_hoja=f"Consolidado Anual {anio_id}",
            )
        else:
            html = self._datos_a_html(
                datos,
                titulo=f"Consolidado Anual — Año {anio_id}",
            )
            return exporter.exportar_pdf(html)

    # ------------------------------------------------------------------
    # Exportación directa de datos
    # ------------------------------------------------------------------

    def exportar_csv(
        self,
        datos: list[dict],
        encoding: str = "utf-8-sig",
    ) -> bytes:
        """
        Exporta una lista de dicts como CSV.

        Útil para integraciones con otros sistemas.
        Lanza si no hay exportador configurado.
        """
        exporter = self._get_exporter_o_lanzar()
        return exporter.exportar_csv(datos, encoding=encoding)

    # ------------------------------------------------------------------
    # Boletín por periodo (individual por estudiante)
    # ------------------------------------------------------------------

    def generar_boletin_periodo(
        self,
        estudiante_id: int,
        grupo_id: int,
        periodo_id: int,
        formato: str = "pdf",
        grupo_nombre: str = "",
        periodo_nombre: str = "",
    ) -> bytes:
        """
        Genera el boletín de un estudiante para un periodo específico.

        PDF: genera un documento formal con membrete, tabla Área > Asignatura,
             asistencia por tipo, observaciones y firmas.
        Excel: tabla plana con nota y asistencia por asignatura.

        Lanza:
            ValueError: Si no hay exportador configurado.
        """
        fmt = FormatoInforme(formato)

        if fmt == FormatoInforme.PDF:
            import importlib  # noqa: PLC0415
            _boletin_mod = importlib.import_module("src.infrastructure.exporters.boletin_pdf")
            datos = self._estadisticos_repo.boletin_datos_acumulado(
                estudiante_id, grupo_id, periodo_id
            )
            return _boletin_mod.generar_boletin_acumulado_pdf(datos)

        # Excel: tabla plana acumulada con columna por cada periodo anterior + actual
        exporter = self._get_exporter_o_lanzar()
        datos_raw = self._estadisticos_repo.boletin_datos_acumulado(
            estudiante_id, grupo_id, periodo_id
        )
        periodos = datos_raw.get("periodos", [])
        label_def = "Definitiva" if datos_raw.get("es_ultimo_periodo") else "Promedio"
        filas: list[dict] = []
        for area in datos_raw.get("areas", []):
            for asig in area.get("asignaturas", []):
                fila: dict = {
                    "Área":       area["area_nombre"],
                    "Asignatura": asig["nombre"],
                }
                for per in periodos:
                    fila[per["nombre"]] = asig.get("notas_periodo", {}).get(per["id"])
                fila[label_def]       = asig.get("definitiva")
                fila["Presentes"]     = asig.get("presentes", 0)
                fila["F. Inj."]       = asig.get("faltas_injustificadas", 0)
                fila["F. Just."]      = asig.get("faltas_justificadas", 0)
                fila["Retrasos"]      = asig.get("retrasos", 0)
                fila["Excusas"]       = asig.get("excusas", 0)
                filas.append(fila)
        return exporter.exportar_excel(filas, nombre_hoja="Boletín Periodo")

    # ------------------------------------------------------------------
    # Boletín anual (individual por estudiante)
    # ------------------------------------------------------------------

    def generar_boletin_anual(
        self,
        estudiante_id: int,
        grupo_id: int,
        anio_id: int,
        formato: str = "pdf",
        grupo_nombre: str = "",
    ) -> bytes:
        """
        Genera el boletín anual de un estudiante.

        PDF: documento formal con tabla Área > Asignatura, columnas por periodo
             configuradas dinámicamente, definitiva, asistencia anual, firmas.
        Excel: un libro con una hoja por área, filas por asignatura.

        Lanza:
            ValueError: Si no hay exportador configurado.
        """
        fmt = FormatoInforme(formato)

        if fmt == FormatoInforme.PDF:
            import importlib  # noqa: PLC0415
            _boletin_mod = importlib.import_module("src.infrastructure.exporters.boletin_pdf")
            datos = self._estadisticos_repo.boletin_datos_anual(
                estudiante_id, grupo_id, anio_id
            )
            return _boletin_mod.generar_boletin_anual_pdf(datos)

        # Excel: tabla plana con columna por periodo
        exporter = self._get_exporter_o_lanzar()
        datos_raw = self._estadisticos_repo.boletin_datos_anual(
            estudiante_id, grupo_id, anio_id
        )
        periodos = datos_raw.get("periodos", [])
        filas: list[dict] = []
        for area in datos_raw.get("areas", []):
            for asig in area.get("asignaturas", []):
                fila: dict = {
                    "Área":      area["area_nombre"],
                    "Asignatura": asig["nombre"],
                }
                for per in periodos:
                    nota = asig.get("notas_periodo", {}).get(per["id"])
                    fila[per["nombre"]] = nota
                fila["Definitiva"]    = asig.get("definitiva")
                fila["Presentes"]     = asig.get("presentes", 0)
                fila["F. Inj."]       = asig.get("faltas_injustificadas", 0)
                fila["F. Just."]      = asig.get("faltas_justificadas", 0)
                fila["Retrasos"]      = asig.get("retrasos", 0)
                fila["Excusas"]       = asig.get("excusas", 0)
                filas.append(fila)
        return exporter.exportar_excel(filas, nombre_hoja="Boletín Anual")

    # ------------------------------------------------------------------
    # Boletines masivos por grupo (genera + fusiona, sin merge en la vista)
    # ------------------------------------------------------------------

    def generar_boletines_grupo(
        self,
        grupo_id: int,
        periodo_id: int | None = None,
        anio_id: int | None = None,
        formato: str = "pdf",
        grupo_nombre: str = "",
        periodo_nombre: str = "",
    ) -> BoletinesGrupoDTO:
        """Genera el boletín de cada estudiante del grupo y los fusiona en un
        único documento (PDF combinado o Excel con una hoja por estudiante).

        Modo periodo: pasar `periodo_id`. Modo anual: pasar `anio_id`.
        Devuelve el documento fusionado y la lista de estudiantes con error.
        """
        if periodo_id is None and anio_id is None:
            raise ValueError("Debe indicar periodo_id (boletín de periodo) o anio_id (anual).")
        if self._estudiante_repo is None:
            raise ValueError("InformeService no tiene estudiante_repo configurado.")

        fmt = FormatoInforme(formato)
        estudiantes = self._estudiante_repo.listar_por_grupo(grupo_id)

        pdfs: list[bytes] = []
        hojas: list[tuple[str, bytes]] = []
        errores: list[str] = []

        for est in estudiantes:
            nombre = f"{est.nombre} {est.apellido}"
            try:
                if anio_id is not None:
                    contenido = self.generar_boletin_anual(
                        est.id, grupo_id, anio_id, formato,
                        grupo_nombre=grupo_nombre,
                    )
                else:
                    contenido = self.generar_boletin_periodo(
                        est.id, grupo_id, periodo_id, formato,
                        grupo_nombre=grupo_nombre, periodo_nombre=periodo_nombre,
                    )
            except Exception:
                errores.append(nombre)
                continue
            if fmt == FormatoInforme.PDF:
                pdfs.append(contenido)
            else:
                hojas.append((f"{est.apellido} {est.nombre}"[:31], contenido))

        if fmt == FormatoInforme.PDF:
            contenido_final = merge_pdfs(pdfs) if pdfs else None
        else:
            contenido_final = merge_excels(hojas) if hojas else None

        return BoletinesGrupoDTO(contenido=contenido_final, errores=errores)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Exportación de estadísticos (encapsula el pipeline de la vista)
    # ------------------------------------------------------------------

    _ESTADO_ASISTENCIA_LABEL = {
        "P": "Presente", "FJ": "Falta Justificada",
        "FI": "Falta Injustificada", "R": "Retraso", "E": "Excusa",
    }

    # tipo → (título PDF, nombre de hoja Excel)
    _ESTADISTICO_TITULOS = {
        "consolidado_notas":       ("Consolidado de Notas", "Consolidado Notas"),
        "consolidado_asistencia":  ("Consolidado de Asistencia", "Consolidado Asistencia"),
        "ranking_grupo":           ("Ranking del Grupo", "Ranking"),
        "distribucion_desempenos": ("Distribución de Desempeños", "Distribución Desempeños"),
        "estados_asistencia":      ("Estados de Asistencia", "Estados Asistencia"),
        "comparativo_periodos":    ("Comparativo por Periodos", "Comparativo Periodos"),
        "promedios_area":          ("Promedios por Área", "Promedios por Área"),
        "tendencia_asistencia":    ("Tendencia de Asistencia", "Tendencia Asistencia"),
    }

    def _filas_estadistico(self, tipo: str, datos) -> list[dict]:
        """Normaliza `datos` (de cualquier tipo) a list[dict] lista para exportar."""
        if tipo == "estados_asistencia":
            return [
                {"Estado": self._ESTADO_ASISTENCIA_LABEL.get(k, k), "Registros": v}
                for k, v in (datos or {}).items()
            ]
        if tipo == "distribucion_desempenos":
            return [
                {"Nivel de Desempeño": k, "Estudiantes": v}
                for k, v in (datos or {}).items()
            ]
        if tipo == "comparativo_periodos":
            raw = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            return [
                {"Periodo": r.get("periodo_nombre", r.get("Periodo", "")),
                 "Promedio": r.get("promedio", r.get("Promedio", 0))}
                for r in raw
            ]
        if tipo == "tendencia_asistencia":
            return [
                {"Semana": r.get("semana", ""), "% Asistencia": r.get("porcentaje", 0)}
                for r in (datos if isinstance(datos, list) else [])
            ]
        # Tabulares directos (consolidado_notas/asistencia, ranking, promedios_area, …)
        return sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])

    @staticmethod
    def _inyectar_meta_html(html_str: str, contexto: dict | None) -> str:
        """Inyecta <meta> de grupo/periodo/asignatura para el membrete del PDF."""
        contexto = contexto or {}
        metas = (
            f'<meta name="report-grupo" content="{contexto.get("grupo_nombre", "")}">'
            f'<meta name="report-periodo" content="{contexto.get("periodo_nombre", "")}">'
            f'<meta name="report-asignatura" content="{contexto.get("asignatura_nombre", "")}">'
        )
        return html_str.replace("</head>", f"{metas}</head>", 1)

    def exportar_estadistico(
        self,
        tipo: str,
        datos,
        formato: FormatoInforme | str,
        contexto: dict | None = None,
    ) -> bytes:
        """Exporta un estadístico a Excel o PDF encapsulando todo el pipeline
        (sanitizar + normalizar filas + to_html + inyectar meta + exporter).

        `contexto` puede traer: grupo_id, anio_id (para consolidado_anual),
        grupo_nombre/periodo_nombre/asignatura_nombre (membrete PDF).
        """
        fmt = FormatoInforme(formato) if isinstance(formato, str) else formato
        contexto = contexto or {}
        exporter = self._get_exporter_o_lanzar()

        # consolidado_anual delega en su generador (ya sanitiza internamente)
        if tipo == "consolidado_anual":
            return self.generar_consolidado_anual(
                contexto.get("grupo_id"), contexto.get("anio_id"), formato=fmt
            )

        if tipo not in self._ESTADISTICO_TITULOS:
            raise ValueError(f"Tipo de informe no reconocido: {tipo!r}")

        titulo, nombre_hoja = self._ESTADISTICO_TITULOS[tipo]
        filas = self._filas_estadistico(tipo, datos)

        if fmt == FormatoInforme.EXCEL:
            return exporter.exportar_excel(filas, nombre_hoja=nombre_hoja)
        html = self._datos_a_html(filas, titulo=titulo)
        return exporter.exportar_pdf(self._inyectar_meta_html(html, contexto))

    @staticmethod
    def _datos_a_html(datos: list[dict], titulo: str = "Informe") -> str:
        if not datos:
            return (
                f"<html><head><meta charset='utf-8'></head>"
                f"<body><h1>{titulo}</h1><p>No hay datos para mostrar.</p></body></html>"
            )

        encabezados = list(datos[0].keys())
        def _celda(val) -> str:
            if val is None:
                return "—"
            s = str(val).strip()
            return s if s and s.lower() != "none" else "—"

        filas_html = "".join(
            "<tr>" + "".join(f"<td>{_celda(fila.get(col))}</td>" for col in encabezados) + "</tr>"
            for fila in datos
        )
        encabezados_html = "".join(f"<th>{col}</th>" for col in encabezados)

        return (
            f"<html><head><meta charset='utf-8'>"
            f"<style>"
            f"body {{ font-family: Arial, sans-serif; font-size: 11px; }}"
            f"h1 {{ font-size: 15px; color: #2B3674; margin-bottom: 8px; }}"
            f"table {{ border-collapse: collapse; width: 100%; }}"
            f"th {{ background-color: #2B6CB0; color: white; padding: 6px 8px; text-align: center; }}"
            f"td {{ border: 1px solid #ddd; padding: 4px 8px; }}"
            f"tr:nth-child(even) {{ background-color: #f5f5f5; }}"
            f"</style></head>"
            f"<body>"
            f"<h1>{titulo}</h1>"
            f"<table>"
            f"<thead><tr>{encabezados_html}</tr></thead>"
            f"<tbody>{filas_html}</tbody>"
            f"</table>"
            f"</body></html>"
        )


def merge_pdfs(pdf_list: list[bytes]) -> bytes:
    """
    Une varios PDF (como bytes) en un único documento PDF.

    Usa pypdf.  Si la lista tiene un solo elemento lo devuelve directamente.
    Lanza ValueError si la lista está vacía.
    """
    if not pdf_list:
        raise ValueError("No hay PDFs para fusionar.")
    if len(pdf_list) == 1:
        return pdf_list[0]

    import io
    from pypdf import PdfWriter, PdfReader  # noqa: PLC0415

    writer = PdfWriter()
    for pdf_bytes in pdf_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def merge_excels(excel_list: list[tuple[str, bytes]]) -> bytes:
    """
    Combina varios Excel (bytes) en un único libro con una hoja por estudiante.

    Args:
        excel_list: lista de tuplas (nombre_hoja, excel_bytes).
                    El nombre_hoja se trunca a 31 caracteres (límite de Excel).

    Lanza ValueError si la lista está vacía.
    """
    if not excel_list:
        raise ValueError("No hay archivos Excel para fusionar.")

    import io
    import openpyxl  # noqa: PLC0415

    wb_dest = openpyxl.Workbook()
    wb_dest.remove(wb_dest.active)  # elimina la hoja vacía por defecto

    for nombre_hoja, excel_bytes in excel_list:
        wb_src = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        ws_src = wb_src.active
        nombre_safe = nombre_hoja[:31]
        ws_dest = wb_dest.create_sheet(title=nombre_safe)
        for row in ws_src.iter_rows(values_only=True):
            ws_dest.append(list(row))

    buf = io.BytesIO()
    wb_dest.save(buf)
    return buf.getvalue()


__all__ = [
    "InformeService",
    "InformeNotasDTO",
    "InformeAsistenciaDTO",
    "FormatoInforme",
    "sanitizar_datos_exportacion",
    "merge_pdfs",
    "merge_excels",
    "BoletinesGrupoDTO",
]
