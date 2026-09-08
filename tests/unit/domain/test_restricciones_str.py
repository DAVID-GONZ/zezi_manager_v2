"""
Test estructural: restricciones de longitud en campos de texto.
================================================================

R22 — todos los campos str de los modelos en scope tienen cota declarada
       o aparecen en EXCLUSIONES con razón documentada.
R23 — la cota del tipo Annotated coincide con el valor que exige el
       field_validator pre-existente de ese campo.
R24 — añadir un campo str nuevo sin cota rompe este test.
R17 — los campos de email siguen rechazando formatos inválidos y
       normalizan a minúsculas.
"""

from __future__ import annotations

import pytest
from pydantic import StringConstraints
from pydantic.fields import FieldInfo

from src.domain.models.acudiente import (
    ActualizarAcudienteDTO,
    Acudiente,
    NuevoAcudienteDTO,
)
from src.domain.models.configuracion import (
    ActualizarInfoInstitucionalDTO,
    ActualizarNivelDesempenoDTO,
    NivelDesempeno,
    NuevoNivelDesempenoDTO,
)
from src.domain.models.convivencia import (
    CategoriaObservacion,
    EntradaSeguimiento,
    MedidaPedagogica,
    NotaComportamiento,
    NuevaAlertaSeguimientoDTO,
    NuevaCategoriaDTO,
    NuevaEntradaSeguimientoDTO,
    NuevaMedidaPedagogicaDTO,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevaPlantillaDTO,
    NuevoRegistroComportamientoDTO,
    NuevoTipoSituacionDTO,
    ObservacionPeriodo,
    PlantillaObservacion,
    RegistroComportamiento,
    TipoSituacion,
)
from src.domain.models.estudiante import (
    ActualizarEstudianteDTO,
    Estudiante,
    FiltroEstudiantesDTO,
    MovimientoEstudiante,
    NuevoEstudianteDTO,
)
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    ConfigGeneracion,
    EscenarioHorario,
    Franja,
    FranjaReunion,
    Grado,
    Grupo,
    Horario,
    Logro,
    NuevaAreaDTO,
    NuevaAsignaturaDTO,
    NuevaConfigGeneracionDTO,
    NuevaFranjaDTO,
    NuevaPlantillaFranjaDTO,
    NuevaSalaDTO,
    NuevoEscenarioDTO,
    NuevoGrupoDTO,
    NuevoHorarioDTO,
    NuevoLogroDTO,
    PlantillaFranja,
    Sala,
)
from src.domain.models.institucion import (
    ActualizarInstitucionDTO,
    Institucion,
    NuevaInstitucionConDirectorDTO,
    NuevaInstitucionDTO,
)

# ---------------------------------------------------------------------------
# Importar todos los modelos en scope
# ---------------------------------------------------------------------------
from src.domain.models.usuario import (
    ActualizarUsuarioDTO,
    FiltroUsuariosDTO,
    NuevoUsuarioDTO,
    Usuario,
)

# ---------------------------------------------------------------------------
# Función auxiliar: extrae max_length de StringConstraints en un campo
# ---------------------------------------------------------------------------


def _max_length_en_tipo(tipo: object) -> int | None:
    """Busca recursivamente StringConstraints con max_length dentro de un tipo.

    Cubre:
    - Annotated[str, StringConstraints(max_length=N)]        → metadata directa
    - Annotated[str, StringConstraints(max_length=N)] | None → metadata dentro del Union
    - typing.Union[Annotated[str, ...], None]                → idem
    """
    if tipo is None:
        return None
    # Annotated lleva __metadata__
    if hasattr(tipo, "__metadata__"):
        for meta in tipo.__metadata__:  # type: ignore[attr-defined]
            if isinstance(meta, StringConstraints) and meta.max_length is not None:
                return meta.max_length
    # Union / UnionType: buscar en cada argumento
    for arg in getattr(tipo, "__args__", ()):
        result = _max_length_en_tipo(arg)
        if result is not None:
            return result
    return None


