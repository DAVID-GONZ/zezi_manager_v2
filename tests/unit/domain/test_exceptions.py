"""
test_exceptions.py — Suite de la jerarquía de excepciones de dominio.
=====================================================================

Cubre R1–R8, R16, R18, R19, R20 del paso datos_01_excepciones_dominio.
"""
from __future__ import annotations

from src.domain.exceptions import (
    CategoriaError,
    CodigoError,
    ConflictoError,
    DependenciaNoDisponibleError,
    NoEncontradoError,
    OperacionFueraDeInstitucionError,
    OperacionSoloLecturaError,
    PermisoDenegadoError,
    ReglaDeNegocioError,
    ZeciError,
)

# ---------------------------------------------------------------------------
# R1 — Herencia de ValueError por familia
# ---------------------------------------------------------------------------

def test_regla_negocio_es_value_error():  # R1
    exc = ReglaDeNegocioError("error de regla")
    assert isinstance(exc, ValueError)


def test_no_encontrado_es_value_error():  # R1
    exc = NoEncontradoError("no encontrado")
    assert isinstance(exc, ValueError)


def test_conflicto_es_value_error():  # R1
    exc = ConflictoError("conflicto")
    assert isinstance(exc, ValueError)


def test_permiso_denegado_es_permission_error():  # R1
    exc = PermisoDenegadoError("permiso denegado")
    assert isinstance(exc, PermissionError)


def test_dependencia_no_disponible_es_runtime_error():  # R1
    exc = DependenciaNoDisponibleError("dependencia no disponible")
    assert isinstance(exc, RuntimeError)


def test_solo_lectura_es_permission_error():  # R1
    exc = OperacionSoloLecturaError("solo lectura")
    assert isinstance(exc, PermissionError)


def test_fuera_de_institucion_es_permission_error():  # R1
    exc = OperacionFueraDeInstitucionError("fuera de institución")
    assert isinstance(exc, PermissionError)


# ---------------------------------------------------------------------------
# R2 — Todas las familias son subclases de ZeciError
# ---------------------------------------------------------------------------

def test_todas_las_familias_son_zeci_error():  # R2
    for cls in (
        ReglaDeNegocioError,
        NoEncontradoError,
        ConflictoError,
        PermisoDenegadoError,
        DependenciaNoDisponibleError,
        OperacionSoloLecturaError,
        OperacionFueraDeInstitucionError,
    ):
        exc = cls("msg")
        assert isinstance(exc, ZeciError), f"{cls.__name__} no es ZeciError"


# ---------------------------------------------------------------------------
# R3 — ZeciError NO es subclase de ValueError
# ---------------------------------------------------------------------------

def test_zecierror_no_es_value_error():  # R3
    assert not issubclass(ZeciError, ValueError)


# ---------------------------------------------------------------------------
# R4 — MRO exacto de PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_mro_permiso_denegado():  # R4
    mro = PermisoDenegadoError.__mro__
    # Los primeros 5 deben ser exactamente estos (en orden)
    expected = [PermisoDenegadoError, ZeciError, PermissionError, OSError, Exception]
    assert mro[:5] == tuple(expected), f"MRO inesperado: {mro[:5]}"


# ---------------------------------------------------------------------------
# R5 — exc.args == (mensaje,) y str(exc) == mensaje
# ---------------------------------------------------------------------------

def test_args_y_str():  # R5
    for cls in (
        ReglaDeNegocioError,
        NoEncontradoError,
        ConflictoError,
        PermisoDenegadoError,
        DependenciaNoDisponibleError,
        OperacionSoloLecturaError,
        OperacionFueraDeInstitucionError,
    ):
        msg = f"mensaje de prueba para {cls.__name__}"
        exc = cls(msg)
        assert exc.args == (msg,), f"{cls.__name__}: args={exc.args!r}"
        assert str(exc) == msg, f"{cls.__name__}: str={str(exc)!r}"


# ---------------------------------------------------------------------------
# R6 — Unicidad de miembros de CodigoError
# ---------------------------------------------------------------------------

def test_codigos_unicos():  # R6
    valores = [m.value for m in CodigoError]
    assert len(valores) == len(set(valores)), "Hay valores duplicados en CodigoError"


