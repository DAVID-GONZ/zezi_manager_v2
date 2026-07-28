"""Tests unitarios para ConvivenciaService."""
from __future__ import annotations

from datetime import date

import pytest

from src.domain.models.convivencia import (
    CategoriaObservacion,
    ConceptoComportamientoDTO,
    FiltroConvivenciaDTO,
    NotaComportamiento,
    NuevaCategoriaDTO,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
    ObservacionPeriodo,
    PlantillaObservacion,
    RegistroComportamiento,
    TipoRegistro,
)
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.services.convivencia_service import ConvivenciaService

# ===========================================================================
# Fake
# ===========================================================================

class FakeConvRepo(IConvivenciaRepository):
    def __init__(self):
        self._obs: dict[int, ObservacionPeriodo] = {}
        self._regs: dict[int, RegistroComportamiento] = {}
        self._notas: dict[tuple, NotaComportamiento] = {}
        self._cats: dict[int, CategoriaObservacion] = {}
        self._plantillas: dict[int, PlantillaObservacion] = {}
        self._next_obs = 1
        self._next_reg = 1
        self._next_nota = 1
        self._next_cat = 1
        self._next_plantilla = 1

    # Observaciones
    def get_observacion(self, oid: int) -> ObservacionPeriodo | None:
        return self._obs.get(oid)

    def get_observacion_por_asignacion(self, est_id: int, asig_id: int, per_id: int) -> ObservacionPeriodo | None:
        for o in self._obs.values():
            if o.estudiante_id == est_id and o.asignacion_id == asig_id and o.periodo_id == per_id:
                return o
        return None

    def listar_observaciones_por_estudiante(self, est_id: int, per_id=None, solo_publicas=False) -> list[ObservacionPeriodo]:
        return [o for o in self._obs.values() if o.estudiante_id == est_id]

    def guardar_observacion(self, o: ObservacionPeriodo) -> ObservacionPeriodo:
        o = o.model_copy(update={"id": self._next_obs})
        self._next_obs += 1
        self._obs[o.id] = o
        return o

    def actualizar_observacion(self, o: ObservacionPeriodo) -> ObservacionPeriodo:
        self._obs[o.id] = o
        return o

    def eliminar_observacion(self, oid: int) -> bool:
        return self._obs.pop(oid, None) is not None

    # Registros
    def get_registro(self, rid: int) -> RegistroComportamiento | None:
        return self._regs.get(rid)

    def listar_registros(self, filtro: FiltroConvivenciaDTO, institucion_id=None) -> list[RegistroComportamiento]:
        return list(self._regs.values())

    def contar_registros(self, filtro: FiltroConvivenciaDTO, institucion_id=None) -> int:
        return len(self._regs)

    def guardar_registro(self, r: RegistroComportamiento) -> RegistroComportamiento:
        r = r.model_copy(update={"id": self._next_reg})
        self._next_reg += 1
        self._regs[r.id] = r
        return r

    def actualizar_registro(self, r: RegistroComportamiento) -> RegistroComportamiento:
        self._regs[r.id] = r
        return r

    def eliminar_registro(self, rid: int) -> bool:
        return self._regs.pop(rid, None) is not None

    # Notas
    def get_nota(self, est_id: int, per_id: int) -> NotaComportamiento | None:
        return self._notas.get((est_id, per_id))

    def listar_notas_por_estudiante(self, est_id: int) -> list[NotaComportamiento]:
        return []

    def listar_notas_por_grupo(self, grupo_id: int, per_id: int) -> list[NotaComportamiento]:
        return [n for (e, p), n in self._notas.items() if p == per_id and n.grupo_id == grupo_id]

    def guardar_nota(self, n: NotaComportamiento) -> NotaComportamiento:
        key = (n.estudiante_id, n.periodo_id)
        self._notas[key] = n
        return n

    # Categorías
    def listar_categorias(self, solo_activas: bool = True) -> list[CategoriaObservacion]:
        cats = list(self._cats.values())
        if solo_activas:
            cats = [c for c in cats if c.activa]
        return cats

    def get_categoria(self, categoria_id: int) -> CategoriaObservacion | None:
        return self._cats.get(categoria_id)

    def guardar_categoria(self, cat: CategoriaObservacion) -> CategoriaObservacion:
        cat = cat.model_copy(update={"id": self._next_cat})
        self._next_cat += 1
        self._cats[cat.id] = cat
        return cat

    def actualizar_categoria(self, cat: CategoriaObservacion) -> CategoriaObservacion:
        self._cats[cat.id] = cat
        return cat

    # Plantillas (convivencia_12)
    def listar_plantillas(self, categoria_id=None, solo_activas=True) -> list[PlantillaObservacion]:
        result = list(self._plantillas.values())
        if solo_activas:
            result = [p for p in result if p.activa]
        if categoria_id is not None:
            result = [p for p in result if p.categoria_id == categoria_id]
        return sorted(result, key=lambda p: p.uso_count, reverse=True)

    def get_plantilla(self, plantilla_id: int) -> PlantillaObservacion | None:
        return self._plantillas.get(plantilla_id)

    def guardar_plantilla(self, p: PlantillaObservacion) -> PlantillaObservacion:
        p = p.model_copy(update={"id": self._next_plantilla})
        self._next_plantilla += 1
        self._plantillas[p.id] = p
        return p

    def actualizar_plantilla(self, p: PlantillaObservacion) -> PlantillaObservacion:
        self._plantillas[p.id] = p
        return p

    def incrementar_uso_plantilla(self, plantilla_id: int) -> None:
        if plantilla_id in self._plantillas:
            p = self._plantillas[plantilla_id]
            self._plantillas[plantilla_id] = p.model_copy(
                update={"uso_count": p.uso_count + 1}
            )


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[ConvivenciaService, FakeConvRepo]:
    repo = FakeConvRepo()
    return ConvivenciaService(repo), repo