def _max_length_de_campo(field_info: FieldInfo) -> int | None:
    """Busca StringConstraints en la metadata del campo y retorna max_length.

    Busca primero en field_info.metadata (cotas directas) y luego de forma
    recursiva dentro de field_info.annotation (cotas dentro de Union | None).
    """
    for meta in field_info.metadata:
        if isinstance(meta, StringConstraints) and meta.max_length is not None:
            return meta.max_length
    # Fallback: buscar dentro del tipo anotado (cubre Tipo | None)
    return _max_length_en_tipo(field_info.annotation)


# ---------------------------------------------------------------------------
# MODELOS_EN_SCOPE: todas las clases a verificar por R22/R24
# ---------------------------------------------------------------------------

MODELOS_EN_SCOPE: list[type] = [
    # usuario.py
    Usuario,
    NuevoUsuarioDTO,
    ActualizarUsuarioDTO,
    FiltroUsuariosDTO,
    # institucion.py
    Institucion,
    NuevaInstitucionDTO,
    ActualizarInstitucionDTO,
    NuevaInstitucionConDirectorDTO,
    # estudiante.py
    Estudiante,
    NuevoEstudianteDTO,
    ActualizarEstudianteDTO,
    FiltroEstudiantesDTO,
    MovimientoEstudiante,
    # acudiente.py
    Acudiente,
    NuevoAcudienteDTO,
    ActualizarAcudienteDTO,
    # convivencia.py
    TipoSituacion,
    MedidaPedagogica,
    CategoriaObservacion,
    PlantillaObservacion,
    ObservacionPeriodo,
    EntradaSeguimiento,
    RegistroComportamiento,
    NotaComportamiento,
    NuevoTipoSituacionDTO,
    NuevaMedidaPedagogicaDTO,
    NuevaCategoriaDTO,
    NuevaPlantillaDTO,
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
    NuevaEntradaSeguimientoDTO,
    NuevaNotaComportamientoDTO,
    NuevaAlertaSeguimientoDTO,
    # configuracion.py
    NivelDesempeno,
    NuevoNivelDesempenoDTO,
    ActualizarNivelDesempenoDTO,
    ActualizarInfoInstitucionalDTO,
    # infraestructura.py
    AreaConocimiento,
    Asignatura,
    Grupo,
    Grado,
    EscenarioHorario,
    Horario,
    Logro,
    Franja,
    PlantillaFranja,
    ConfigGeneracion,
    FranjaReunion,
    Sala,
    NuevaAreaDTO,
    NuevaAsignaturaDTO,
    NuevoGrupoDTO,
    NuevoEscenarioDTO,
    NuevaSalaDTO,
    NuevoHorarioDTO,
    NuevoLogroDTO,
    NuevaPlantillaFranjaDTO,
    NuevaFranjaDTO,
    NuevaConfigGeneracionDTO,
]


# ---------------------------------------------------------------------------
# EXCLUSIONES: campos str sin cota y su razón (R12/R13/R14/excepcion)
# ---------------------------------------------------------------------------
# Formato: {Clase: {nombre_campo: "Rxx: razón"}}

