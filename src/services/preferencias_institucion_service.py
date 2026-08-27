"""Servicio de preferencias por institución (tenant)."""

from __future__ import annotations

from typing import Any

from src.domain.models.preferencia_institucion import (
    ActualizarPreferenciaDTO,
    CategoriaPreferencia,
    PreferenciaInstitucion,
    PreferenciasDTO,
    TipoValor,
)
from src.domain.ports.preferencias_repo import IPreferenciasRepository
from src.services.solo_lectura import requiere_escritura

CLAVES_CONOCIDAS: frozenset[str] = frozenset(
    {
        "nota_minima_aprobacion_default",
        "nota_minima_escala_default",
        "nota_maxima_escala_default",
        "numero_periodos_default",
        "modulo_convivencia_activo",
        "modulo_alertas_activo",
        "color_primario",
        "color_secundario",
        # Política de registros en el boletín (convivencia_29)
        "registros_boletin_tipos",
        "registros_boletin_dificultad_requiere_notificacion",
        "registros_boletin_incluye_descargo",
        "registros_boletin_dedup_observaciones",
        # Clasificación de situación (convivencia_34)
        "tipo_situacion_obligatorio",
    }
)


class PreferenciasInstitucionService:
    def __init__(self, repo: IPreferenciasRepository):
        self._repo = repo

    def get_dto(self, institucion_id: int) -> PreferenciasDTO:
        prefs = {p.clave: p.valor_tipado() for p in self._repo.get_all(institucion_id)}
        campos = PreferenciasDTO.model_fields
        kwargs = {k: prefs[k] for k in campos if k in prefs and prefs[k] is not None}
        return PreferenciasDTO(**kwargs)

    def get(self, institucion_id: int, clave: str) -> Any:
        pref = self._repo.get(institucion_id, clave)
        return pref.valor_tipado() if pref else None

    @requiere_escritura
    def set(self, institucion_id: int, dto: ActualizarPreferenciaDTO) -> PreferenciaInstitucion:
        if dto.clave not in CLAVES_CONOCIDAS:
            raise ValueError(f"Clave desconocida: {dto.clave!r}")
        existing = self._repo.get(institucion_id, dto.clave)
        if existing is not None:
            pref = existing.model_copy(update={"valor": dto.valor})
        else:
            pref = PreferenciaInstitucion(
                institucion_id=institucion_id,
                categoria=_inferir_categoria(dto.clave),
                clave=dto.clave,
                valor=dto.valor,
                tipo_valor=_inferir_tipo(dto.clave),
            )
        return self._repo.set(pref)

    def modulo_activo(self, institucion_id: int, nombre_modulo: str) -> bool:
        from src.domain.modulos import clave_de_modulo

        clave = clave_de_modulo(nombre_modulo)
        if clave is None:
            return True
        try:
            val = self.get(institucion_id, clave)
            return bool(val) if val is not None else True
        except Exception:
            return True


def _inferir_categoria(clave: str) -> CategoriaPreferencia:
    if clave.startswith(("modulo_", "registros_boletin_", "tipo_situacion")):
        return CategoriaPreferencia.CONVIVENCIA
    if clave.startswith("color_"):
        return CategoriaPreferencia.APARIENCIA
    return CategoriaPreferencia.ACADEMICAS


def _inferir_tipo(clave: str) -> TipoValor:
    if clave.startswith("modulo_") or clave in (
        "registros_boletin_dificultad_requiere_notificacion",
        "registros_boletin_incluye_descargo",
        "registros_boletin_dedup_observaciones",
        "tipo_situacion_obligatorio",
    ):
        return TipoValor.BOOL
    if clave == "registros_boletin_tipos":
        return TipoValor.JSON
    if clave == "numero_periodos_default":
        return TipoValor.INT
    if clave in ("color_primario", "color_secundario"):
        return TipoValor.STR
    return TipoValor.FLOAT


__all__ = [
    "CLAVES_CONOCIDAS",
    "ActualizarPreferenciaDTO",
    "PreferenciasDTO",
    "PreferenciasInstitucionService",
]
