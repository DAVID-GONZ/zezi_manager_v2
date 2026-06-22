"""
Tests de aislamiento por objeto entre instituciones (paso_36 — hallazgo E).

Verifican que las operaciones por `id` (actualizar / eliminar / desactivar /
get_by_id) sobre entidades con `institucion_id` directo rechacen objetos de
OTRA institución cuando hay scope de sesión activo, y las permitan con los
propios. El admin (scope None) opera cross-tenant. Un `institucion_id` forjado
en el objeto que pasa el caller NO burla el check (se usa el del repo).
"""
from __future__ import annotations

import pytest

from src.domain.models.usuario import Usuario, Rol, ActualizarUsuarioDTO
from src.domain.models.estudiante import Estudiante, ActualizarEstudianteDTO
from src.domain.models.infraestructura import Grupo, Asignatura, Sala, PlantillaFranja
from src.domain.models.configuracion import ConfiguracionAnio

from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository

from src.services.usuario_service import UsuarioService
from src.services.estudiante_service import EstudianteService
from src.services.infraestructura_service import InfraestructuraService
from src.services.configuracion_service import ConfiguracionService
from src.services.contexto_tenant import (
    activar_institucion,
    usar_institucion,
    OperacionFueraDeInstitucionError,
)

INST_A = 1
INST_B = 2


@pytest.fixture(autouse=True)
def _reset_scope():
    activar_institucion(None)
    yield
    activar_institucion(None)


# ---------------------------------------------------------------------------
# Fakes mínimos: sólo implementan los métodos bajo prueba. Tras definir cada
# clase se vacía `__abstractmethods__` para poder instanciarla sin proveer todo
# el contrato del puerto (los métodos no usados quedarían como abstractos).
# ---------------------------------------------------------------------------

class _FakeUsuarioRepo(IUsuarioRepository):
    def __init__(self):
        self.data: dict[int, Usuario] = {}

    def get_by_id(self, uid):
        return self.data.get(uid)

    def actualizar(self, u):
        self.data[u.id] = u
        return u

    def desactivar(self, uid):
        u = self.data[uid]
        self.data[uid] = u.model_copy(update={"activo": False})

    def reactivar(self, uid):
        u = self.data[uid]
        self.data[uid] = u.model_copy(update={"activo": True})

    def cambiar_rol(self, uid, rol):
        u = self.data[uid]
        self.data[uid] = u.model_copy(update={"rol": rol})


class _FakeEstudianteRepo(IEstudianteRepository):
    def __init__(self):
        self.data: dict[int, Estudiante] = {}

    def get_by_id(self, eid):
        return self.data.get(eid)

    def actualizar(self, e):
        self.data[e.id] = e
        return e


class _FakeInfraRepo(IInfraestructuraRepository):
    def __init__(self):
        self.grupos: dict[int, Grupo] = {}
        self.asignaturas: dict[int, Asignatura] = {}
        self.salas: dict[int, Sala] = {}
        self.plantillas: dict[int, PlantillaFranja] = {}
        self.eliminados: list[str] = []

    # grupos
    def get_grupo(self, gid):
        return self.grupos.get(gid)

    def actualizar_grupo(self, g):
        self.grupos[g.id] = g
        return g

    def eliminar_grupo(self, gid):
        self.eliminados.append(f"grupo:{gid}")
        return self.grupos.pop(gid, None) is not None

    # asignaturas
    def get_asignatura(self, aid):
        return self.asignaturas.get(aid)

    def actualizar_asignatura(self, a):
        self.asignaturas[a.id] = a
        return a

    def eliminar_asignatura(self, aid):
        self.eliminados.append(f"asig:{aid}")
        return self.asignaturas.pop(aid, None) is not None

    # salas
    def get_sala(self, sid):
        return self.salas.get(sid)

    def actualizar_sala(self, s):
        self.salas[s.id] = s
        return s

    def eliminar_sala(self, sid):
        self.eliminados.append(f"sala:{sid}")
        return self.salas.pop(sid, None) is not None

    # plantillas
    def get_plantilla_franja(self, pid):
        return self.plantillas.get(pid)

    def eliminar_plantilla_franja(self, pid):
        self.eliminados.append(f"plantilla:{pid}")
        return self.plantillas.pop(pid, None) is not None


class _FakeConfigRepo(IConfiguracionRepository):
    def __init__(self):
        self.data: dict[int, ConfiguracionAnio] = {}
        self.activados: list[int] = []

    def get_by_id(self, aid):
        return self.data.get(aid)

    def activar(self, aid):
        self.activados.append(aid)

    def actualizar(self, c):
        self.data[c.id] = c
        return c


for _cls in (_FakeUsuarioRepo, _FakeEstudianteRepo, _FakeInfraRepo, _FakeConfigRepo):
    _cls.__abstractmethods__ = frozenset()


# ---------------------------------------------------------------------------
# Builders de entidades en dos instituciones (A y B)
# ---------------------------------------------------------------------------

def _usuario(uid, inst):
    return Usuario(
        id=uid, usuario=f"u{uid}", nombre_completo="Usuario Prueba",
        rol=Rol.PROFESOR, activo=True, institucion_id=inst,
    )


def _estudiante(eid, inst):
    return Estudiante(
        id=eid, tipo_documento="TI", numero_documento=f"D{eid}",
        nombre="Nombre", apellido="Apellido", institucion_id=inst,
    )


def _grupo(gid, inst):
    return Grupo(id=gid, codigo=f"60{gid}", grado=6, institucion_id=inst)


def _asignatura(aid, inst):
    return Asignatura(id=aid, nombre=f"Materia {aid}", area_id=1, institucion_id=inst)