EXCLUSIONES: dict[type, dict[str, str]] = {
    # -----------------------------------------------------------------------
    # usuario.py
    # -----------------------------------------------------------------------
    # DocenteInfoDTO, AsignacionDocenteInfoDTO, UsuarioResumenDTO,
    # ResumenUsuariosDTO excluidos de MODELOS_EN_SCOPE por R13.
    # -----------------------------------------------------------------------
    # institucion.py
    # -----------------------------------------------------------------------
    # InstitucionResumenDTO, ResultadoAprovisionamientoDTO: R13.
    # -----------------------------------------------------------------------
    # estudiante.py
    # -----------------------------------------------------------------------
    # EstudianteResumenDTO, MovimientoEstudianteInfoDTO: R13.
    # -----------------------------------------------------------------------
    # acudiente.py — sin exclusiones en clases de MODELOS_EN_SCOPE
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # convivencia.py
    # -----------------------------------------------------------------------
    EntradaSeguimiento: {
        "usuario_nombre": (
            "R13: campo poblado exclusivamente por el repositorio desde un JOIN; "
            "nunca recibe datos crudos de un cliente."
        ),
    },
    # -----------------------------------------------------------------------
    # configuracion.py — sin exclusiones en clases de MODELOS_EN_SCOPE
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # infraestructura.py
    # -----------------------------------------------------------------------
    AreaConocimiento: {
        "color": (
            "Excepción documentada (design.md §3): hex CSS; "
            "valores válidos son #RGB (4 chars) o #RRGGBB (7 chars). "
            "El validator retorna None para cualquier valor inválido. "
            "Es una cadena de formato fijo, no una categoría de longitud libre."
        ),
    },
    EscenarioHorario: {
        "created_at": "R14: representa un instante de tiempo en ISO 8601.",
    },
    PlantillaFranja: {
        "jornada": (
            "R14: validado contra JORNADAS_VALIDAS (conjunto cerrado AM/PM/UNICA), "
            "destinado a enum en paso futuro."
        ),
        "created_at": "R14: representa un instante de tiempo en ISO 8601.",
    },
    Franja: {
        "hora_inicio": "R14: representación de hora en formato HH:MM.",
        "hora_fin": "R14: representación de hora en formato HH:MM.",
    },
    ConfigGeneracion: {
        "created_at": "R14: representa un instante de tiempo en ISO 8601.",
        "updated_at": "R14: representa un instante de tiempo en ISO 8601.",
    },
    FranjaReunion: {
        "dia_semana": (
            "R14: validado contra DIAS_VALIDOS (conjunto cerrado, derivado de DiaSemana StrEnum)."
        ),
    },
    NuevaPlantillaFranjaDTO: {
        "jornada": (
            "R14: validado contra JORNADAS_VALIDAS (conjunto cerrado AM/PM/UNICA), "
            "destinado a enum en paso futuro."
        ),
    },
    NuevaFranjaDTO: {
        "hora_inicio": "R14: representación de hora en formato HH:MM.",
        "hora_fin": "R14: representación de hora en formato HH:MM.",
    },
}


# ---------------------------------------------------------------------------
# COTAS_CON_VALIDATOR_EXISTENTE: pares (Clase, campo) donde YA había un
# field_validator con comprobación de max_length antes de este paso.
# El test R23 verifica que el tipo Annotated coincida con ese valor.
# ---------------------------------------------------------------------------

COTAS_CON_VALIDATOR_EXISTENTE: dict[tuple[type, str], int] = {
    (Usuario, "usuario"): 50,
    (Usuario, "nombre_completo"): 150,
    (Estudiante, "nombre"): 100,
    (Estudiante, "apellido"): 100,
    (NuevoEstudianteDTO, "nombre"): 100,
    (NuevoEstudianteDTO, "apellido"): 100,
    (ActualizarEstudianteDTO, "nombre"): 100,
    (ActualizarEstudianteDTO, "apellido"): 100,
    (Acudiente, "nombre_completo"): 150,
    (Institucion, "nombre"): 200,
    (Institucion, "nombre_oficial"): 200,
    (NuevaInstitucionDTO, "nombre"): 200,
    (NuevaInstitucionConDirectorDTO, "nombre"): 200,
    (NuevaInstitucionConDirectorDTO, "nombre_oficial"): 200,
    (AreaConocimiento, "nombre"): 120,
    (Asignatura, "nombre"): 100,
    (Grupo, "codigo"): 20,
    (NivelDesempeno, "nombre"): 50,
    (ObservacionPeriodo, "texto"): 2000,
    (EntradaSeguimiento, "texto"): 2000,
    (RegistroComportamiento, "descripcion"): 1000,
    (Logro, "descripcion"): 500,
}


# ---------------------------------------------------------------------------
# Ayuda para detectar campos str (incluyendo str | None)
# ---------------------------------------------------------------------------