# ===========================================================================
# Tests
# ===========================================================================

class TestRegistrarObservacion:
    def test_crea_nueva_observacion(self):
        svc, _ = _make_svc()
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Buen desempeño", es_publica=True, categoria_id=1,
        )
        obs = svc.registrar_observacion(dto)
        assert obs.id is not None

    def test_actualiza_observacion_existente(self):
        svc, _ = _make_svc()
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Texto inicial", categoria_id=1,
        )
        svc.registrar_observacion(dto)
        dto2 = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Texto actualizado", categoria_id=1,
        )
        obs = svc.registrar_observacion(dto2)
        assert obs.texto == "Texto actualizado"


class TestRegistrarComportamiento:
    def test_registra_comportamiento_fortaleza(self):
        svc, _ = _make_svc()
        dto = NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            tipo=TipoRegistro.FORTALEZA,
            descripcion="Excelente participación en clase",
            fecha=date.today(),
        )
        reg = svc.registrar_comportamiento(dto)
        assert reg.id is not None
        assert reg.tipo == TipoRegistro.FORTALEZA

    def test_notificar_acudiente_exitosamente(self):
        svc, _ = _make_svc()
        dto = NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            tipo=TipoRegistro.CITACION_ACUDIENTE,
            descripcion="Citación por bajo rendimiento",
            requiere_firma=True,
            fecha=date.today(),
        )
        reg = svc.registrar_comportamiento(dto)
        notificado = svc.notificar_acudiente(reg.id)
        assert notificado.acudiente_notificado is True

    def test_lanza_si_registro_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.notificar_acudiente(999)


class TestNotaComportamiento:
    def test_registra_nota_comportamiento(self):
        svc, _ = _make_svc()
        dto = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=85.0
        )
        nota = svc.registrar_nota_comportamiento(dto)
        assert nota.valor == pytest.approx(85.0)

    def test_upsert_nota_sobreescribe(self):
        svc, _ = _make_svc()
        dto1 = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=70.0
        )
        dto2 = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=85.0
        )
        svc.registrar_nota_comportamiento(dto1)
        svc.registrar_nota_comportamiento(dto2)
        nota = svc.get_nota_comportamiento(1, 5)
        assert nota.valor == pytest.approx(85.0)


# ===========================================================================
# Enforcement de autorización (convivencia_04b — defensa en profundidad)
# ===========================================================================

