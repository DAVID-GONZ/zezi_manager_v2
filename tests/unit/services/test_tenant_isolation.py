"""
Tests de aislamiento multi-tenant — tenant_04_tests_aislamiento (Fase 1C).

Verifica que los servicios auto-scopean correctamente por institución:
  - con scope fijado (usar_institucion(N)) cada servicio solo ve datos del tenant N
  - admin (scope None) ve datos de todas las instituciones
  - los métodos de puerto con institucion_id obligatorio fallan con TypeError
    si se llaman sin él
  - ningún repo implementado declara listar_/contar_/buscar_ con default=None
    en institucion_id
"""
from __future__ import annotations

import pathlib
import re

import pytest

from src.domain.models.configuracion import ConfiguracionAnio
from src.domain.models.convivencia import CategoriaObservacion
from src.domain.models.estudiante import EstadoMatricula, EstudianteResumenDTO, FiltroEstudiantesDTO
from src.domain.models.tenant import TenantScope
from src.domain.models.usuario import FiltroUsuariosDTO, Rol, UsuarioResumenDTO
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.ports.usuario_repo import IUsuarioRepository
from src.services.configuracion_service import ConfiguracionService
from src.services.contexto_tenant import activar_institucion, usar_institucion
from src.services.convivencia_service import ConvivenciaService
from src.services.estudiante_service import EstudianteService
from src.services.usuario_service import UsuarioService


# =============================================================================
# Reset de scope entre tests
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_scope():
    """Cada test arranca y termina con scope None."""
    activar_institucion(None)
    yield
    activar_institucion(None)


# =============================================================================
# Fake repos en memoria
# =============================================================================


class FakeUsuarioRepo(IUsuarioRepository):
    """
    Repo en memoria que filtra por institucion_id en listar_resumenes.
    Almacena (institucion_id, UsuarioResumenDTO).
    """

    def __init__(self) -> None:
        self._resumenes: list[tuple[int | None, UsuarioResumenDTO]] = []

    def agregar(self, institucion_id: int | None, resumen: UsuarioResumenDTO) -> None:
        self._resumenes.append((institucion_id, resumen))

    # ── métodos usados por los tests ──────────────────────────────────────────

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        if filtro.institucion_id is None:
            return [r for _, r in self._resumenes]
        return [r for inst, r in self._resumenes if inst == filtro.institucion_id]

    def listar_filtrado(self, filtro: FiltroUsuariosDTO):
        return []

    # ── métodos abstractos no usados ──────────────────────────────────────────

    def get_by_id(self, usuario_id):
        return None

    def get_by_username(self, username):
        return None

    def get_by_email(self, email):
        return None

    def existe_usuario(self, username):
        return False

    def listar_docentes_info(self, institucion_id, periodo_id=None, solo_activos=True):
        return []

    def get_docente_info(self, usuario_id, institucion_id, periodo_id=None):
        return None

    def listar_asignaciones_docente(self, usuario_id, institucion_id, periodo_id=None):
        return []

    def guardar(self, usuario):
        return usuario

    def actualizar(self, usuario):
        return usuario

    def actualizar_carga(self, usuario_id, carga_horaria_max, horas_extra):
        return False

    def cambiar_rol(self, usuario_id, nuevo_rol):
        return False

    def desactivar(self, usuario_id):
        return False

    def reactivar(self, usuario_id):
        return False

    def marcar_debe_cambiar_password(self, usuario_id, valor):
        return False

    def get_password_hash(self, usuario_id):
        return None

    def actualizar_password_hash(self, usuario_id, nuevo_hash):
        return False


