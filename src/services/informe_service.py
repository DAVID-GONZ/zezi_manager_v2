"""
InformeService
===============
Orquesta la generación y exportación de informes académicos.

Coordina el repositorio de estadísticos (obtención de datos) con el
IExporterService (conversión al formato de salida). No contiene lógica
de presentación ni accede directamente a la BD.
"""
from __future__ import annotations

from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.ports.service_ports import IExporterService
from src.domain.models.dtos import (
    FormatoInforme,
    InformeAsistenciaDTO,
    InformeNotasDTO,
)


class InformeService:
    """
    Orquesta la generación de informes académicos en diferentes formatos.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        estadisticos_repo: IEstadisticosRepository,
        exporter: IExporterService | None = None,
    ) -> None:
        self._estadisticos_repo = estadisticos_repo
        self._exporter          = exporter

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
        datos = self.datos_informe_notas(dto)

        if dto.formato == FormatoInforme.EXCEL:
            return exporter.exportar_excel(
                datos,
                nombre_hoja=f"Notas Periodo {dto.periodo_id}",
            )
        else:
            # Para PDF generamos un HTML sencillo
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
        datos = self.datos_informe_asistencia(dto)

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
        datos = self.datos_consolidado_anual(grupo_id, anio_id)

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
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _datos_a_html(datos: list[dict], titulo: str = "Informe") -> str:
        """
        Convierte una lista de dicts a una tabla HTML simple.

        Solo se usa internamente para la exportación a PDF cuando no se
        dispone de un motor de plantillas.
        """
        if not datos:
            return f"<h1>{titulo}</h1><p>No hay datos para mostrar.</p>"

        encabezados = list(datos[0].keys())
        filas_html = "".join(
            "<tr>" + "".join(f"<td>{fila.get(col, '')}</td>" for col in encabezados) + "</tr>"
            for fila in datos
        )
        encabezados_html = "".join(f"<th>{col}</th>" for col in encabezados)

        return (
            f"<html><body>"
            f"<h1>{titulo}</h1>"
            f"<table border='1'>"
            f"<thead><tr>{encabezados_html}</tr></thead>"
            f"<tbody>{filas_html}</tbody>"
            f"</table>"
            f"</body></html>"
        )


__all__ = ["InformeService"]
