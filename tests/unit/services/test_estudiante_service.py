"""Tests unitarios para EstudianteService."""
from __future__ import annotations

import pytest

from src.domain.models.estudiante import (
    Estudiante, EstadoMatricula, FiltroEstudiantesDTO,
    EstudianteResumenDTO, NuevoEstudianteDTO,
)
from src.domain.models.piar import PIAR, NuevoPIARDTO, ActualizarPIARDTO
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.services.estudiante_service import EstudianteService


# ===========================================================================
# Fake
# ===========================================================================

class FakeEstudianteRepo(IEstudianteRepository):
    def __init__(self):
        self._ests: dict[int, Estudiante] = {}
        self._piars: list[PIAR] = []
        self._next_id = 1
        self._next_piar = 1

    def guardar(self, e: Estudiante) -> Estudiante:
        e = e.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._ests[e.id] = e
        return e

    def actualizar(self, e: Estudiante) -> Estudiante:
        self._ests[e.id] = e
        return e

    def actualizar_estado_matricula(self, eid: int, estado: str) -> None:
        e = self._ests[eid]
        self._ests[eid] = e.model_copy(update={"estado_matricula": estado})

    def get_by_id(self, eid: int) -> Estudiante | None:
        return self._ests.get(eid)

    def get_by_documento(self, doc: str, institucion_id: int | None = None) -> Estudiante | None:
        for e in self._ests.values():
            if e.numero_documento == doc and (
                institucion_id is None or e.institucion_id == institucion_id
            ):
                return e
        return None

    def existe_documento(self, doc: str, institucion_id: int | None = None) -> bool:
        return any(
            e.numero_documento == doc
            and (institucion_id is None or e.institucion_id == institucion_id)
            for e in self._ests.values()
        )

    def asignar_grupo(self, eid: int, grupo_id: int) -> None:
        e = self._ests[eid]
        self._ests[eid] = e.model_copy(update={"grupo_id": grupo_id})

    def listar_por_grupo(
        self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None
    ) -> list[Estudiante]:
        return [
            e for e in self._ests.values()
            if e.grupo_id == grupo_id
            and (institucion_id is None or e.institucion_id == institucion_id)
        ]

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        return [
            e for e in self._ests.values()
            if filtro.institucion_id is None or e.institucion_id == filtro.institucion_id
        ]

    def listar_resumenes(self, filtro: FiltroEstudiantesDTO) -> list[EstudianteResumenDTO]:
        return []

    def contar_por_grupo(
        self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None
    ) -> int:
        return sum(
            1 for e in self._ests.values()
            if e.grupo_id == grupo_id
            and (institucion_id is None or e.institucion_id == institucion_id)
        )

    def get_resumen(self, eid: int) -> EstudianteResumenDTO | None:
        return None

    def existe_piar(self, eid: int, anio_id: int) -> bool:
        return any(p.estudiante_id == eid and p.anio_id == anio_id for p in self._piars)

    def guardar_piar(self, p: PIAR) -> PIAR:
        p = p.model_copy(update={"id": self._next_piar})
        self._next_piar += 1
        self._piars.append(p)
        return p

    def get_piar(self, eid: int, anio_id: int) -> PIAR | None:
        for p in self._piars:
            if p.estudiante_id == eid and p.anio_id == anio_id:
                return p
        return None

    def actualizar_piar(self, p: PIAR) -> PIAR:
        return p

    def listar_piars(self, eid: int) -> list[PIAR]:
        return [p for p in self._piars if p.estudiante_id == eid]


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[EstudianteService, FakeEstudianteRepo]:
    repo = FakeEstudianteRepo()
    return EstudianteService(repo), repo


