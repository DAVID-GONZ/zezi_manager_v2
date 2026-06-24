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
        self._movimientos: list = []
        self._next_id = 1
        self._next_piar = 1
        self._next_mov = 1

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

    def registrar_movimiento(
        self, estudiante_id, grupo_origen_id, grupo_destino_id,
        tipo, motivo=None, usuario_registro_id=None,
    ):
        from datetime import datetime
        from src.domain.models.estudiante import MovimientoEstudiante
        mov = MovimientoEstudiante(
            id=self._next_mov,
            estudiante_id=estudiante_id,
            grupo_origen_id=grupo_origen_id,
            grupo_destino_id=grupo_destino_id,
            fecha_movimiento=datetime.now(),
            tipo_movimiento=tipo,
            motivo=motivo,
            usuario_registro_id=usuario_registro_id,
        )
        self._next_mov += 1
        self._movimientos.append(mov)
        return mov

    def listar_historial(self, estudiante_id):
        from src.domain.models.estudiante import MovimientoEstudianteInfoDTO
        return [
            MovimientoEstudianteInfoDTO(
                id=m.id,
                estudiante_id=m.estudiante_id,
                grupo_origen_codigo=str(m.grupo_origen_id) if m.grupo_origen_id else None,
                grupo_destino_codigo=str(m.grupo_destino_id) if m.grupo_destino_id else None,
                fecha_movimiento=m.fecha_movimiento,
                tipo_movimiento=m.tipo_movimiento,
                motivo=m.motivo,
                usuario_registro_id=m.usuario_registro_id,
            )
            for m in reversed(self._movimientos)
            if m.estudiante_id == estudiante_id
        ]

    def listar_por_grupo(
        self, grupo_id: int, solo_activos: bool = True, institucion_id: int | None = None
    ) -> list[Estudiante]:
        return [
            e for e in self._ests.values()
            if e.grupo_id == grupo_id
            and (institucion_id is None or e.institucion_id == institucion_id)
        ]

    def _aplica_filtro(self, e: Estudiante, filtro: FiltroEstudiantesDTO) -> bool:
        if filtro.institucion_id is not None and e.institucion_id != filtro.institucion_id:
            return False
        if filtro.grupo_id is not None and e.grupo_id != filtro.grupo_id:
            return False
        # grupos_ids None → sin restricción; lista vacía → ningún match.
        if filtro.grupos_ids is not None and e.grupo_id not in filtro.grupos_ids:
            return False
        return True

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        return [e for e in self._ests.values() if self._aplica_filtro(e, filtro)]

    def listar_resumenes(self, filtro: FiltroEstudiantesDTO) -> list[EstudianteResumenDTO]:
        return [
            EstudianteResumenDTO.desde_estudiante(e)
            for e in self._ests.values()
            if self._aplica_filtro(e, filtro)
        ]

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


