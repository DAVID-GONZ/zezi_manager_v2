"""
tests/unit/services/test_registros_boletin.py
=============================================
Tests para convivencia_29 — política de registros de comportamiento en boletín.

Cubre:
  - PreferenciasDTO: defaults de los 4 campos nuevos.
  - CLAVES_CONOCIDAS: las 4 claves están registradas.
  - _inferir_categoria / _inferir_tipo: categoría CONVIVENCIA y tipos correctos.
  - ConvivenciaService._registros_informables_periodo: todos los ramos de política.
  - InformeService.convivencia_boletin: devuelve clave "registros".
  - InformeService.convivencia_boletin_anual: devuelve clave "registros".
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from src.domain.models.convivencia import (
    TIPO_REGISTRO_DISPLAY,
    FiltroConvivenciaDTO,
    ObservacionPeriodo,
    RegistroComportamiento,
    TipoRegistro,
)
from src.domain.models.preferencia_institucion import (
    CategoriaPreferencia,
    PreferenciasDTO,
    TipoValor,
)
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.services.convivencia_service import ConvivenciaService
from src.services.informe_service import InformeService
from src.services.preferencias_institucion_service import (
    CLAVES_CONOCIDAS,
    PreferenciasInstitucionService,
    _inferir_categoria,
    _inferir_tipo,
)

# ===========================================================================
# Fakes
# ===========================================================================

class _FakeConvRepo(IConvivenciaRepository):
    """Fake mínimo de IConvivenciaRepository para tests de registros en boletín."""

    def __init__(self, registros=None, obs=None, nota=None):
        self._registros: list[RegistroComportamiento] = registros or []
        self._obs: list[ObservacionPeriodo] = obs or []
        self._nota = nota

    # Registros
    def get_registro(self, rid): return None
    def listar_registros(self, filtro: FiltroConvivenciaDTO, institucion_id=None):
        return list(self._registros)
    def contar_registros(self, filtro, institucion_id=None): return len(self._registros)
    def guardar_registro(self, r): return r
    def actualizar_registro(self, r): return r
    def eliminar_registro(self, rid): return False

    # Observaciones
    def get_observacion(self, oid): return None
    def get_observacion_por_asignacion(self, est, asig, per): return None
    def listar_observaciones_por_estudiante(self, est, per=None, solo_publicas=False):
        return list(self._obs)
    def listar_observaciones_por_grupo(self, grupo_id, periodo_id=None, solo_publicas=False): return []
    def guardar_observacion(self, o): return o
    def actualizar_observacion(self, o): return o
    def eliminar_observacion(self, oid): return False

    # Notas
    def get_nota(self, est, per): return self._nota
    def listar_notas_por_estudiante(self, est): return []
    def listar_notas_por_grupo(self, grupo_id, per): return []
    def guardar_nota(self, n): return n

    # Categorías
    def listar_categorias(self, solo_activas=True, institucion_id=None): return []
    def get_categoria(self, cat_id): return None
    def guardar_categoria(self, c): return c
    def actualizar_categoria(self, c): return c

    # Plantillas
    def listar_plantillas(self, categoria_id=None, solo_activas=True, institucion_id=None): return []
    def get_plantilla(self, pid): return None
    def guardar_plantilla(self, p): return p
    def actualizar_plantilla(self, p): return p
    def incrementar_uso_plantilla(self, pid): pass


def _make_registro(
    id_: int,
    tipo: TipoRegistro,
    fecha: date | None = None,
    acudiente_notificado: bool = False,
    descripcion: str = "desc",
) -> RegistroComportamiento:
    requiere_firma = False if tipo == TipoRegistro.DESCARGO else False
    return RegistroComportamiento(
        id=id_,
        estudiante_id=1,
        grupo_id=10,
        periodo_id=5,
        tipo=tipo,
        descripcion=descripcion,
        requiere_firma=requiere_firma,
        acudiente_notificado=acudiente_notificado,
        fecha=fecha or date(2026, 6, 1),
    )


def _make_svc(registros=None, prefs: PreferenciasDTO | None = None) -> ConvivenciaService:
    """Construye un ConvivenciaService con prefs inyectadas.

    Para aislar del contexto_tenant (que retorna None en unit-tests) se
    monkey-patchea ``_get_prefs_convivencia`` directamente cuando se
    proporcionan prefs explícitas.
    """
    repo = _FakeConvRepo(registros=registros)
    svc = ConvivenciaService(repo=repo)
    if prefs is not None:
        svc._get_prefs_convivencia = lambda: prefs  # type: ignore[method-assign]
    return svc


# ===========================================================================
# T1 — PreferenciasDTO defaults
# ===========================================================================

class TestPreferenciasDefaults:

    def test_registros_boletin_tipos_default(self):
        dto = PreferenciasDTO()
        assert "fortaleza" in dto.registros_boletin_tipos
        assert "compromiso" in dto.registros_boletin_tipos
        assert "citacion_acudiente" in dto.registros_boletin_tipos
        assert "dificultad" not in dto.registros_boletin_tipos
        assert "descargo" not in dto.registros_boletin_tipos

    def test_registros_boletin_dificultad_requiere_notificacion_default(self):
        assert PreferenciasDTO().registros_boletin_dificultad_requiere_notificacion is True

    def test_registros_boletin_incluye_descargo_default(self):
        assert PreferenciasDTO().registros_boletin_incluye_descargo is False

    def test_registros_boletin_dedup_observaciones_default(self):
        assert PreferenciasDTO().registros_boletin_dedup_observaciones is True

    def test_defaults_independientes_entre_instancias(self):
        """default_factory garantiza que las listas no se comparten."""
        a = PreferenciasDTO()
        b = PreferenciasDTO()
        a.registros_boletin_tipos.append("extra")
        assert "extra" not in b.registros_boletin_tipos


# ===========================================================================
# T2 — CLAVES_CONOCIDAS y helpers de inferencia
# ===========================================================================

class TestClavesBoletin:

    def test_claves_en_conocidas(self):
        for clave in (
            "registros_boletin_tipos",
            "registros_boletin_dificultad_requiere_notificacion",
            "registros_boletin_incluye_descargo",
            "registros_boletin_dedup_observaciones",
        ):
            assert clave in CLAVES_CONOCIDAS, f"{clave!r} debe estar en CLAVES_CONOCIDAS"

    def test_inferir_categoria_convivencia(self):
        for clave in (
            "registros_boletin_tipos",
            "registros_boletin_dificultad_requiere_notificacion",
            "registros_boletin_incluye_descargo",
            "registros_boletin_dedup_observaciones",
        ):
            assert _inferir_categoria(clave) == CategoriaPreferencia.CONVIVENCIA

    def test_inferir_tipo_json(self):
        assert _inferir_tipo("registros_boletin_tipos") == TipoValor.JSON

    def test_inferir_tipo_bool(self):
        for clave in (
            "registros_boletin_dificultad_requiere_notificacion",
            "registros_boletin_incluye_descargo",
            "registros_boletin_dedup_observaciones",
        ):
            assert _inferir_tipo(clave) == TipoValor.BOOL, f"{clave!r} debe ser BOOL"

    def test_set_clave_nueva_no_lanza(self):
        """El servicio acepta las 4 claves nuevas sin lanzar ValueError."""
        from src.domain.models.preferencia_institucion import (
            ActualizarPreferenciaDTO,
            PreferenciaInstitucion,
        )
        repo = MagicMock()
        repo.get.return_value = None
        repo.set.return_value = PreferenciaInstitucion(
            id=1, institucion_id=1,
            categoria=CategoriaPreferencia.CONVIVENCIA,
            clave="registros_boletin_tipos",
            valor='["fortaleza"]',
            tipo_valor=TipoValor.JSON,
        )
        svc = PreferenciasInstitucionService(repo)
        result = svc.set(1, ActualizarPreferenciaDTO(
            clave="registros_boletin_tipos", valor='["fortaleza"]'
        ))
        assert result.clave == "registros_boletin_tipos"

    def test_get_dto_carga_tipos_de_bd(self):
        """Si la BD tiene registros_boletin_tipos, el DTO lo carga correctamente."""
        from src.domain.models.preferencia_institucion import PreferenciaInstitucion
        pref = PreferenciaInstitucion(
            id=1, institucion_id=1,
            categoria=CategoriaPreferencia.CONVIVENCIA,
            clave="registros_boletin_tipos",
            valor='["fortaleza","descargo"]',
            tipo_valor=TipoValor.JSON,
        )
        repo = MagicMock()
        repo.get_all.return_value = [pref]
        svc = PreferenciasInstitucionService(repo)
        dto = svc.get_dto(1)
        assert dto.registros_boletin_tipos == ["fortaleza", "descargo"]


# ===========================================================================
# T3 — ConvivenciaService._registros_informables_periodo
# ===========================================================================

class TestRegistrosInformablesPeriodo:

    def test_sin_provider_usa_defaults(self):
        """Sin preferencias inyectadas usa defaults (fortaleza, compromiso, citacion_acudiente)."""
        regs = [
            _make_registro(1, TipoRegistro.FORTALEZA),
            _make_registro(2, TipoRegistro.DIFICULTAD, acudiente_notificado=True),
            _make_registro(3, TipoRegistro.DESCARGO),  # excluido por default
        ]
        svc = ConvivenciaService(repo=_FakeConvRepo(registros=regs))
        resultado = svc._registros_informables_periodo(1, 5)
        tipos = {r["tipo"] for r in resultado}
        assert "Fortaleza" in tipos
        assert "Dificultad" not in tipos   # no está en default tipos
        assert "Descargo" not in tipos

    def test_filtro_por_tipos(self):
        """Solo los tipos en registros_boletin_tipos pasan."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["dificultad"],
            registros_boletin_dificultad_requiere_notificacion=False,
        )
        regs = [
            _make_registro(1, TipoRegistro.FORTALEZA),
            _make_registro(2, TipoRegistro.DIFICULTAD),
            _make_registro(3, TipoRegistro.COMPROMISO),
        ]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert len(resultado) == 1
        assert resultado[0]["tipo"] == "Dificultad"

    def test_gate_dificultad_requiere_notificacion_activo(self):
        """Con gate activo, dificultad solo entra si acudiente_notificado=True."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["dificultad"],
            registros_boletin_dificultad_requiere_notificacion=True,
        )
        regs = [
            _make_registro(1, TipoRegistro.DIFICULTAD, acudiente_notificado=False),
            _make_registro(2, TipoRegistro.DIFICULTAD, acudiente_notificado=True),
        ]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert len(resultado) == 1
        assert resultado[0]["tipo"] == "Dificultad"

    def test_gate_dificultad_desactivado(self):
        """Con gate desactivado, dificultad entra aunque no haya notificación."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["dificultad"],
            registros_boletin_dificultad_requiere_notificacion=False,
        )
        regs = [
            _make_registro(1, TipoRegistro.DIFICULTAD, acudiente_notificado=False),
        ]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert len(resultado) == 1

    def test_gate_descargo_incluye_false(self):
        """Con incluye_descargo=False, descargo nunca aparece aunque esté en tipos."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["descargo"],
            registros_boletin_incluye_descargo=False,
        )
        regs = [_make_registro(1, TipoRegistro.DESCARGO)]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert resultado == []

    def test_gate_descargo_incluye_true(self):
        """Con incluye_descargo=True y descargo en tipos, aparece en el boletín."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["descargo"],
            registros_boletin_incluye_descargo=True,
        )
        regs = [_make_registro(1, TipoRegistro.DESCARGO)]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert len(resultado) == 1
        assert resultado[0]["tipo"] == "Descargo"

    def test_dedup_excluye_ids_presentes(self):
        """Con dedup activo, registros cuyo id está en excluir_ids se omiten."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["fortaleza"],
            registros_boletin_dedup_observaciones=True,
        )
        regs = [
            _make_registro(1, TipoRegistro.FORTALEZA),
            _make_registro(2, TipoRegistro.FORTALEZA),
        ]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5, excluir_ids={1})
        assert len(resultado) == 1
        assert resultado[0]["tipo"] == "Fortaleza"

    def test_dedup_desactivado_no_excluye(self):
        """Con dedup=False, los ids en excluir_ids no bloquean la inclusión."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["fortaleza"],
            registros_boletin_dedup_observaciones=False,
        )
        regs = [
            _make_registro(1, TipoRegistro.FORTALEZA),
            _make_registro(2, TipoRegistro.FORTALEZA),
        ]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5, excluir_ids={1})
        assert len(resultado) == 2

    def test_ordenado_por_fecha(self):
        """El resultado se ordena por fecha ascendente."""
        prefs = PreferenciasDTO(
            registros_boletin_tipos=["fortaleza", "compromiso"],
        )
        regs = [
            _make_registro(1, TipoRegistro.FORTALEZA, fecha=date(2026, 6, 10)),
            _make_registro(2, TipoRegistro.COMPROMISO, fecha=date(2026, 3, 5)),
        ]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert len(resultado) == 2
        assert resultado[0]["fecha"] == "2026-03-05"
        assert resultado[1]["fecha"] == "2026-06-10"

    def test_estructura_dict_correcto(self):
        """Cada elemento del resultado tiene fecha, tipo y descripcion."""
        prefs = PreferenciasDTO(registros_boletin_tipos=["fortaleza"])
        regs = [_make_registro(1, TipoRegistro.FORTALEZA, descripcion="Excelente actitud")]
        svc = _make_svc(registros=regs, prefs=prefs)
        resultado = svc._registros_informables_periodo(1, 5)
        assert len(resultado) == 1
        r = resultado[0]
        assert "fecha" in r
        assert "tipo" in r
        assert "descripcion" in r
        assert r["tipo"] == "Fortaleza"
        assert r["descripcion"] == "Excelente actitud"

    def test_lista_vacia_si_sin_registros(self):
        """Sin registros en repo, retorna lista vacía."""
        svc = ConvivenciaService(repo=_FakeConvRepo(registros=[]))
        resultado = svc._registros_informables_periodo(1, 5)
        assert resultado == []