class _StubCatalogoSvc:
    """Stub minimal de CatalogoAcademicoService: siempre autoriza/deniega."""
    def __init__(self, autoriza: bool):
        self._autoriza = autoriza
        self.llamadas: list[tuple] = []

    def puede_gestionar_comportamiento_en_grupo(
        self, usuario_rol, usuario_id, grupo_id
    ) -> bool:
        self.llamadas.append((usuario_rol, usuario_id, grupo_id))
        return self._autoriza


class TestEnforcementAutorizacion:
    def _dto_registro(self) -> NuevoRegistroComportamientoDTO:
        return NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            tipo=TipoRegistro.FORTALEZA,
            descripcion="Buen trabajo",
            fecha=date.today(),
        )

    def test_provider_deniega_lanza_permission_error_y_no_persiste(self):
        repo = FakeConvRepo()
        stub = _StubCatalogoSvc(autoriza=False)
        svc = ConvivenciaService(
            repo=repo,
            catalogo_academico_svc_provider=lambda: stub,
        )
        with pytest.raises(PermissionError):
            svc.registrar_comportamiento(
                self._dto_registro(),
                usuario_id=99,
                usuario_rol="profesor",
            )
        assert repo._regs == {}  # no persistió
        assert stub.llamadas == [("profesor", 99, 10)]

    def test_provider_autoriza_mutacion_ok(self):
        repo = FakeConvRepo()
        stub = _StubCatalogoSvc(autoriza=True)
        svc = ConvivenciaService(
            repo=repo,
            catalogo_academico_svc_provider=lambda: stub,
        )
        reg = svc.registrar_comportamiento(
            self._dto_registro(),
            usuario_id=99,
            usuario_rol="profesor",
        )
        assert reg.id is not None
        assert stub.llamadas == [("profesor", 99, 10)]

    def test_sin_provider_es_compat_retro(self):
        svc, repo = _make_svc()  # sin provider
        reg = svc.registrar_comportamiento(
            self._dto_registro(), usuario_id=99, usuario_rol="profesor",
        )
        assert reg.id is not None


# ===========================================================================
# Concepto consolidado (convivencia_05)
# ===========================================================================

class _FakeNivel:
    def __init__(self, id, nombre, rmin, rmax, descripcion=None):
        self.id = id
        self.nombre = nombre
        self.rango_min = rmin
        self.rango_max = rmax
        self.descripcion = descripcion


class _FakeConfigSvc:
    def __init__(self, niveles):
        self._niveles = niveles
    def listar_niveles(self, anio_id):
        return self._niveles


class _FakePeriodoSvc:
    class _P:
        anio_id = 2026
    def get_by_id(self, periodo_id):
        return self._P()


class _FakeEst:
    def __init__(self, id):
        self.id = id


class _FakeEstSvc:
    def __init__(self, ests):
        self._ests = ests
    def listar_por_grupo(self, grupo_id, solo_activos=True):
        return self._ests


_NIVELES = [
    _FakeNivel(1, "Bajo", 0, 59.99, "Bajo desempeño"),
    _FakeNivel(2, "Básico", 60, 69.99, "Básico"),
    _FakeNivel(3, "Alto", 70, 84.99, "Alto"),
    _FakeNivel(4, "Superior", 85, 100, "Superior"),
]


def _svc_completo(ests=None):
    repo = FakeConvRepo()
    svc = ConvivenciaService(
        repo=repo,
        configuracion_svc_provider=lambda: _FakeConfigSvc(_NIVELES),
        periodo_svc_provider=lambda: _FakePeriodoSvc(),
        estudiante_svc_provider=lambda: _FakeEstSvc(ests or []),
    )
    return svc, repo