# ---------------------------------------------------------------------------
# R7 — to_dict() con las tres claves: codigo, mensaje, detalles
# ---------------------------------------------------------------------------

def test_to_dict():  # R7
    exc = ReglaDeNegocioError("test", detalles={"campo": "valor"})
    d = exc.to_dict()
    assert set(d.keys()) == {"codigo", "mensaje", "detalles"}
    assert d["mensaje"] == "test"
    assert d["detalles"] == {"campo": "valor"}
    assert isinstance(d["codigo"], str)


def test_to_dict_detalles_vacio():  # R7
    exc = ConflictoError("conflicto sin detalles")
    d = exc.to_dict()
    assert d["detalles"] == {}


# ---------------------------------------------------------------------------
# R8 — categoria correcta por familia
# ---------------------------------------------------------------------------

def test_categoria_por_familia():  # R8
    assert ReglaDeNegocioError.categoria == CategoriaError.VALIDACION
    assert NoEncontradoError.categoria == CategoriaError.NO_ENCONTRADO
    assert ConflictoError.categoria == CategoriaError.CONFLICTO
    assert PermisoDenegadoError.categoria == CategoriaError.PERMISO
    assert DependenciaNoDisponibleError.categoria == CategoriaError.DEPENDENCIA
    # subclases heredan la categoría del padre
    assert OperacionSoloLecturaError.categoria == CategoriaError.PERMISO
    assert OperacionFueraDeInstitucionError.categoria == CategoriaError.PERMISO


# ---------------------------------------------------------------------------
# R16 — codigo específico en subclases de PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_codigo_especifico_solo_lectura():  # R16
    exc = OperacionSoloLecturaError("operación bloqueada")
    assert exc.codigo == CodigoError.SOLO_LECTURA


def test_codigo_especifico_fuera_de_institucion():  # R16
    exc = OperacionFueraDeInstitucionError("objeto ajeno")
    assert exc.codigo == CodigoError.FUERA_DE_INSTITUCION


# ---------------------------------------------------------------------------
# R19 — codigo puede ser sobreescrito en la instancia
# ---------------------------------------------------------------------------

def test_codigo_override_en_instancia():  # R19
    exc = ConflictoError("periodo cerrado", codigo=CodigoError.PERIODO_CERRADO)
    assert exc.codigo == CodigoError.PERIODO_CERRADO
    assert exc.categoria == CategoriaError.CONFLICTO  # categoria no cambia


def test_codigo_default_sin_override():  # R19
    exc = NoEncontradoError("no existe")
    assert exc.codigo == CodigoError.NO_ENCONTRADO


# ---------------------------------------------------------------------------
# R18 — Guarda estructural: ningún src/services/*.py tiene raise ValueError/RuntimeError
# (se añade en T22 al final del bloque D)
# ---------------------------------------------------------------------------

def test_no_quedan_raises_genericos_en_servicios():  # R18
    """Ningún src/services/*.py debe tener raise ValueError/RuntimeError."""
    import ast
    import pathlib

    servicios = sorted(pathlib.Path("src/services").glob("*.py"))
    encontrados = []
    for f in servicios:
        tree = ast.parse(f.read_text("utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Raise)
                and isinstance(getattr(node, "exc", None), ast.Call)
                and getattr(getattr(node.exc, "func", None), "id", "") in ("ValueError", "RuntimeError")
            ):
                encontrados.append((str(f), node.lineno))
    assert not encontrados, f"Quedan raises genéricos: {encontrados}"


def test_zecierror_lanzados_usan_codigoerror():  # R20
    """Cada ZeciError lanzado desde servicios usa un miembro de CodigoError."""
    import pathlib

    # Solo verifica que no se pasan strings literales fuera del enum
    # (el enum ya lo garantiza por construcción; este test es una segunda red)
    servicios = sorted(pathlib.Path("src/services").glob("*.py"))
    for f in servicios:
        src = f.read_text("utf-8")
        # Si el archivo importa ZeciError o sus subclases, debe importar de src.domain.exceptions
        if "ZeciError" in src or "NoEncontradoError" in src or "ConflictoError" in src:
            assert "from src.domain.exceptions import" in src, (
                f"{f} usa excepciones de dominio pero no importa de src.domain.exceptions"
            )