# ===========================================================================
# T4 — InformeService.convivencia_boletin (periodo)
# ===========================================================================

class TestConvivenciaBoletin:

    def _make_informe_svc(self, registros=None, obs=None):
        """Helper: InformeService con ConvivenciaService(FakeConvRepo)."""
        from unittest.mock import MagicMock

        from src.domain.ports.estadisticos_repo import IEstadisticosRepository
        repo = _FakeConvRepo(registros=registros, obs=obs)
        est_repo = MagicMock(spec=IEstadisticosRepository)
        return InformeService(
            estadisticos_repo=est_repo,
            convivencia_svc_provider=lambda: ConvivenciaService(repo),
        )

    def test_devuelve_clave_registros(self):
        """convivencia_boletin siempre devuelve la clave 'registros'."""
        svc = self._make_informe_svc()
        result = svc.convivencia_boletin(1, 5)
        assert "registros" in result

    def test_registros_vacios_por_defecto(self):
        """Sin registros en repo, 'registros' es lista vacía."""
        svc = self._make_informe_svc()
        result = svc.convivencia_boletin(1, 5)
        assert result["registros"] == []

    def test_registros_fortaleza_incluida(self):
        """Fortaleza está en defaults → aparece en registros."""
        regs = [_make_registro(1, TipoRegistro.FORTALEZA, descripcion="Muy buen comportamiento")]
        svc = self._make_informe_svc(registros=regs)
        result = svc.convivencia_boletin(1, 5)
        assert len(result["registros"]) == 1
        assert result["registros"][0]["tipo"] == "Fortaleza"

    def test_descargo_excluido_por_default(self):
        """Descargo no está en defaults → excluido."""
        regs = [_make_registro(1, TipoRegistro.DESCARGO)]
        svc = self._make_informe_svc(registros=regs)
        result = svc.convivencia_boletin(1, 5)
        assert result["registros"] == []

    def test_dedup_con_obs_vinculada(self):
        """Registro cuyo id está en obs.registro_comportamiento_id → excluido por dedup."""
        obs = [ObservacionPeriodo(
            id=10, estudiante_id=1, asignacion_id=2, periodo_id=5,
            texto="Buena actitud", es_publica=True, registro_comportamiento_id=1,
        )]
        regs = [_make_registro(1, TipoRegistro.FORTALEZA)]
        svc = self._make_informe_svc(registros=regs, obs=obs)
        result = svc.convivencia_boletin(1, 5)
        # El registro id=1 está referenciado en obs → dedup lo excluye
        assert result["registros"] == []

    def test_sin_repo_devuelve_registros_vacios(self):
        """Sin convivencia_repo, registros es lista vacía."""
        from unittest.mock import MagicMock

        from src.domain.ports.estadisticos_repo import IEstadisticosRepository
        est_repo = MagicMock(spec=IEstadisticosRepository)
        svc = InformeService(estadisticos_repo=est_repo)
        result = svc.convivencia_boletin(1, 5)
        assert result["registros"] == []