def _sala(sid, inst):
    return Sala(id=sid, nombre=f"Salon {sid}", institucion_id=inst)


def _anio(aid, inst):
    return ConfiguracionAnio(id=aid, anio=2026, institucion_id=inst)


# ===========================================================================
# Usuarios
# ===========================================================================

class TestUsuarioAislamiento:
    def _svc(self):
        repo = _FakeUsuarioRepo()
        repo.data[10] = _usuario(10, INST_A)
        repo.data[20] = _usuario(20, INST_B)
        return UsuarioService(repo), repo

    def test_director_no_lee_usuario_de_otra_institucion(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.get_by_id(20)

    def test_director_lee_usuario_propio(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            assert svc.get_by_id(10).id == 10

    def test_director_no_actualiza_usuario_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.actualizar(20, ActualizarUsuarioDTO(nombre_completo="Hack"))

    def test_director_no_desactiva_usuario_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.desactivar(20)

    def test_admin_scope_none_opera_con_ambos(self):
        svc, _ = self._svc()
        # scope None
        assert svc.get_by_id(10).id == 10
        assert svc.get_by_id(20).id == 20


# ===========================================================================
# Estudiantes
# ===========================================================================

class TestEstudianteAislamiento:
    def _svc(self):
        repo = _FakeEstudianteRepo()
        repo.data[10] = _estudiante(10, INST_A)
        repo.data[20] = _estudiante(20, INST_B)
        return EstudianteService(repo), repo

    def test_director_no_lee_estudiante_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.get_by_id(20)

    def test_director_actualiza_estudiante_propio(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            out = svc.actualizar(10, ActualizarEstudianteDTO(nombre="Nuevo"))
            assert out.nombre == "Nuevo"

    def test_director_no_actualiza_estudiante_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.actualizar(20, ActualizarEstudianteDTO(nombre="Hack"))

    def test_admin_opera_con_ambos(self):
        svc, _ = self._svc()
        assert svc.get_by_id(10).id == 10
        assert svc.get_by_id(20).id == 20


# ===========================================================================
# Infraestructura: grupos / asignaturas / salas / plantillas
# ===========================================================================

class TestInfraAislamiento:
    def _svc(self):
        repo = _FakeInfraRepo()
        repo.grupos[10] = _grupo(10, INST_A)
        repo.grupos[20] = _grupo(20, INST_B)
        repo.asignaturas[10] = _asignatura(10, INST_A)
        repo.asignaturas[20] = _asignatura(20, INST_B)
        repo.salas[10] = _sala(10, INST_A)
        repo.salas[20] = _sala(20, INST_B)
        repo.plantillas[10] = PlantillaFranja(
            id=10, nombre="P-A", jornada="UNICA",
            dias_activos=["Lunes"], institucion_id=INST_A,
        )
        repo.plantillas[20] = PlantillaFranja(
            id=20, nombre="P-B", jornada="UNICA",
            dias_activos=["Lunes"], institucion_id=INST_B,
        )
        return InfraestructuraService(repo), repo

    def test_director_no_elimina_grupo_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.eliminar_grupo(20)

    def test_director_elimina_grupo_propio(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            assert svc.eliminar_grupo(10) is True

    def test_director_no_actualiza_grupo_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.actualizar_grupo(_grupo(20, INST_B))

    def test_actualizar_grupo_no_permite_mover_institucion(self):
        # institucion_id forjado a A para un grupo que es de B → debe leerse
        # el del repo (B) y rechazar; nunca mover el grupo a A.
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            forjado = _grupo(20, INST_A)  # mismo id 20 pero institucion forjada
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.actualizar_grupo(forjado)

    def test_actualizar_grupo_preserva_institucion_persistida(self):
        # Director de A actualiza su grupo pero envía institucion_id forjado a B.
        # El servicio debe preservar la institución persistida (A).
        svc, repo = self._svc()
        with usar_institucion(INST_A):
            forjado = _grupo(10, INST_B)  # grupo de A, intenta moverse a B
            out = svc.actualizar_grupo(forjado)
            assert out.institucion_id == INST_A
            assert repo.grupos[10].institucion_id == INST_A

    def test_director_no_elimina_asignatura_ajena(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.eliminar_asignatura(20)

    def test_director_no_elimina_sala_ajena(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.eliminar_sala(20)

    def test_director_no_elimina_plantilla_ajena(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.eliminar_plantilla(20)

    def test_admin_elimina_de_ambas(self):
        svc, _ = self._svc()
        # scope None
        assert svc.eliminar_grupo(10) is True
        assert svc.eliminar_grupo(20) is True


# ===========================================================================
# Configuración de año
# ===========================================================================

class TestConfiguracionAislamiento:
    def _svc(self):
        repo = _FakeConfigRepo()
        repo.data[10] = _anio(10, INST_A)
        repo.data[20] = _anio(20, INST_B)
        return ConfiguracionService(repo), repo

    def test_director_no_activa_anio_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.activar_anio(20)

    def test_director_activa_anio_propio(self):
        svc, repo = self._svc()
        with usar_institucion(INST_A):
            svc.activar_anio(10)
            assert 10 in repo.activados

    def test_director_no_lee_anio_ajeno(self):
        svc, _ = self._svc()
        with usar_institucion(INST_A):
            with pytest.raises(OperacionFueraDeInstitucionError):
                svc.get_by_id(20)

    def test_admin_opera_con_ambos(self):
        svc, _ = self._svc()
        assert svc.get_by_id(10).id == 10
        assert svc.get_by_id(20).id == 20