class TestRBACActorRol:
    """RBAC ligero (paso_42): las mutaciones rechazan al profesor vía actor_rol.

    `actor_rol=None` (default) y los roles de gestión (director/coordinador)
    siguen funcionando; "profesor" es rechazado con ValueError accionable.
    """

    def _piar_dto(self, eid: int) -> NuevoPIARDTO:
        return NuevoPIARDTO(
            estudiante_id=eid, anio_id=1,
            descripcion_necesidad="Necesidad inicial",
        )

    # ── matricular ───────────────────────────────────────────────────────
    def test_matricular_rechaza_profesor(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="profesor"):
            svc.matricular(_dto("P1"), actor_rol="profesor")

    def test_matricular_acepta_director(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto("D1"), actor_rol="director")
        assert est.id is not None

    def test_matricular_acepta_coordinador(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto("C1"), actor_rol="coordinador")
        assert est.id is not None

    def test_matricular_acepta_none(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto("N1"), actor_rol=None)
        assert est.id is not None

    # ── actualizar ───────────────────────────────────────────────────────
    def test_actualizar_rechaza_profesor(self):
        from src.domain.models.estudiante import ActualizarEstudianteDTO
        svc, _ = _make_svc()
        est = svc.matricular(_dto("U1"))
        dto = ActualizarEstudianteDTO(nombre="Nuevo")
        with pytest.raises(ValueError, match="profesor"):
            svc.actualizar(est.id, dto, actor_rol="profesor")

    def test_actualizar_acepta_director(self):
        from src.domain.models.estudiante import ActualizarEstudianteDTO
        svc, _ = _make_svc()
        est = svc.matricular(_dto("U2"))
        dto = ActualizarEstudianteDTO(nombre="Nuevo")
        actualizado = svc.actualizar(est.id, dto, actor_rol="director")
        assert actualizado.nombre == "Nuevo"

    # ── actualizar_piar ──────────────────────────────────────────────────
    def test_actualizar_piar_rechaza_profesor(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto("PI1"))
        svc.registrar_piar(self._piar_dto(est.id))
        dto = ActualizarPIARDTO(descripcion_necesidad="Actualizada")
        with pytest.raises(ValueError, match="profesor"):
            svc.actualizar_piar(est.id, 1, dto, actor_rol="profesor")

    def test_actualizar_piar_acepta_coordinador(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto("PI2"))
        svc.registrar_piar(self._piar_dto(est.id))
        dto = ActualizarPIARDTO(descripcion_necesidad="Actualizada")
        piar = svc.actualizar_piar(est.id, 1, dto, actor_rol="coordinador")
        assert piar.descripcion_necesidad == "Actualizada"

    # ── matricular_masivo_csv ────────────────────────────────────────────
    def test_csv_rechaza_profesor_sin_recorrer_filas(self):
        svc, _ = _make_svc()
        filas = [{
            "tipo_documento": "TI", "numero_documento": "CSV1",
            "nombre": "Ana", "apellido": "Uno", "genero": "", "grupo_codigo": "",
        }]
        # Falla toda la carga con ValueError, no marca la fila como error.
        with pytest.raises(ValueError, match="profesor"):
            svc.matricular_masivo_csv(filas, {}, actor_rol="profesor")

    def test_csv_acepta_director(self):
        svc, _ = _make_svc()
        filas = [{
            "tipo_documento": "TI", "numero_documento": "CSV2",
            "nombre": "Ana", "apellido": "Uno", "genero": "", "grupo_codigo": "",
        }]
        resultado = svc.matricular_masivo_csv(filas, {}, actor_rol="director")
        assert resultado.exitosas == 1


class TestScopeGruposDocente:
    """Restricción del listado por conjunto de grupos (caso docente).

    Simula lo que la página de estudiantes pasa al filtro: el profesor solo ve
    estudiantes de los grupos donde tiene asignación (grupos_ids); el directivo
    no pasa grupos_ids (None) y ve todos los de su institución.
    """

    def _sembrar(self, svc):
        # Tres estudiantes en tres grupos distintos.
        e1 = svc.matricular(NuevoEstudianteDTO(numero_documento="A1", nombre="Ana", apellido="Uno", grupo_id=10))
        e2 = svc.matricular(NuevoEstudianteDTO(numero_documento="A2", nombre="Beto", apellido="Dos", grupo_id=20))
        e3 = svc.matricular(NuevoEstudianteDTO(numero_documento="A3", nombre="Cira", apellido="Tres", grupo_id=30))
        return e1, e2, e3

    def test_profesor_solo_ve_sus_grupos(self):
        svc, _ = _make_svc()
        self._sembrar(svc)
        filtro = FiltroEstudiantesDTO(grupos_ids=[10, 30])
        resultado = svc.listar_resumenes_plano(filtro)
        grupos = {r["grupo_id"] for r in resultado}
        assert grupos == {10, 30}
        assert len(resultado) == 2

    def test_docente_sin_asignaciones_no_ve_nada(self):
        svc, _ = _make_svc()
        self._sembrar(svc)
        # Lista vacía = docente sin asignaciones → 0 resultados.
        resultado = svc.listar_resumenes_plano(FiltroEstudiantesDTO(grupos_ids=[]))
        assert resultado == []

    def test_directivo_ve_todos(self):
        svc, _ = _make_svc()
        self._sembrar(svc)
        # grupos_ids None (directivo/admin) → ve todos los de su institución.
        resultado = svc.listar_resumenes_plano(FiltroEstudiantesDTO())
        assert len(resultado) == 3


# ===========================================================================
# Traslado entre grupos + historial (paso_43)
# ===========================================================================

class _FakeGrupo:
    """Stub mínimo de Grupo para el grupo_reader del servicio."""
    def __init__(self, gid, codigo, grado, institucion_id=None):
        self.id = gid
        self.codigo = codigo
        self.grado = grado
        self.institucion_id = institucion_id


def _make_svc_con_grupos(grupos: dict[int, _FakeGrupo]):
    repo = FakeEstudianteRepo()
    svc = EstudianteService(repo, grupo_reader=lambda gid: grupos.get(gid))
    return svc, repo