# ===========================================================================
# T5 — InformeService.convivencia_boletin_anual (anual)
# ===========================================================================

class TestConvivenciaBoletinAnual:

    def _make_periodo(self, id_: int, nombre: str):
        m = MagicMock()
        m.id = id_
        m.nombre = nombre
        return m

    def _make_informe_svc_anual(self, registros=None):
        from unittest.mock import MagicMock

        from src.domain.ports.estadisticos_repo import IEstadisticosRepository
        periodos = [self._make_periodo(1, "P1"), self._make_periodo(2, "P2")]
        periodo_svc = MagicMock()
        periodo_svc.listar_por_anio.return_value = periodos
        repo = _FakeConvRepo(registros=registros)
        est_repo = MagicMock(spec=IEstadisticosRepository)
        return InformeService(
            estadisticos_repo=est_repo,
            convivencia_svc_provider=lambda: ConvivenciaService(
                repo,
                periodo_svc_provider=lambda: periodo_svc,
            ),
        )

    def test_devuelve_clave_registros(self):
        """convivencia_boletin_anual siempre incluye la clave 'registros'."""
        svc = self._make_informe_svc_anual()
        result = svc.convivencia_boletin_anual(1, 2026)
        assert "registros" in result

    def test_registros_vacios_por_defecto(self):
        """Sin registros, 'registros' es lista vacía."""
        svc = self._make_informe_svc_anual()
        result = svc.convivencia_boletin_anual(1, 2026)
        assert result["registros"] == []

    def test_registros_fortaleza_anual(self):
        """Fortaleza aparece en el resultado anual."""
        regs = [_make_registro(1, TipoRegistro.FORTALEZA, descripcion="Líder ejemplar")]
        svc = self._make_informe_svc_anual(registros=regs)
        result = svc.convivencia_boletin_anual(1, 2026)
        assert len(result["registros"]) >= 1
        tipos = {r["tipo"] for r in result["registros"]}
        assert "Fortaleza" in tipos

    def test_ordenado_por_fecha_anual(self):
        """Los registros anuales se ordenan por fecha ascendente."""
        regs = [
            _make_registro(1, TipoRegistro.FORTALEZA, fecha=date(2026, 8, 1)),
            _make_registro(2, TipoRegistro.COMPROMISO, fecha=date(2026, 3, 5)),
        ]
        svc = self._make_informe_svc_anual(registros=regs)
        result = svc.convivencia_boletin_anual(1, 2026)
        registros = result["registros"]
        assert len(registros) >= 2
        fechas = [r["fecha"] for r in registros]
        assert fechas == sorted(fechas)

    def test_sin_repo_devuelve_empty(self):
        """Sin convivencia_repo ni periodo_svc, retorna estructura vacía con registros=[]."""
        from unittest.mock import MagicMock

        from src.domain.ports.estadisticos_repo import IEstadisticosRepository
        est_repo = MagicMock(spec=IEstadisticosRepository)
        svc = InformeService(estadisticos_repo=est_repo)
        result = svc.convivencia_boletin_anual(1, 2026)
        assert "registros" in result
        assert result["registros"] == []


# ===========================================================================
# T6 — TIPO_REGISTRO_DISPLAY
# ===========================================================================

class TestTipoRegistroDisplay:

    def test_todos_los_tipos_presentes(self):
        for t in TipoRegistro:
            assert t.value in TIPO_REGISTRO_DISPLAY, f"{t.value!r} falta en TIPO_REGISTRO_DISPLAY"

    def test_valores_no_vacios(self):
        for k, v in TIPO_REGISTRO_DISPLAY.items():
            assert v, f"Label vacío para {k!r}"
