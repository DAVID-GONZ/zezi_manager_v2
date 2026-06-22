"""
Tests unitarios para ConfiguracionService.
Usa repositorios falsos en memoria (FakeRepository pattern).
"""
from __future__ import annotations

import pytest

from src.domain.models.configuracion import (
    ConfiguracionAnio,
    CriterioPromocion,
    NivelDesempeno,
    NuevaConfiguracionAnioDTO,
    NuevoNivelDesempenoDTO,
)
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.services.configuracion_service import ConfiguracionService


# ===========================================================================
# Repositorio falso
# ===========================================================================

class FakeConfigRepo(IConfiguracionRepository):
    def __init__(self):
        self._configs: dict[int, ConfiguracionAnio] = {}
        self._niveles: dict[int, list[NivelDesempeno]] = {}
        self._criterios: dict[int, CriterioPromocion] = {}
        self._next_id = 1

    def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        config = config.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._configs[config.id] = config
        return config

    def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        self._configs[config.id] = config
        return config

    def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None:
        return self._configs.get(anio_id)

    def get_by_anio(
        self, institucion_id: int | None, anio: int
    ) -> ConfiguracionAnio | None:
        for c in self._configs.values():
            if c.anio == anio and (
                institucion_id is None or c.institucion_id == institucion_id
            ):
                return c
        return None

    def get_activa(self, institucion_id: int | None = None) -> ConfiguracionAnio | None:
        for c in self._configs.values():
            if c.activo and (
                institucion_id is None or c.institucion_id == institucion_id
            ):
                return c
        return None

    def activar(self, anio_id: int) -> None:
        # Multi-tenant (paso_27): desactivar SOLO los años de la misma
        # institución que el año a activar.
        objetivo = self._configs.get(anio_id)
        inst = objetivo.institucion_id if objetivo else None
        for c in self._configs.values():
            if c.id == anio_id:
                self._configs[c.id] = c.model_copy(update={"activo": True})
            elif c.institucion_id == inst:
                self._configs[c.id] = c.model_copy(update={"activo": False})

    def guardar_numero_periodos(self, anio_id: int, numero: int, pesos_iguales: bool = True) -> None:
        pass  # No-op en test

    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        return self._niveles.get(anio_id, [])

    def reemplazar_niveles(self, anio_id: int, niveles: list[NivelDesempeno]) -> list[NivelDesempeno]:
        self._niveles[anio_id] = niveles
        return niveles

    def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None:
        for nivel in self._niveles.get(anio_id, []):
            if nivel.rango_min <= nota <= nivel.rango_max:
                return nivel
        return None

    def get_nivel(self, nivel_id: int) -> NivelDesempeno | None:
        for niveles in self._niveles.values():
            for n in niveles:
                if n.id == nivel_id:
                    return n
        return None

    def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        anio_id = nivel.anio_id
        nivel = nivel.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._niveles.setdefault(anio_id, []).append(nivel)
        return nivel

    def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        niveles = self._niveles.get(nivel.anio_id, [])
        for i, n in enumerate(niveles):
            if n.id == nivel.id:
                niveles[i] = nivel
                break
        return nivel

    def eliminar_nivel(self, nivel_id: int) -> bool:
        for anio_id, niveles in self._niveles.items():
            for i, n in enumerate(niveles):
                if n.id == nivel_id:
                    self._niveles[anio_id].pop(i)
                    return True
        return False

    def listar(
        self, institucion_id: int | None = None
    ) -> list[ConfiguracionAnio]:
        if institucion_id is None:
            return list(self._configs.values())
        return [
            c for c in self._configs.values()
            if c.institucion_id == institucion_id
        ]

    def get_numero_periodos(self, anio_id: int) -> int:
        return 4

    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        return self._criterios.get(anio_id)

    def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion:
        self._criterios[criterios.anio_id] = criterios
        return criterios


# ===========================================================================
# Tests
# ===========================================================================

def _make_service() -> tuple[ConfiguracionService, FakeConfigRepo]:
    repo = FakeConfigRepo()
    svc  = ConfiguracionService(repo)
    return svc, repo