def _es_str_simple(annotation: object) -> bool:
    """True si la anotación es `str` o `str | None` (sin Annotated)."""
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())
    # Annotated tiene __class_getitem__ y su __origin__ es str si es un simple
    # StringConstraints-typed field; en ese caso _max_length_de_campo lo capta.
    # Aquí detectamos el caso en que NO hay Annotated y la anotación es str.
    if annotation is str:
        return True
    # str | None  (UnionType en 3.10+)
    if origin is type(None):
        return False
    try:
        import types

        if isinstance(annotation, types.UnionType):
            return set(args) == {str, type(None)}
    except AttributeError:
        pass
    # typing.Union[str, None]
    if origin is getattr(__import__("typing"), "Union", None):
        return set(args) == {str, type(None)}
    return False


def _tiene_string_constraints(annotation: object) -> bool:
    """True si la anotación es Annotated[str, StringConstraints(max_length=…)]."""
    import typing

    origin = getattr(annotation, "__origin__", None)
    # Annotated tiene __class_getitem__ y origin es el tipo base
    if origin is None:
        return False
    # Python 3.8+ Annotated
    if hasattr(typing, "get_args") and hasattr(annotation, "__metadata__"):
        # Annotated[str, ...] o Annotated[str | None, ...]
        for meta in annotation.__metadata__:  # type: ignore[attr-defined]
            if isinstance(meta, StringConstraints) and meta.max_length is not None:
                return True
    return False


def _anotacion_es_str_sin_cota(model: type, campo: str) -> tuple[bool, bool]:
    """
    Retorna (es_str_como_tal, tiene_cota).

    Un campo es 'str sin cota' si su tipo efectivo incluye str pero no lleva
    StringConstraints con max_length en su metadata.
    """
    field_info = model.model_fields[campo]
    # Si max_length está en metadata, tiene cota
    max_len = _max_length_de_campo(field_info)
    if max_len is not None:
        return False, True

    # Revisar si la anotación bruta es str / str | None (sin Annotated acotado)
    ann = model.__annotations__.get(campo)
    if ann is None:
        # Buscar en la jerarquía de clases
        for cls in model.__mro__:
            if campo in getattr(cls, "__annotations__", {}):
                ann = cls.__annotations__[campo]
                break
    if ann is None:
        return False, False

    es_str = _es_str_simple(ann)
    return es_str, False


# ---------------------------------------------------------------------------
# T E S T S
# ---------------------------------------------------------------------------


def test_todos_los_campos_str_tienen_cota() -> None:
    """
    R22, R24 — Para cada modelo en scope y cada campo de texto (str o str | None),
    verifica que haya una StringConstraints con max_length en la metadata del campo.
    Si no la tiene, el campo DEBE estar en EXCLUSIONES con razón documentada.
    """
    fallos: list[str] = []

    for modelo in MODELOS_EN_SCOPE:
        exclusiones_modelo = EXCLUSIONES.get(modelo, {})
        for nombre_campo, field_info in modelo.model_fields.items():
            # Comprobar si tiene cota declarada
            max_len = _max_length_de_campo(field_info)
            if max_len is not None:
                continue  # tiene cota → OK

            # Sin cota: verificar si está en EXCLUSIONES
            if nombre_campo in exclusiones_modelo:
                continue  # excluido con razón → OK

            # Sin cota y sin exclusión: verificar si el tipo involucra str
            # (campos int, bool, Decimal, date, etc. no nos interesan)
            _ = modelo.model_fields[nombre_campo].annotation
            # Pydantic v2 pone la anotación procesada en field_info.annotation
            # pero puede ser None si usa tipos complejos.
            # Recorremos la jerarquía si es necesario.
            raw_ann = None
            for cls in modelo.__mro__:
                if nombre_campo in getattr(cls, "__annotations__", {}):
                    raw_ann = cls.__annotations__[nombre_campo]
                    break

            if raw_ann is None:
                continue  # no encontrado como anotación directa

            if _es_str_simple(raw_ann):
                fallos.append(
                    f"{modelo.__name__}.{nombre_campo}: "
                    f"campo str sin cota declarada y no registrado en EXCLUSIONES."
                )

    assert not fallos, (
        "Los siguientes campos de texto no tienen cota ni exclusión justificada:\n"
        + "\n".join(f"  - {f}" for f in fallos)
    )