class TestConceptoComportamiento:
    def test_sin_nota_devuelve_dto_vacio(self):
        svc, _ = _svc_completo()
        dto = svc.get_concepto_periodo(estudiante_id=1, periodo_id=5)
        assert isinstance(dto, ConceptoComportamientoDTO)
        assert dto.valor is None
        assert dto.aprobado is False
        assert dto.nivel_nombre is None
        assert dto.concepto is None

    def test_con_desempeno_id_explicito(self):
        svc, repo = _svc_completo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            valor=65.0, desempeno_id=4, observacion="Excelente actitud",
        )
        dto = svc.get_concepto_periodo(1, 5)
        # desempeno_id=4 (Superior) prevalece sobre el rango que daría "Básico"
        assert dto.nivel_nombre == "Superior"
        assert dto.valor == 65.0
        assert dto.concepto == "Excelente actitud"
        assert dto.aprobado is True

    def test_sin_desempeno_id_resuelve_por_rango(self):
        svc, repo = _svc_completo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=72.5,
        )
        dto = svc.get_concepto_periodo(1, 5)
        assert dto.nivel_nombre == "Alto"
        assert dto.aprobado is True

    def test_nota_menor_a_minima_no_aprobado(self):
        svc, repo = _svc_completo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=55.0,
        )
        dto = svc.get_concepto_periodo(1, 5, nota_minima=60.0)
        assert dto.aprobado is False
        assert dto.nivel_nombre == "Bajo"

    def test_listar_conceptos_grupo_incluye_estudiantes_sin_nota(self):
        ests = [_FakeEst(1), _FakeEst(2), _FakeEst(3)]
        svc, repo = _svc_completo(ests=ests)
        # Solo el estudiante 2 tiene nota.
        repo._notas[(2, 5)] = NotaComportamiento(
            estudiante_id=2, grupo_id=10, periodo_id=5, valor=90.0,
        )
        conceptos = svc.listar_conceptos_grupo(grupo_id=10, periodo_id=5)
        assert len(conceptos) == 3
        by_est = {c.estudiante_id: c for c in conceptos}
        assert by_est[1].valor is None and by_est[1].aprobado is False
        assert by_est[2].valor == 90.0 and by_est[2].nivel_nombre == "Superior"
        assert by_est[3].valor is None

    # -----------------------------------------------------------------
    # convivencia_06 — Reporte por grupo/periodo
    # -----------------------------------------------------------------

    def test_reporte_periodo_grupo_combina_notas_y_observaciones(self):
        ests = [_FakeEst(1), _FakeEst(2), _FakeEst(3)]
        # Añadimos nombre/apellido dinámicamente sin acoplar el modelo real.
        for e, nom, ape in [(ests[0], "Ana", "Ruiz"), (ests[1], "Bob", "Diaz"), (ests[2], "Cyd", "Paz")]:
            e.nombre = nom
            e.apellido = ape
        svc, repo = _svc_completo(ests=ests)
        # Estudiante 1 → nota + 2 observaciones.
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            valor=90.0, observacion="Excelente disciplina",
        )
        repo.guardar_observacion(ObservacionPeriodo(
            estudiante_id=1, asignacion_id=99, periodo_id=5,
            texto="Muy participativo",
        ))
        repo.guardar_observacion(ObservacionPeriodo(
            estudiante_id=1, asignacion_id=100, periodo_id=5,
            texto="Colabora con compañeros",
        ))
        # Estudiante 2 → sin nota, con 1 observación.
        repo.guardar_observacion(ObservacionPeriodo(
            estudiante_id=2, asignacion_id=99, periodo_id=5,
            texto="Debe entregar tareas a tiempo",
        ))
        # Estudiante 3 → sin nota, sin observaciones.

        filas = svc.reporte_periodo_grupo(grupo_id=10, periodo_id=5)
        assert len(filas) == 3
        by_id = {f.estudiante_id: f for f in filas}

        # Estudiante 1: nota + concepto + 2 observaciones
        assert by_id[1].valor == 90.0
        assert by_id[1].nivel_nombre == "Superior"
        assert by_id[1].concepto == "Excelente disciplina"
        assert set(by_id[1].observaciones) == {
            "Muy participativo", "Colabora con compañeros",
        }
        assert by_id[1].nombre == "Ruiz Ana"

        # Estudiante 2: sin nota, 1 observación
        assert by_id[2].valor is None
        assert by_id[2].nivel_nombre is None
        assert by_id[2].concepto is None
        assert by_id[2].observaciones == ["Debe entregar tareas a tiempo"]

        # Estudiante 3: sin nota, sin observaciones
        assert by_id[3].valor is None
        assert by_id[3].observaciones == []

    def test_reporte_periodo_grupo_sin_provider_lanza(self):
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        with pytest.raises(RuntimeError):
            svc.reporte_periodo_grupo(grupo_id=10, periodo_id=5)

    def test_get_concepto_sin_providers_lanza(self):
        repo = FakeConvRepo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=70.0,
        )
        svc = ConvivenciaService(repo=repo)
        with pytest.raises(RuntimeError):
            svc.get_concepto_periodo(1, 5)

    # -----------------------------------------------------------------
    # convivencia_06b — Exportación en el servicio (hexagonal)
    # -----------------------------------------------------------------

    def test_exportar_reporte_sin_exporter_lanza(self):
        svc, _ = _svc_completo()
        with pytest.raises(RuntimeError):
            svc.exportar_reporte_periodo_grupo(10, 5, "excel")

    def test_exportar_reporte_formato_invalido_lanza(self):
        class _NullExp:
            def exportar_excel(self, *a, **kw): return b""
            def exportar_pdf(self, *a, **kw): return b""
            def exportar_csv(self, *a, **kw): return b""
        repo = FakeConvRepo()
        svc = ConvivenciaService(
            repo=repo,
            configuracion_svc_provider=lambda: _FakeConfigSvc(_NIVELES),
            periodo_svc_provider=lambda: _FakePeriodoSvc(),
            estudiante_svc_provider=lambda: _FakeEstSvc([]),
            exporter=_NullExp(),
        )
        with pytest.raises(ValueError):
            svc.exportar_reporte_periodo_grupo(10, 5, "csv")

    def test_exportar_reporte_excel_llama_al_exporter(self):
        """La composición (columnas, aplanado) vive en el servicio; el
        exporter solo recibe list[dict] con las claves del reporte."""
        calls: dict = {}

        class _FakeExp:
            def exportar_excel(self, datos, nombre_hoja="Datos", ruta_destino=None):
                calls["excel_datos"] = datos
                calls["excel_hoja"]  = nombre_hoja
                return b"XLSX-BYTES"
            def exportar_pdf(self, html, ruta_destino=None):
                calls["pdf_html"] = html
                return b"PDF-BYTES"
            def exportar_csv(self, *a, **kw): return b""

        est = _FakeEst(1); est.nombre = "Ana"; est.apellido = "Ruiz"
        repo = FakeConvRepo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=80.0,
        )
        svc = ConvivenciaService(
            repo=repo,
            configuracion_svc_provider=lambda: _FakeConfigSvc(_NIVELES),
            periodo_svc_provider=lambda: _FakePeriodoSvc(),
            estudiante_svc_provider=lambda: _FakeEstSvc([est]),
            exporter=_FakeExp(),
        )
        bytes_ = svc.exportar_reporte_periodo_grupo(10, 5, "excel", titulo="X")
        assert bytes_ == b"XLSX-BYTES"
        assert calls["excel_hoja"] == "X"
        datos = calls["excel_datos"]
        assert isinstance(datos, list) and len(datos) == 1
        assert set(datos[0].keys()) == {"estudiante", "nota", "nivel", "concepto", "observaciones"}
        assert datos[0]["estudiante"] == "Ruiz Ana"
        assert datos[0]["nota"] == 80.0

    def test_exportar_reporte_pdf_genera_html_con_columnas(self):
        class _FakeExp:
            def __init__(self): self.html = None
            def exportar_excel(self, *a, **kw): return b""
            def exportar_pdf(self, html, ruta_destino=None):
                self.html = html; return b"PDF-BYTES"
            def exportar_csv(self, *a, **kw): return b""

        est = _FakeEst(1); est.nombre = "Ana"; est.apellido = "Ruiz"
        repo = FakeConvRepo()
        exp = _FakeExp()
        svc = ConvivenciaService(
            repo=repo,
            configuracion_svc_provider=lambda: _FakeConfigSvc(_NIVELES),
            periodo_svc_provider=lambda: _FakePeriodoSvc(),
            estudiante_svc_provider=lambda: _FakeEstSvc([est]),
            exporter=exp,
        )
        bytes_ = svc.exportar_reporte_periodo_grupo(10, 5, "pdf", titulo="Reporte X")
        assert bytes_ == b"PDF-BYTES"
        # HTML compuesto por el servicio contiene columnas del reporte
        assert "<th>Estudiante</th>" in exp.html
        assert "<th>Concepto</th>" in exp.html
        assert "Reporte X" in exp.html