class TestCrearAnio:
    def test_crea_anio_nuevo(self):
        svc, repo = _make_service()
        dto = NuevaConfiguracionAnioDTO(anio=2025)
        config = svc.crear_anio(dto)
        assert config.id is not None
        assert config.anio == 2025

    def test_lanza_si_anio_duplicado(self):
        svc, repo = _make_service()
        dto = NuevaConfiguracionAnioDTO(anio=2025)
        svc.crear_anio(dto)
        with pytest.raises(ValueError, match="2025"):
            svc.crear_anio(dto)

    def test_crea_diferentes_anios(self):
        svc, repo = _make_service()
        c1 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2024))
        c2 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        assert c1.id != c2.id


class TestActivarAnio:
    def test_activa_anio_existente(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        result = svc.activar_anio(config.id)
        assert result is not None

    def test_lanza_si_anio_no_existe(self):
        svc, _ = _make_service()
        with pytest.raises(ValueError, match="999"):
            svc.activar_anio(999)


class TestGetActiva:
    def test_lanza_si_no_hay_activo(self):
        svc, repo = _make_service()
        with pytest.raises(ValueError, match="activo"):
            svc.get_activa()

    def test_retorna_config_activa(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        # config creada con activo=True
        activa = svc.get_activa()
        assert activa.anio == 2025


class TestConfigurarNiveles:
    def test_niveles_sin_solapamiento(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        niveles = [
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="Bajo",   rango_min=0,  rango_max=59),
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="Basico", rango_min=60, rango_max=79),
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="Alto",   rango_min=80, rango_max=100),
        ]
        resultado = svc.configurar_niveles(config.id, niveles)
        assert len(resultado) == 3

    def test_lanza_si_rangos_solapados(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        niveles = [
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="A", rango_min=0,  rango_max=60),
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="B", rango_min=55, rango_max=100),
        ]
        with pytest.raises(ValueError, match="solapan"):
            svc.configurar_niveles(config.id, niveles)

    def test_lanza_si_lista_vacia(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        with pytest.raises(ValueError, match="menos un nivel"):
            svc.configurar_niveles(config.id, [])


class TestGetCriterios:
    def test_retorna_none_si_no_existen(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        assert svc.get_criterios(config.id) is None

    def test_guarda_y_recupera_criterios(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        criterios = CriterioPromocion(
            anio_id=config.id,
            max_asignaturas_perdidas=2,
            nota_minima_habilitacion=60.0,
        )
        guardados = svc.guardar_criterios(criterios)
        recuperados = svc.get_criterios(config.id)
        assert recuperados is not None
        assert recuperados.max_asignaturas_perdidas == 2


# ===========================================================================
# Group 3 — CRUD granular de niveles + propiedad de dominio
# ===========================================================================

def _anio(svc) -> int:
    return svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2030)).id


class TestNivelesGranulares:
    def test_agregar_nivel_asigna_id_y_orden(self):
        svc, _ = _make_service()
        aid = _anio(svc)
        svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Alto", rango_min=80, rango_max=100))
        n = svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Bajo", rango_min=0, rango_max=59))
        assert n.id is not None
        niveles = sorted(svc.listar_niveles(aid), key=lambda x: x.rango_min)
        assert [x.orden for x in niveles] == [0, 1]  # reindexado por rango

    def test_agregar_nivel_solapado_falla(self):
        svc, _ = _make_service()
        aid = _anio(svc)
        svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Bajo", rango_min=0, rango_max=60))
        with pytest.raises(ValueError, match="solapan"):
            svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
                anio_id=aid, nombre="Medio", rango_min=55, rango_max=80))

    def test_actualizar_nivel(self):
        svc, _ = _make_service()
        aid = _anio(svc)
        n = svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Bajo", rango_min=0, rango_max=59))
        svc.actualizar_nivel(aid, n.id, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Bajisimo", rango_min=0, rango_max=49))
        actualizado = next(x for x in svc.listar_niveles(aid) if x.id == n.id)
        assert actualizado.nombre == "Bajisimo" and actualizado.rango_max == 49

    def test_eliminar_nivel(self):
        svc, _ = _make_service()
        aid = _anio(svc)
        a = svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Bajo", rango_min=0, rango_max=59))
        svc.agregar_nivel(aid, NuevoNivelDesempenoDTO(
            anio_id=aid, nombre="Alto", rango_min=60, rango_max=100))
        assert svc.eliminar_nivel(aid, a.id) is True
        assert all(x.id != a.id for x in svc.listar_niveles(aid))


class TestAprobacionEnRango:
    def test_propiedad_dominio(self):
        c = ConfiguracionAnio(anio=2025, nota_minima_escala=0,
                              nota_maxima_escala=100, nota_minima_aprobacion=60)
        assert c.aprobacion_en_rango is True
        c2 = ConfiguracionAnio(anio=2026, nota_minima_escala=10,
                               nota_maxima_escala=50, nota_minima_aprobacion=60)
        assert c2.aprobacion_en_rango is False


# ===========================================================================
# Multi-tenant (paso_27) — configuración por institución
# ===========================================================================

class TestConfigPorInstitucion:
    def test_anio_activo_por_institucion(self):
        """get_activa(institucion_id) devuelve el año activo de ese tenant."""
        svc, _ = _make_service()
        svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=2))
        a1 = svc.get_activa(institucion_id=1)
        a2 = svc.get_activa(institucion_id=2)
        assert a1.institucion_id == 1 and a1.anio == 2025
        assert a2.institucion_id == 2 and a2.anio == 2025
        assert a1.id != a2.id

    def test_mismo_anio_dos_instituciones_no_colisiona(self):
        """Dos instituciones pueden tener el mismo número de año."""
        svc, _ = _make_service()
        c1 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        c2 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=2))
        assert c1.id != c2.id

    def test_anio_duplicado_misma_institucion_falla(self):
        svc, _ = _make_service()
        svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        with pytest.raises(ValueError, match="institución"):
            svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))

    def test_activar_no_desactiva_anios_de_otra_institucion(self):
        """Activar un año de una institución no toca los de otra."""
        svc, _ = _make_service()
        # Institución 1: dos años (2024 activo por defecto, 2025 nuevo).
        a2024 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2024, institucion_id=1))
        a2025 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        # Institución 2: un año, debe quedar intacto.
        b2025 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=2))

        svc.activar_anio(a2025.id)

        assert svc.get_by_id(a2025.id).activo is True
        assert svc.get_by_id(a2024.id).activo is False   # desactivado (misma inst)
        assert svc.get_by_id(b2025.id).activo is True     # intacto (otra inst)