class FakeEstudianteRepo(IEstudianteRepository):
    """
    Repo en memoria que filtra estudiantes por institucion_id en listar_resumenes.
    Almacena (institucion_id, EstudianteResumenDTO).
    """

    def __init__(self) -> None:
        self._resumenes: list[tuple[int | None, EstudianteResumenDTO]] = []

    def agregar(self, institucion_id: int | None, resumen: EstudianteResumenDTO) -> None:
        self._resumenes.append((institucion_id, resumen))

    # ── métodos usados por los tests ──────────────────────────────────────────

    def listar_resumenes(self, filtro: FiltroEstudiantesDTO) -> list[EstudianteResumenDTO]:
        if filtro.institucion_id is None:
            return [r for _, r in self._resumenes]
        return [r for inst, r in self._resumenes if inst == filtro.institucion_id]

    def listar_filtrado(self, filtro):
        return []

    # ── métodos abstractos no usados ──────────────────────────────────────────

    def get_by_id(self, estudiante_id):
        return None

    def get_by_documento(self, numero_documento, institucion_id):
        return None

    def existe_documento(self, numero_documento, institucion_id):
        return False

    def get_resumen(self, estudiante_id):
        return None

    def listar_por_grupo(self, grupo_id, institucion_id, solo_activos=True):
        return []

    def contar_por_grupo(self, grupo_id, institucion_id, solo_activos=True):
        return 0

    def guardar(self, estudiante):
        return estudiante

    def actualizar(self, estudiante):
        return estudiante

    def actualizar_estado_matricula(self, estudiante_id, estado):
        return False

    def asignar_grupo(self, estudiante_id, grupo_id):
        return False

    def registrar_movimiento(
        self,
        estudiante_id,
        grupo_origen_id,
        grupo_destino_id,
        tipo,
        motivo=None,
        usuario_registro_id=None,
    ):
        raise NotImplementedError

    def listar_historial(self, estudiante_id):
        return []

    def get_piar(self, estudiante_id, anio_id):
        return None

    def listar_piars(self, estudiante_id):
        return []

    def existe_piar(self, estudiante_id, anio_id):
        return False

    def guardar_piar(self, piar):
        return piar

    def actualizar_piar(self, piar):
        return piar