# ===========================================================================
# Catálogo de categorías (convivencia_10)
# ===========================================================================

class TestCategoriasObservacion:
    def test_listar_categorias_delega_al_repo(self):
        """listar_categorias llama al repo con solo_activas=True por defecto."""
        repo = FakeConvRepo()
        # Precargar dos categorías: una activa y una inactiva.
        repo.guardar_categoria(
            CategoriaObservacion(nombre="Académico", activa=True)
        )
        repo.guardar_categoria(
            CategoriaObservacion(nombre="Archivada", activa=False)
        )
        svc = ConvivenciaService(repo=repo)
        resultado = svc.listar_categorias(solo_activas=True)
        assert len(resultado) == 1
        assert resultado[0].nombre == "Académico"
        # Con solo_activas=False deben aparecer ambas
        todas = svc.listar_categorias(solo_activas=False)
        assert len(todas) == 2

    def test_crear_categoria_llama_guardar(self):
        """crear_categoria persiste la categoría y retorna el objeto con id."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        dto = NuevaCategoriaDTO(nombre="Convivencia", es_comportamental=True)
        cat = svc.crear_categoria(dto)
        assert cat.id is not None
        assert cat.nombre == "Convivencia"
        assert cat.es_comportamental is True
        assert cat.activa is True
        # Verificar persistencia en repo
        assert len(repo._cats) == 1

    def test_desactivar_categoria_pone_activa_false(self):
        """desactivar_categoria setea activa=False en la categoría."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        # Crear primero una categoría activa
        dto = NuevaCategoriaDTO(nombre="Normas", es_comportamental=True)
        cat = svc.crear_categoria(dto)
        assert cat.activa is True
        # Desactivar
        desactivada = svc.desactivar_categoria(cat.id)
        assert desactivada.activa is False
        assert desactivada.nombre == "Normas"
        # El repo también refleja el cambio
        en_repo = repo.get_categoria(cat.id)
        assert en_repo.activa is False