class TestTrasladar:
    def _grupos(self):
        # 10 y 11 mismo grado (6); 20 grado 7 (cambio de grado).
        return {
            10: _FakeGrupo(10, "6A", 6),
            11: _FakeGrupo(11, "6B", 6),
            20: _FakeGrupo(20, "7A", 7),
        }

    def test_mismo_grado_ok_registra_historial(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T1", nombre="Ana", apellido="Uno", grupo_id=10))
        out = svc.trasladar(
            est.id, 11, motivo="cambio de salón",
            usuario_id=7, actor_rol="director",
        )
        assert out.grupo_id == 11
        hist = svc.listar_historial(est.id)
        assert len(hist) == 1
        assert hist[0].tipo_movimiento.value == "TRASLADO"
        assert hist[0].motivo == "cambio de salón"
        assert hist[0].usuario_registro_id == 7

    def test_otro_grado_sin_confirmar_lanza(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T2", nombre="Ana", apellido="Dos", grupo_id=10))
        with pytest.raises(ValueError, match="otro grado"):
            svc.trasladar(est.id, 20, motivo=None, actor_rol="director")
        # No debe haber cambiado el grupo ni registrado historial.
        assert svc.get_by_id(est.id).grupo_id == 10
        assert svc.listar_historial(est.id) == []

    def test_otro_grado_confirmado_con_motivo_ok(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T3", nombre="Ana", apellido="Tres", grupo_id=10))
        out = svc.trasladar(
            est.id, 20, motivo="promoción",
            actor_rol="coordinador", permitir_cambio_grado=True,
        )
        assert out.grupo_id == 20
        hist = svc.listar_historial(est.id)
        assert len(hist) == 1
        assert hist[0].motivo == "promoción"

    def test_otro_grado_confirmado_sin_motivo_lanza(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T4", nombre="Ana", apellido="Cuatro", grupo_id=10))
        with pytest.raises(ValueError, match="motivo"):
            svc.trasladar(
                est.id, 20, motivo="   ",
                actor_rol="director", permitir_cambio_grado=True,
            )

    def test_profesor_rechazado(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T5", nombre="Ana", apellido="Cinco", grupo_id=10))
        with pytest.raises(ValueError, match="profesor"):
            svc.trasladar(est.id, 11, motivo="x", actor_rol="profesor")

    def test_grupo_destino_inexistente_lanza(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T6", nombre="Ana", apellido="Seis", grupo_id=10))
        with pytest.raises(ValueError, match="no existe"):
            svc.trasladar(est.id, 999, motivo="x", actor_rol="director")

    def test_mismo_grupo_lanza(self):
        grupos = self._grupos()
        svc, _ = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T7", nombre="Ana", apellido="Siete", grupo_id=10))
        with pytest.raises(ValueError, match="ya pertenece"):
            svc.trasladar(est.id, 10, motivo="x", actor_rol="director")

    def test_aislamiento_institucion(self):
        # Grupo destino de OTRA institución → rechazado al verificar pertenencia.
        from src.services.contexto_tenant import usar_institucion
        grupos = {
            10: _FakeGrupo(10, "6A", 6, institucion_id=1),
            30: _FakeGrupo(30, "6C", 6, institucion_id=2),
        }
        svc, _ = _make_svc_con_grupos(grupos)
        # El estudiante se matricula dentro del scope de la institución 1 para
        # que verificar_pertenencia del estudiante pase; el grupo destino (inst 2)
        # debe ser rechazado.
        with usar_institucion(1):
            est = svc.matricular(NuevoEstudianteDTO(
                numero_documento="T8", nombre="Ana", apellido="Ocho", grupo_id=10))
            with pytest.raises(Exception):
                svc.trasladar(est.id, 30, motivo="x", actor_rol="director")

    def test_notas_siguen_al_estudiante_tras_traslado(self):
        # El estudiante conserva su id tras el traslado; cualquier registro que
        # cuelgue de estudiante_id sigue siendo accesible por ese mismo id.
        grupos = self._grupos()
        svc, repo = _make_svc_con_grupos(grupos)
        est = svc.matricular(NuevoEstudianteDTO(
            numero_documento="T9", nombre="Ana", apellido="Nueve", grupo_id=10))
        id_antes = est.id
        svc.registrar_piar(NuevoPIARDTO(
            estudiante_id=id_antes, anio_id=1,
            descripcion_necesidad="Necesidad previa al traslado"))
        out = svc.trasladar(id_antes, 11, motivo="cambio", actor_rol="director")
        assert out.id == id_antes
        # El registro que colgaba del estudiante sigue accesible por su id.
        assert svc.get_piar(id_antes, 1) is not None
        assert repo.get_by_id(id_antes).grupo_id == 11