class FakeConvRepo(IConvivenciaRepository):
    """
    Repo en memoria para categorías de convivencia.
    listar_categorias filtra por institucion_id (int) o devuelve todo ("*").
    """

    def __init__(self) -> None:
        self._categorias: list[tuple[int | None, CategoriaObservacion]] = []

    def agregar(self, institucion_id: int | None, cat: CategoriaObservacion) -> None:
        self._categorias.append((institucion_id, cat))

    # ── métodos usados por los tests ──────────────────────────────────────────

    def listar_categorias(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[CategoriaObservacion]:
        if institucion_id == "*":
            cats = [c for _, c in self._categorias]
        else:
            cats = [c for inst, c in self._categorias if inst == institucion_id]
        if solo_activas:
            return [c for c in cats if c.activa]
        return cats

    # ── métodos abstractos no usados ──────────────────────────────────────────

    def get_observacion(self, observacion_id):
        return None

    def get_observacion_por_asignacion(self, estudiante_id, asignacion_id, periodo_id):
        return None

    def listar_observaciones_por_estudiante(self, estudiante_id, periodo_id=None, solo_publicas=False):
        return []

    def listar_observaciones_por_grupo(self, grupo_id, periodo_id=None, solo_publicas=False):
        return []

    def guardar_observacion(self, observacion):
        return observacion

    def actualizar_observacion(self, observacion):
        return observacion

    def eliminar_observacion(self, observacion_id):
        return False

    def get_registro(self, registro_id):
        return None

    def listar_registros(self, filtro, institucion_id):
        return []

    def contar_registros(self, filtro, institucion_id):
        return 0

    def guardar_registro(self, registro):
        return registro

    def actualizar_registro(self, registro):
        return registro

    def eliminar_registro(self, registro_id):
        return False

    def get_nota(self, estudiante_id, periodo_id):
        return None

    def listar_notas_por_estudiante(self, estudiante_id):
        return []

    def listar_notas_por_grupo(self, grupo_id, periodo_id):
        return []

    def guardar_nota(self, nota):
        return nota

    def get_categoria(self, categoria_id):
        return None

    def guardar_categoria(self, categoria):
        return categoria

    def actualizar_categoria(self, categoria):
        return categoria

    def listar_plantillas(self, institucion_id, categoria_id=None, solo_activas=True):
        return []

    def get_plantilla(self, plantilla_id):
        return None

    def guardar_plantilla(self, plantilla):
        return plantilla

    def actualizar_plantilla(self, plantilla):
        return plantilla

    def incrementar_uso_plantilla(self, plantilla_id):
        pass

    def listar_tipos_situacion(self, institucion_id, solo_activas=True):
        return []

    def get_tipo_situacion(self, tipo_situacion_id):
        return None

    def guardar_tipo_situacion(self, tipo_situacion):
        return tipo_situacion

    def actualizar_tipo_situacion(self, tipo_situacion):
        return tipo_situacion

    def listar_entradas_seguimiento(self, registro_id):
        return []

    def guardar_entrada_seguimiento(self, entrada):
        return entrada

    def listar_medidas(self, institucion_id, solo_activas=True):
        return []

    def get_medida(self, medida_id):
        return None

    def guardar_medida(self, medida):
        return medida

    def actualizar_medida(self, medida):
        return medida

    def resolver_nombres_usuario(self, usuario_ids):
        return {}

    def resolver_nombres_asignatura(self, asignacion_ids):
        return {}

    def resolver_grupo_grado(self, grupo_id):
        return {}

    def resolver_acudiente_principal(self, estudiante_id):
        return {}


class FakeConfigRepo(IConfiguracionRepository):
    """
    Repo en memoria para configuración de año activo por institución.
    """

    def __init__(self) -> None:
        self._configs: dict[int, ConfiguracionAnio] = {}

    def agregar(self, institucion_id: int, config: ConfiguracionAnio) -> None:
        self._configs[institucion_id] = config

    # ── métodos usados por los tests ──────────────────────────────────────────

    def get_activa(self, institucion_id: TenantScope) -> ConfiguracionAnio | None:
        if institucion_id == "*":
            return next(iter(self._configs.values()), None)
        return self._configs.get(institucion_id)

    def listar(self, institucion_id: TenantScope) -> list[ConfiguracionAnio]:
        if institucion_id == "*":
            return list(self._configs.values())
        c = self._configs.get(institucion_id)
        return [c] if c else []

    # ── métodos abstractos no usados ──────────────────────────────────────────

    def get_by_id(self, anio_id):
        return None

    def get_by_anio(self, institucion_id, anio):
        return None

    def guardar(self, config):
        return config

    def actualizar(self, config):
        return config

    def activar(self, anio_id):
        return False

    def listar_niveles(self, anio_id):
        return []

    def get_nivel(self, nivel_id):
        return None

    def guardar_nivel(self, nivel):
        return nivel

    def actualizar_nivel(self, nivel):
        return nivel

    def eliminar_nivel(self, nivel_id):
        return False

    def reemplazar_niveles(self, anio_id, niveles):
        return []

    def clasificar_nota(self, nota, anio_id):
        return None

    def get_criterios(self, anio_id):
        return None

    def guardar_criterios(self, criterios):
        return criterios

    def get_numero_periodos(self, anio_id):
        return 4

    def guardar_numero_periodos(self, anio_id, numero_periodos, pesos_iguales=True):
        pass


# =============================================================================
# Fixtures de datos de prueba (dos instituciones)
# =============================================================================


@pytest.fixture()
def usuario_repo() -> FakeUsuarioRepo:
    repo = FakeUsuarioRepo()
    # Institución 1
    repo.agregar(
        1,
        UsuarioResumenDTO(
            id=1,
            usuario="ana",
            nombre_completo="Ana García",
            rol=Rol.DIRECTOR,
            activo=True,
            institucion_id=1,
        ),
    )
    repo.agregar(
        1,
        UsuarioResumenDTO(
            id=2,
            usuario="luis",
            nombre_completo="Luis Pérez",
            rol=Rol.PROFESOR,
            activo=True,
            institucion_id=1,
        ),
    )
    # Institución 2
    repo.agregar(
        2,
        UsuarioResumenDTO(
            id=3,
            usuario="sara",
            nombre_completo="Sara López",
            rol=Rol.DIRECTOR,
            activo=True,
            institucion_id=2,
        ),
    )
    return repo


@pytest.fixture()
def estudiante_repo() -> FakeEstudianteRepo:
    repo = FakeEstudianteRepo()
    # Institución 1
    repo.agregar(
        1,
        EstudianteResumenDTO(
            id=1,
            id_publico="E001",
            documento_display="11111111",
            nombre_completo="Est Inst1 A",
            genero=None,
            grupo_id=None,
            estado_matricula=EstadoMatricula.ACTIVO,
            posee_piar=False,
        ),
    )
    repo.agregar(
        1,
        EstudianteResumenDTO(
            id=2,
            id_publico="E002",
            documento_display="11111112",
            nombre_completo="Est Inst1 B",
            genero=None,
            grupo_id=None,
            estado_matricula=EstadoMatricula.ACTIVO,
            posee_piar=False,
        ),
    )
    # Institución 2
    repo.agregar(
        2,
        EstudianteResumenDTO(
            id=3,
            id_publico="E003",
            documento_display="22222221",
            nombre_completo="Est Inst2 A",
            genero=None,
            grupo_id=None,
            estado_matricula=EstadoMatricula.ACTIVO,
            posee_piar=False,
        ),
    )
    return repo


@pytest.fixture()
def conv_repo() -> FakeConvRepo:
    repo = FakeConvRepo()
    repo.agregar(1, CategoriaObservacion(id=1, nombre="Comportamiento Inst1", activa=True, institucion_id=1))
    repo.agregar(2, CategoriaObservacion(id=2, nombre="Comportamiento Inst2", activa=True, institucion_id=2))
    return repo


@pytest.fixture()
def config_repo() -> FakeConfigRepo:
    repo = FakeConfigRepo()
    repo.agregar(1, ConfiguracionAnio(id=1, anio=2025, institucion_id=1, activo=True))
    repo.agregar(2, ConfiguracionAnio(id=2, anio=2026, institucion_id=2, activo=True))
    return repo


# =============================================================================
# Tests de aislamiento por servicio
# =============================================================================


def test_listar_resumenes_usuarios_scopeado(usuario_repo: FakeUsuarioRepo) -> None:
    """Con usar_institucion(1), UsuarioService solo ve usuarios de inst 1."""
    svc = UsuarioService(repo=usuario_repo)
    with usar_institucion(1):
        result = svc.listar_resumenes(FiltroUsuariosDTO())
    ids = {r.id for r in result}
    assert 1 in ids
    assert 2 in ids
    assert 3 not in ids, "usuario de inst 2 no debe aparecer con scope=1"


def test_listar_resumenes_estudiantes_scopeado(estudiante_repo: FakeEstudianteRepo) -> None:
    """Con usar_institucion(1), EstudianteService solo ve estudiantes de inst 1."""
    svc = EstudianteService(repo=estudiante_repo)
    with usar_institucion(1):
        result = svc.listar_resumenes(FiltroEstudiantesDTO())
    ids = {r.id for r in result}
    assert 1 in ids
    assert 2 in ids
    assert 3 not in ids, "estudiante de inst 2 no debe aparecer con scope=1"


def test_listar_categorias_convivencia_scopeado(conv_repo: FakeConvRepo) -> None:
    """Con usar_institucion(1), ConvivenciaService solo ve categorías de inst 1."""
    svc = ConvivenciaService(repo=conv_repo)
    with usar_institucion(1):
        result = svc.listar_categorias(solo_activas=False)
    nombres = {c.nombre for c in result}
    assert "Comportamiento Inst1" in nombres
    assert "Comportamiento Inst2" not in nombres, "cat de inst 2 no debe aparecer con scope=1"


def test_get_activa_config_scopeada(config_repo: FakeConfigRepo) -> None:
    """Con usar_institucion(1), ConfiguracionService.get_activa retorna el año de inst 1."""
    svc = ConfiguracionService(repo=config_repo)
    with usar_institucion(1):
        config = svc.get_activa()
    assert config.anio == 2025
    assert config.institucion_id == 1


def test_admin_ve_todas_las_instituciones(usuario_repo: FakeUsuarioRepo) -> None:
    """Con usar_institucion(None), listar_resumenes retorna usuarios de inst 1 y 2."""
    svc = UsuarioService(repo=usuario_repo)
    with usar_institucion(None):
        result = svc.listar_resumenes(FiltroUsuariosDTO())
    ids = {r.id for r in result}
    assert 1 in ids, "usuario inst 1 debe aparecer cuando scope=None (admin)"
    assert 3 in ids, "usuario inst 2 debe aparecer cuando scope=None (admin)"


def test_scope_none_con_tenant_scope_obligatorio() -> None:
    """listar_categorias del puerto sin institucion_id levanta TypeError."""
    repo = FakeConvRepo()
    with pytest.raises(TypeError):
        repo.listar_categorias()  # falta institucion_id obligatorio


def test_ningun_listar_con_default_none() -> None:
    """Ningún repo implementado debe tener listar_/contar_/buscar_ con default=None en institucion_id."""
    repos_dir = pathlib.Path("src/infrastructure/db/repositories")
    pattern = re.compile(r"def\s+(?:listar_|contar_|buscar_)\w+\s*\(.*institucion_id.*=\s*None")
    violaciones = []
    for f in repos_dir.glob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                violaciones.append(f"{f.name}:{i}: {line.strip()}")
    assert not violaciones, "Metodos con default None:\n" + "\n".join(violaciones)