# ===========================================================================
# Autorización por objeto: observaciones (convivencia_11)
# ===========================================================================

class _FakeAsignacionSvc:
    """Stub de AsignacionService: asignación con usuario_id configurable."""
    def __init__(self, usuario_id_titular: int):
        self._usuario_id_titular = usuario_id_titular

    def get_by_id(self, asig_id: int):
        class _Asig:
            pass
        a = _Asig()
        a.id = asig_id
        a.usuario_id = self._usuario_id_titular
        return a

    def listar_por_docente(self, usuario_id, periodo_id=None):
        return []


class TestObservacionAutorizacionPorObjeto:
    """Autorización por objeto (convivencia_11): profesores solo en sus asignaciones."""

    def test_profesor_no_autorizado_registrar_observacion_ajena(self):
        """Profesor intenta registrar obs de asignación que no es suya → PermissionError."""
        repo = FakeConvRepo()
        # asignacion_id=3 pertenece al titular usuario_id=99, no al profesor 50
        svc = ConvivenciaService(
            repo=repo,
            asignacion_svc_provider=lambda: _FakeAsignacionSvc(usuario_id_titular=99),
        )
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Obs ajena", categoria_id=1,
        )
        with pytest.raises(PermissionError, match="Solo puedes registrar"):
            svc.registrar_observacion(dto, usuario_id=50, usuario_rol="profesor")
        # No debe haber persistido nada
        assert repo._obs == {}

    def test_profesor_autorizado_registra_su_propia_observacion(self):
        """Profesor registra obs de su propia asignación → permitido."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(
            repo=repo,
            asignacion_svc_provider=lambda: _FakeAsignacionSvc(usuario_id_titular=50),
        )
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Obs propia", categoria_id=1,
        )
        obs = svc.registrar_observacion(dto, usuario_id=50, usuario_rol="profesor")
        assert obs.id is not None
        assert len(repo._obs) == 1

    def test_director_puede_registrar_sin_restriccion_de_asignacion(self):
        """Director no pasa por la verificación de asignación → acceso pleno."""
        repo = FakeConvRepo()
        # Aunque el provider diga que el titular es 99, el director (50) puede pasar
        svc = ConvivenciaService(
            repo=repo,
            asignacion_svc_provider=lambda: _FakeAsignacionSvc(usuario_id_titular=99),
        )
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Obs de director", categoria_id=1,
        )
        obs = svc.registrar_observacion(dto, usuario_id=50, usuario_rol="director")
        assert obs.id is not None

    def test_sin_asignacion_provider_no_bloquea_a_profesor(self):
        """Sin asignacion_svc_provider, compat retro: no bloquea aunque sea profesor."""
        svc, repo = _make_svc()  # sin asignacion_svc_provider
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Obs sin provider", categoria_id=1,
        )
        obs = svc.registrar_observacion(dto, usuario_id=50, usuario_rol="profesor")
        assert obs.id is not None


# ===========================================================================
# Catálogo de plantillas (convivencia_12)
# ===========================================================================

class TestPlantillasObservacion:
    def test_listar_plantillas_servicio(self):
        """listar_plantillas delega al repo con solo_activas=True y filtra por categoría."""
        repo = FakeConvRepo()
        # Insertar plantillas: una de cat 1, una de cat 2, una inactiva
        repo.guardar_plantilla(PlantillaObservacion(texto="Texto A", categoria_id=1, activa=True))
        repo.guardar_plantilla(PlantillaObservacion(texto="Texto B", categoria_id=2, activa=True))
        repo.guardar_plantilla(PlantillaObservacion(texto="Inactiva", categoria_id=1, activa=False))
        svc = ConvivenciaService(repo=repo)

        # Sin filtro: devuelve solo las activas
        todas_activas = svc.listar_plantillas()
        assert len(todas_activas) == 2
        textos = {p.texto for p in todas_activas}
        assert "Texto A" in textos
        assert "Texto B" in textos
        assert "Inactiva" not in textos

        # Filtrado por categoria_id=1: solo "Texto A"
        de_cat1 = svc.listar_plantillas(categoria_id=1)
        assert len(de_cat1) == 1
        assert de_cat1[0].texto == "Texto A"

        # Filtrado por categoria_id=2: solo "Texto B"
        de_cat2 = svc.listar_plantillas(categoria_id=2)
        assert len(de_cat2) == 1
        assert de_cat2[0].texto == "Texto B"

    def test_registrar_observacion_desde_plantilla_incrementa_uso(self):
        """registrar_observacion_desde_plantilla guarda obs con origen='plantilla' e incrementa uso."""
        repo = FakeConvRepo()
        # Insertar una plantilla
        plantilla = repo.guardar_plantilla(
            PlantillaObservacion(texto="Buen desempeño", categoria_id=1, uso_count=3)
        )
        svc = ConvivenciaService(repo=repo)
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto=plantilla.texto, categoria_id=1,
        )
        obs = svc.registrar_observacion_desde_plantilla(dto, plantilla.id)

        # La observación debe haberse guardado con origen="plantilla"
        assert obs.id is not None
        assert obs.origen == "plantilla"

        # El uso_count debe haber incrementado
        actualizada = repo.get_plantilla(plantilla.id)
        assert actualizada.uso_count == 4  # 3 + 1

    def test_registrar_observacion_desde_plantilla_upsert(self):
        """Si ya existe una observación para asig/periodo/estudiante, la actualiza."""
        repo = FakeConvRepo()
        plantilla = repo.guardar_plantilla(
            PlantillaObservacion(texto="Texto plantilla", categoria_id=1)
        )
        svc = ConvivenciaService(repo=repo)

        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Texto original", categoria_id=1,
        )
        # Primera vez → crea
        obs1 = svc.registrar_observacion_desde_plantilla(dto, plantilla.id)
        assert obs1.origen == "plantilla"

        # Segunda vez → actualiza (misma asig/periodo/estudiante)
        dto2 = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Texto actualizado", categoria_id=1,
        )
        obs2 = svc.registrar_observacion_desde_plantilla(dto2, plantilla.id)
        assert obs2.texto == "Texto actualizado"
        assert obs2.origen == "plantilla"

        # Solo debe haber una observación en el repo
        assert len(repo._obs) == 1

        # Uso incrementado 2 veces
        assert repo.get_plantilla(plantilla.id).uso_count == 2


# ===========================================================================
# Catálogo de retroalimentación (convivencia_13)
# ===========================================================================

class TestPromocionPlantillas:
    """Tests para promover_observacion_a_plantilla y listar_plantillas_sugeridas."""

    def _obs_en_repo(self, repo: FakeConvRepo) -> ObservacionPeriodo:
        """Inserta una observación de prueba y la retorna con id asignado."""
        return repo.guardar_observacion(
            ObservacionPeriodo(
                estudiante_id=1,
                asignacion_id=3,
                periodo_id=5,
                texto="Excelente participación",
                categoria_id=2,
            )
        )

    def test_promover_observacion_a_plantilla_crea_plantilla(self):
        """Director promueve una observación existente → se crea PlantillaObservacion."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        obs = self._obs_en_repo(repo)

        plantilla = svc.promover_observacion_a_plantilla(
            obs.id, usuario_id=10, usuario_rol="director"
        )

        assert isinstance(plantilla, PlantillaObservacion)
        assert plantilla.id is not None
        assert plantilla.texto == obs.texto
        assert plantilla.categoria_id == obs.categoria_id
        # Verificar que se persistió en el repo
        assert len(repo._plantillas) == 1

    def test_promover_observacion_coordinador_permitido(self):
        """Coordinador también tiene permiso para promover."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        obs = self._obs_en_repo(repo)

        plantilla = svc.promover_observacion_a_plantilla(
            obs.id, usuario_id=20, usuario_rol="coordinador"
        )
        assert plantilla.id is not None

    def test_promover_observacion_profesor_no_autorizado(self):
        """Profesor intenta promover → PermissionError, no se persiste."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        obs = self._obs_en_repo(repo)

        with pytest.raises(PermissionError):
            svc.promover_observacion_a_plantilla(
                obs.id, usuario_id=50, usuario_rol="profesor"
            )
        # Ninguna plantilla debe haberse creado
        assert len(repo._plantillas) == 0

    def test_promover_observacion_inexistente_lanza(self):
        """Si la observación no existe → ValueError."""
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.promover_observacion_a_plantilla(
                999, usuario_id=10, usuario_rol="director"
            )

    def test_listar_plantillas_sugeridas_limite(self):
        """listar_plantillas_sugeridas retorna como máximo `limite` elementos."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        # Insertar 8 plantillas con distintos uso_count
        for i in range(8):
            repo.guardar_plantilla(
                PlantillaObservacion(texto=f"Plantilla {i}", categoria_id=1, uso_count=i)
            )

        # limite=5 (default)
        sugeridas = svc.listar_plantillas_sugeridas()
        assert len(sugeridas) == 5

        # Las primeras deben ser las de mayor uso_count
        usos = [p.uso_count for p in sugeridas]
        assert usos == sorted(usos, reverse=True)

    def test_listar_plantillas_sugeridas_filtro_categoria(self):
        """listar_plantillas_sugeridas respeta el filtro de categoria_id."""
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        repo.guardar_plantilla(PlantillaObservacion(texto="Cat1-A", categoria_id=1, uso_count=10))
        repo.guardar_plantilla(PlantillaObservacion(texto="Cat1-B", categoria_id=1, uso_count=5))
        repo.guardar_plantilla(PlantillaObservacion(texto="Cat2-A", categoria_id=2, uso_count=8))

        sugeridas_cat1 = svc.listar_plantillas_sugeridas(categoria_id=1, limite=10)
        assert len(sugeridas_cat1) == 2
        assert all(p.categoria_id == 1 for p in sugeridas_cat1)

        sugeridas_cat2 = svc.listar_plantillas_sugeridas(categoria_id=2, limite=10)
        assert len(sugeridas_cat2) == 1
        assert sugeridas_cat2[0].texto == "Cat2-A"