def test_cotas_coherentes_con_validators_existentes() -> None:
    """
    R23 — Para cada campo que ya tenía un field_validator con max_length explícito,
    verifica que la cota del tipo Annotated coincida con ese valor.
    """
    fallos: list[str] = []

    for (modelo, campo), max_esperado in COTAS_CON_VALIDATOR_EXISTENTE.items():
        field_info = modelo.model_fields.get(campo)
        if field_info is None:
            fallos.append(f"{modelo.__name__}.{campo}: campo no encontrado en model_fields.")
            continue

        max_real = _max_length_de_campo(field_info)
        if max_real is None:
            fallos.append(
                f"{modelo.__name__}.{campo}: no tiene StringConstraints con max_length "
                f"(esperado: {max_esperado})."
            )
        elif max_real != max_esperado:
            fallos.append(
                f"{modelo.__name__}.{campo}: max_length={max_real} en el tipo "
                f"pero el validator existente exige {max_esperado} (R6: deben coincidir)."
            )

    assert not fallos, (
        "Divergencia entre cota del tipo Annotated y validator existente (R6/R8):\n"
        + "\n".join(f"  - {f}" for f in fallos)
    )


def test_email_formato_preservado() -> None:
    """
    R17 — Los modelos con campo email siguen rechazando cadenas sin '@',
    cadenas con dominio sin '.', y aceptan email válido normalizado a minúsculas.

    Modelos representativos: Usuario, Acudiente, Institucion.
    """
    from pydantic import ValidationError

    # ---- Usuario ----
    # Rechaza sin '@'
    with pytest.raises(ValidationError):
        Usuario(usuario="u1", nombre_completo="User One", email="noemail")

    # Rechaza dominio sin '.'
    with pytest.raises(ValidationError):
        Usuario(usuario="u2", nombre_completo="User Two", email="a@nodot")

    # Acepta email válido y normaliza a minúsculas
    u = Usuario(usuario="test", nombre_completo="Test User", email="Test@Example.COM")
    assert u.email == "test@example.com"  # R17: normalizado

    # Acepta None (email opcional)
    u2 = Usuario(usuario="test2", nombre_completo="Test Two", email=None)
    assert u2.email is None

    # Rechaza email demasiado largo (R16)
    with pytest.raises(ValidationError):
        Usuario(
            usuario="test3",
            nombre_completo="Test Three",
            email="a" * 250 + "@b.com",  # 256 chars > 254
        )

    # ---- Acudiente ----
    from src.domain.models.acudiente import Parentesco

    with pytest.raises(ValidationError):
        Acudiente(
            numero_documento="123",
            nombre_completo="Maria Garcia",
            parentesco=Parentesco.MADRE,
            email="sinformato",
        )

    a = Acudiente(
        numero_documento="123",
        nombre_completo="Maria Garcia",
        parentesco=Parentesco.MADRE,
        email="MARIA@ejemplo.com",
    )
    assert a.email == "maria@ejemplo.com"  # R17: normalizado

    # ---- Institucion ----
    # Institucion.email_institucional no tiene field_validator de formato
    # (solo StringConstraints max_length=254 vía EmailStr): la cota sí aplica.
    with pytest.raises(ValidationError):
        Institucion(
            nombre="Colegio Test",
            email_institucional="e" * 250 + "@x.co",  # 256 chars > 254
        )

    # Email corto válido se acepta tal cual (sin normalización: no hay validator)
    inst = Institucion(nombre="Colegio Test", email_institucional="info@colegio.edu.co")
    assert inst.email_institucional == "info@colegio.edu.co"