# ===========================================================================
# Scope desde el contextvar (frente C — paso_28)
# ===========================================================================

class TestScopeContextvar:
    """`get_activa()` sin argumento resuelve el tenant del contextvar."""

    def test_get_activa_resuelve_institucion_del_contextvar(self):
        from src.services.contexto_tenant import usar_institucion

        svc, _ = _make_service()
        # Año activo en institución 1 y en institución 2.
        a1 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        a2 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=2))
        svc.activar_anio(a1.id)
        svc.activar_anio(a2.id)

        # Con el scope en la institución 2, get_activa() sin argumento la resuelve.
        with usar_institucion(2):
            activa = svc.get_activa()
        assert activa.id == a2.id
        assert activa.institucion_id == 2

    def test_id_explicito_tiene_prioridad_sobre_contextvar(self):
        from src.services.contexto_tenant import usar_institucion

        svc, _ = _make_service()
        a1 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        a2 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=2))
        svc.activar_anio(a1.id)
        svc.activar_anio(a2.id)

        # Aunque el scope sea 2, el id explícito 1 manda.
        with usar_institucion(2):
            activa = svc.get_activa(institucion_id=1)
        assert activa.id == a1.id

    def test_sin_scope_cae_a_institucion_por_defecto(self):
        """Sin sesión (scope None) y sin catálogo, _resolver_institucion → None."""
        svc, _ = _make_service()
        # FakeConfigRepo.get_activa(None) devuelve el primer activo (single-tenant
        # temprano): cubre el fallback #1/None sin Container disponible.
        a1 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025, institucion_id=1))
        svc.activar_anio(a1.id)
        activa = svc.get_activa()  # sin scope ni id explícito
        assert activa.id == a1.id