def _dto(doc: str = "123456789") -> NuevoEstudianteDTO:
    return NuevoEstudianteDTO(
        numero_documento=doc,
        nombre="Carlos",
        apellido="Pérez",
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestMatricular:
    def test_matricula_estudiante_nuevo(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        assert est.id is not None
        assert est.numero_documento == "123456789"

    def test_lanza_si_documento_duplicado(self):
        svc, _ = _make_svc()
        svc.matricular(_dto("123456789"))
        with pytest.raises(ValueError, match="123456789"):
            svc.matricular(_dto("123456789"))

    def test_documentos_distintos_no_duplican(self):
        svc, _ = _make_svc()
        e1 = svc.matricular(_dto("111"))
        e2 = svc.matricular(_dto("222"))
        assert e1.id != e2.id


class TestRetirar:
    def test_retira_estudiante_activo(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        retirado = svc.retirar(est.id)
        assert retirado.estado_matricula == EstadoMatricula.RETIRADO

    def test_lanza_si_ya_retirado(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        svc.retirar(est.id)
        with pytest.raises(ValueError, match="RETIRADO"):
            svc.retirar(est.id)

    def test_lanza_si_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.retirar(999)


class TestRegistrarPIAR:
    def test_registra_piar_nuevo(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        dto_piar = NuevoPIARDTO(
            estudiante_id=est.id,
            anio_id=1,
            descripcion_necesidad="Necesidades específicas de aprendizaje",
        )
        piar = svc.registrar_piar(dto_piar)
        assert piar.id is not None

    def test_lanza_si_piar_duplicado(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        dto_piar = NuevoPIARDTO(
            estudiante_id=est.id, anio_id=1,
            descripcion_necesidad="Plan inicial",
        )
        svc.registrar_piar(dto_piar)
        with pytest.raises(ValueError, match="Ya existe un PIAR"):
            svc.registrar_piar(dto_piar)


class TestActualizarPIAR:
    def test_actualiza_piar_existente(self):
        svc, repo = _make_svc()
        est = svc.matricular(_dto())
        svc.registrar_piar(NuevoPIARDTO(
            estudiante_id=est.id, anio_id=1,
            descripcion_necesidad="Descripción original",
        ))
        dto_act = ActualizarPIARDTO(descripcion_necesidad="Descripción actualizada")
        piar = svc.actualizar_piar(est.id, 1, dto_act)
        assert piar.descripcion_necesidad == "Descripción actualizada"

    def test_actualiza_solo_campos_provistos(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        svc.registrar_piar(NuevoPIARDTO(
            estudiante_id=est.id, anio_id=1,
            descripcion_necesidad="Original",
            ajustes_evaluativos="Ajustes previos",
        ))
        dto_act = ActualizarPIARDTO(ajustes_pedagogicos="Nuevos ajustes pedagógicos")
        piar = svc.actualizar_piar(est.id, 1, dto_act)
        # El campo no tocado se conserva
        assert piar.ajustes_evaluativos == "Ajustes previos"
        assert piar.ajustes_pedagogicos == "Nuevos ajustes pedagógicos"

    def test_lanza_si_piar_no_existe(self):
        svc, _ = _make_svc()
        dto_act = ActualizarPIARDTO(descripcion_necesidad="No importa")
        with pytest.raises(ValueError, match="No existe PIAR"):
            svc.actualizar_piar(999, 1, dto_act)


class TestMatricularMasivoCsv:
    def _filas(self, n: int = 3) -> list[dict]:
        return [
            {
                "tipo_documento": "TI",
                "numero_documento": f"DOC{i:03d}",
                "nombre": f"Nombre{i}",
                "apellido": f"Apellido{i}",
                "genero": "M",
                "grupo_codigo": "A1",
            }
            for i in range(1, n + 1)
        ]

    def test_carga_exitosa(self):
        svc, _ = _make_svc()
        mapa = {"A1": 10}
        resultado = svc.matricular_masivo_csv(self._filas(3), mapa)
        assert resultado.total_procesadas == 3
        assert resultado.exitosas == 3
        assert resultado.fallidas == 0

    def test_documenta_errores_en_duplicados(self):
        svc, _ = _make_svc()
        filas = self._filas(2)
        # Fila duplicada
        filas.append({
            "tipo_documento": "TI",
            "numero_documento": "DOC001",   # ya insertado
            "nombre": "Dup",
            "apellido": "Ado",
            "genero": "",
            "grupo_codigo": "",
        })
        resultado = svc.matricular_masivo_csv(filas, {})
        assert resultado.total_procesadas == 3
        assert resultado.exitosas == 2
        assert resultado.fallidas == 1
        assert resultado.errores[0]["dato"] == "DOC001"

    def test_grupo_desconocido_no_interrumpe(self):
        svc, _ = _make_svc()
        filas = self._filas(1)
        # mapa vacío → grupo_id=None, pero se matricula igual
        resultado = svc.matricular_masivo_csv(filas, {})
        assert resultado.exitosas == 1

    def test_fue_exitosa_true_si_sin_errores(self):
        svc, _ = _make_svc()
        resultado = svc.matricular_masivo_csv(self._filas(2), {})
        assert resultado.fue_exitosa is True

    def test_fue_exitosa_false_si_hay_errores(self):
        svc, _ = _make_svc()
        filas = [{"tipo_documento": "TI", "numero_documento": "", "nombre": "", "apellido": "", "genero": "", "grupo_codigo": ""}]
        resultado = svc.matricular_masivo_csv(filas, {})
        assert resultado.fue_exitosa is False
