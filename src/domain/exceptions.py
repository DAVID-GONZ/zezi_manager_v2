"""
Jerarquía de excepciones de dominio de ZECI Manager.

La herencia doble (ValueError / PermissionError / RuntimeError) es un puente
transitorio: permite que los 92 `except ValueError`, 7 `except PermissionError` y
9 `except (ValueError, RuntimeError)` de src/interface/ sigan funcionando sin tocar
esa capa. Los mixins se retirarán cuando la interfaz migre a capturar ZeciError.
"""
import enum
from collections.abc import Mapping
from typing import ClassVar


class CategoriaError(enum.StrEnum):
    VALIDACION    = "validacion"
    NO_ENCONTRADO = "no_encontrado"
    CONFLICTO     = "conflicto"
    PERMISO       = "permiso"
    DEPENDENCIA   = "dependencia"


class CodigoError(enum.StrEnum):
    # defaults por familia
    REGLA_NEGOCIO            = "REGLA_NEGOCIO"
    NO_ENCONTRADO            = "NO_ENCONTRADO"
    CONFLICTO                = "CONFLICTO"
    PERMISO_DENEGADO         = "PERMISO_DENEGADO"
    DEPENDENCIA_NO_DISPONIBLE = "DEPENDENCIA_NO_DISPONIBLE"
    # específicos
    SOLO_LECTURA             = "SOLO_LECTURA"
    FUERA_DE_INSTITUCION     = "FUERA_DE_INSTITUCION"
    DOCUMENTO_DUPLICADO      = "DOCUMENTO_DUPLICADO"
    USUARIO_DUPLICADO        = "USUARIO_DUPLICADO"
    PERIODO_CERRADO          = "PERIODO_CERRADO"
    ACTIVIDAD_CERRADA        = "ACTIVIDAD_CERRADA"
    PESOS_EXCEDEN_TOTAL      = "PESOS_EXCEDEN_TOTAL"
    NOTA_FUERA_DE_ESCALA     = "NOTA_FUERA_DE_ESCALA"
    SOLAPE_HORARIO           = "SOLAPE_HORARIO"
    CARGA_DOCENTE_EXCEDIDA   = "CARGA_DOCENTE_EXCEDIDA"
    ROL_NO_AUTORIZADO        = "ROL_NO_AUTORIZADO"
    PASSWORD_INCORRECTA      = "PASSWORD_INCORRECTA"
    AUTENTICACION_NO_CONFIGURADA = "AUTENTICACION_NO_CONFIGURADA"
    REPOSITORIO_NO_DISPONIBLE = "REPOSITORIO_NO_DISPONIBLE"
    EXPORTADOR_NO_DISPONIBLE = "EXPORTADOR_NO_DISPONIBLE"


class ZeciError(Exception):
    """Raíz de toda condición de error originada en las reglas del negocio."""
    codigo: ClassVar[CodigoError]
    categoria: ClassVar[CategoriaError]

    def __init__(
        self,
        mensaje: str,
        *,
        codigo: CodigoError | None = None,
        detalles: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(mensaje)   # UN solo argumento — OSError reinterpreta 2+
        self.mensaje = mensaje
        self.codigo = codigo or type(self).codigo
        self.detalles: dict[str, object] = dict(detalles or {})

    def to_dict(self) -> dict[str, object]:
        return {
            "codigo": str(self.codigo),
            "mensaje": self.mensaje,
            "detalles": self.detalles,
        }


class ReglaDeNegocioError(ZeciError, ValueError):
    codigo = CodigoError.REGLA_NEGOCIO
    categoria = CategoriaError.VALIDACION


class NoEncontradoError(ZeciError, ValueError):
    codigo = CodigoError.NO_ENCONTRADO
    categoria = CategoriaError.NO_ENCONTRADO


class ConflictoError(ZeciError, ValueError):
    codigo = CodigoError.CONFLICTO
    categoria = CategoriaError.CONFLICTO


class PermisoDenegadoError(ZeciError, PermissionError):
    codigo = CodigoError.PERMISO_DENEGADO
    categoria = CategoriaError.PERMISO


class DependenciaNoDisponibleError(ZeciError, RuntimeError):
    codigo = CodigoError.DEPENDENCIA_NO_DISPONIBLE
    categoria = CategoriaError.DEPENDENCIA


class OperacionSoloLecturaError(PermisoDenegadoError):
    codigo = CodigoError.SOLO_LECTURA


class OperacionFueraDeInstitucionError(PermisoDenegadoError):
    codigo = CodigoError.FUERA_DE_INSTITUCION
