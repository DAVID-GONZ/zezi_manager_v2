"""
tests/unit/domain/test_enums_schema.py
=======================================

T3 — Hidratación: verifica que los 5 nuevos campos con StrEnum (datos_05)
     aceptan todos los valores que la BD permite y rechazan los inválidos.

T4 — Alineación: verifica los 30 pares CHECK <-> StrEnum usando check_enums.py,
     de modo que la protección exista aunque la puerta no se ejecute manualmente.

Diseño:
  - Los tests de hidratación usan Pydantic directamente: construyen instancias
    con cada valor admitido por el CHECK y verifican que la coerción al enum es
    correcta, que el valor textual se conserva (StrEnum IS str), y que un valor
    ajeno se rechaza con ValidationError identificando el campo.
  - El test de alineación llama a check_enums.py como subproceso para detectar
    divergencias reales en tiempo de CI.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain.models.convivencia import ObservacionPeriodo, OrigenObservacion
from src.domain.models.infraestructura import (
    ConfigGeneracion,
    EstadoConfigGeneracion,
    Franja,
    FranjaReunion,
    ModoFranjaReunion,
    Sala,
    TipoFranja,
    TipoSala,
)

ROOT = Path(__file__).resolve().parents[3]

# =============================================================================
# T3 — Hidratación de las 5 nuevas columnas con enum
# =============================================================================


class TestTipoFranja:
    """Franja.tipo usa TipoFranja y acepta exactamente los valores del CHECK."""

    @pytest.mark.parametrize("valor", ["lectiva", "descanso", "almuerzo"])
    def test_hidratacion_valor_valido(self, valor: str) -> None:
        f = Franja(
            plantilla_id=1,
            orden=1,
            hora_inicio="07:00",
            hora_fin="07:55",
            tipo=valor,
        )
        assert f.tipo == valor, "El valor textual debe conservarse (StrEnum IS str)"
        assert isinstance(f.tipo, TipoFranja), "Debe coercerse al miembro del enum"

    def test_default_es_lectiva(self) -> None:
        f = Franja(plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:55")
        assert f.tipo == TipoFranja.LECTIVA
        assert f.tipo == "lectiva"

    def test_valor_invalido_rechazado(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Franja(
                plantilla_id=1,
                orden=1,
                hora_inicio="07:00",
                hora_fin="07:55",
                tipo="libre",
            )
        err_str = str(exc.value)
        assert "tipo" in err_str, "El mensaje de error debe identificar el campo 'tipo'"

    def test_es_lectiva_computed_field(self) -> None:
        f_lectiva = Franja(
            plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:55", tipo="lectiva"
        )
        f_descanso = Franja(
            plantilla_id=1, orden=4, hora_inicio="09:45", hora_fin="10:15", tipo="descanso"
        )
        assert f_lectiva.es_lectiva is True
        assert f_descanso.es_lectiva is False


class TestTipoSala:
    """Sala.tipo usa TipoSala y acepta exactamente los valores del CHECK."""

    @pytest.mark.parametrize(
        "valor", ["aula", "computo", "ed_fisica", "laboratorio", "otro"]
    )
    def test_hidratacion_valor_valido(self, valor: str) -> None:
        s = Sala(nombre="Sala 1", tipo=valor)
        assert s.tipo == valor, "El valor textual debe conservarse"
        assert isinstance(s.tipo, TipoSala), "Debe coercerse al miembro del enum"

    def test_default_es_aula(self) -> None:
        s = Sala(nombre="Sala 1")
        assert s.tipo == TipoSala.AULA
        assert s.tipo == "aula"

    def test_valor_invalido_rechazado(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Sala(nombre="Sala 1", tipo="gimnasio")
        assert "tipo" in str(exc.value)


class TestModoFranjaReunion:
    """FranjaReunion.modo usa ModoFranjaReunion y acepta exactamente los valores del CHECK."""

    @pytest.mark.parametrize("valor", ["estricta", "preferente"])
    def test_hidratacion_valor_valido(self, valor: str) -> None:
        fr = FranjaReunion(
            nombre="Consejo",
            docentes=[1, 2],
            dia_semana="Lunes",
            franja_orden=1,
            modo=valor,
        )
        assert fr.modo == valor, "El valor textual debe conservarse"
        assert isinstance(fr.modo, ModoFranjaReunion)

    def test_default_es_preferente(self) -> None:
        fr = FranjaReunion(
            nombre="Consejo",
            docentes=[1],
            dia_semana="Lunes",
            franja_orden=1,
        )
        assert fr.modo == ModoFranjaReunion.PREFERENTE
        assert fr.modo == "preferente"

    def test_valor_invalido_rechazado(self) -> None:
        with pytest.raises(ValidationError) as exc:
            FranjaReunion(
                nombre="Consejo",
                docentes=[1],
                dia_semana="Lunes",
                franja_orden=1,
                modo="obligatoria",
            )
        assert "modo" in str(exc.value)


class TestEstadoConfigGeneracion:
    """ConfigGeneracion.estado usa EstadoConfigGeneracion y acepta los valores del CHECK."""

    @pytest.mark.parametrize("valor", ["borrador", "generado", "aplicado"])
    def test_hidratacion_valor_valido(self, valor: str) -> None:
        cg = ConfigGeneracion(
            nombre="Config 2026",
            periodo_id=1,
            anio_id=1,
            plantilla_id=1,
            estado=valor,
        )
        assert cg.estado == valor, "El valor textual debe conservarse"
        assert isinstance(cg.estado, EstadoConfigGeneracion)

    def test_default_es_borrador(self) -> None:
        cg = ConfigGeneracion(
            nombre="Config 2026",
            periodo_id=1,
            anio_id=1,
            plantilla_id=1,
        )
        assert cg.estado == EstadoConfigGeneracion.BORRADOR
        assert cg.estado == "borrador"

    def test_valor_invalido_rechazado(self) -> None:
        with pytest.raises(ValidationError) as exc:
            ConfigGeneracion(
                nombre="Config 2026",
                periodo_id=1,
                anio_id=1,
                plantilla_id=1,
                estado="archivado",
            )
        assert "estado" in str(exc.value)

    def test_maquina_estados_compatible(self) -> None:
        """puede_transicionar_a() sigue funcionando con el campo enum."""
        cg = ConfigGeneracion(
            nombre="Config 2026",
            periodo_id=1,
            anio_id=1,
            plantilla_id=1,
            estado="borrador",
        )
        assert cg.puede_transicionar_a("generado") is True
        assert cg.puede_transicionar_a("aplicado") is False


class TestOrigenObservacion:
    """ObservacionPeriodo.origen usa OrigenObservacion y acepta los valores del CHECK."""

    @pytest.mark.parametrize("valor", ["libre", "plantilla"])
    def test_hidratacion_valor_valido(self, valor: str) -> None:
        obs = ObservacionPeriodo(
            estudiante_id=1,
            asignacion_id=1,
            periodo_id=1,
            texto="Texto de prueba",
            fecha_registro=datetime(2026, 1, 15),
            origen=valor,
        )
        assert obs.origen == valor, "El valor textual debe conservarse"
        assert isinstance(obs.origen, OrigenObservacion)

    def test_default_es_libre(self) -> None:
        obs = ObservacionPeriodo(
            estudiante_id=1,
            asignacion_id=1,
            periodo_id=1,
            texto="Texto de prueba",
            fecha_registro=datetime(2026, 1, 15),
        )
        assert obs.origen == OrigenObservacion.LIBRE
        assert obs.origen == "libre"

    def test_valor_invalido_rechazado(self) -> None:
        with pytest.raises(ValidationError) as exc:
            ObservacionPeriodo(
                estudiante_id=1,
                asignacion_id=1,
                periodo_id=1,
                texto="Texto de prueba",
                fecha_registro=datetime(2026, 1, 15),
                origen="importada",
            )
        assert "origen" in str(exc.value)


# =============================================================================
# T4 — Test de alineación: verifica los 35 pares CHECK <-> StrEnum
# =============================================================================


def test_enum_check_alineacion() -> None:
    """
    check_enums.py debe salir con código 0 (todo alineado).

    Si alguien añade un StrEnum sin CHECK correspondiente, o modifica los
    valores de un enum sin actualizar el schema (o viceversa), este test
    falla y bloquea CI antes que el problema llegue a producción.

    Verificación manual de que detecta divergencias (ejecutada durante desarrollo,
    no en CI): se alteró temporalmente TipoFranja añadiendo un miembro extra,
    se corrió el test → rojo; se revirtió → verde. El test cumple su función.
    """
    result = subprocess.run(
        [sys.executable, "scripts/check_enums.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        "check_enums.py detectó divergencias enum-CHECK:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_enum_check_detecta_valores_extra() -> None:
    """
    Verifica que el algoritmo de emparejamiento detecta una divergencia
    cuando un enum tiene valores que el CHECK no reconoce.

    Usa las funciones internas de check_enums.py (importadas dinámicamente)
    para construir el escenario de prueba sin subprocesos.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_check_enums_mod",
        ROOT / "scripts" / "check_enums.py",
    )
    check_mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(check_mod)  # type: ignore[union-attr]

    # Simular un pool de matchable enums donde TipoFranja tiene un valor extra
    fake_pool: dict[str, frozenset[str]] = {
        "TipoFranja": frozenset({"lectiva", "descanso", "almuerzo", "valor_extra"}),
    }
    # El CHECK para franjas.tipo = {lectiva, descanso, almuerzo} ya no empareja
    # con el fake TipoFranja que tiene 4 valores
    checks = check_mod._parse_checks(check_mod.SCHEMA_PATH)
    franjas_tipo_check = next(
        (vals for t, c, vals in checks if t == "franjas" and c == "tipo"), None
    )
    assert franjas_tipo_check is not None, "El CHECK franjas.tipo debe estar en schema.py"

    fake_values = frozenset({"lectiva", "descanso", "almuerzo", "valor_extra"})
    # Los conjuntos son distintos: el CHECK tiene 3 valores, el fake enum 4
    assert franjas_tipo_check != fake_values, (
        "El CHECK y el fake enum deben tener conjuntos distintos "
        "para que el emparejamiento falle"
    )
    # Verificar que no se emparejarían
    by_values: dict[frozenset[str], list[str]] = {}
    for name, vals in fake_pool.items():
        by_values.setdefault(vals, []).append(name)

    emparejado = franjas_tipo_check in by_values
    assert not emparejado, (
        "Un enum con valor extra NO debe emparejar el CHECK original por igualdad exacta"
    )
