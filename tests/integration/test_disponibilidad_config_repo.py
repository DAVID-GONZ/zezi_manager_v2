"""
Tests de integración — paso_15b
Disponibilidad docente y config_generacion en SqliteInfraestructuraRepository.
"""
from __future__ import annotations

import pytest

from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.services.infraestructura_service import InfraestructuraService
from src.domain.models.infraestructura import (
    DisponibilidadDocente,
    ConfigGeneracion,
    PesosGeneracion,
)


# =============================================================================
# Helpers
# =============================================================================

def make_repo(db_conn):
    return SqliteInfraestructuraRepository(conn=db_conn)


def make_service(db_conn):
    return InfraestructuraService(repo=make_repo(db_conn))


# =============================================================================
# Disponibilidad docente
# =============================================================================

class TestDisponibilidadDocente:

    def test_upsert_inserta_nueva_fila(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        d = DisponibilidadDocente(
            usuario_id=usuario_id, dia_semana="Lunes", franja_orden=2, disponible=False
        )
        result = repo.upsert_disponibilidad(d)
        assert result.id is not None
        assert result.disponible is False

    def test_upsert_idempotente(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        d = DisponibilidadDocente(
            usuario_id=usuario_id, dia_semana="Martes", franja_orden=1, disponible=False
        )
        r1 = repo.upsert_disponibilidad(d)
        # segunda llamada: actualizar a disponible=True
        d2 = DisponibilidadDocente(
            usuario_id=usuario_id, dia_semana="Martes", franja_orden=1, disponible=True
        )
        r2 = repo.upsert_disponibilidad(d2)
        assert r2.disponible is True
        # Verificar que no hay duplicados
        lista = repo.listar_disponibilidad_docente(usuario_id)
        martes1 = [x for x in lista if x.dia_semana == "Martes" and x.franja_orden == 1]
        assert len(martes1) == 1

    def test_es_disponible_slot_no_registrado_devuelve_true(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        # slot que no está en la tabla → disponible por defecto
        assert repo.es_disponible(usuario_id, "Viernes", 99) is True

    def test_es_disponible_slot_bloqueado_devuelve_false(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        d = DisponibilidadDocente(
            usuario_id=usuario_id, dia_semana="Jueves", franja_orden=3, disponible=False
        )
        repo.upsert_disponibilidad(d)
        assert repo.es_disponible(usuario_id, "Jueves", 3) is False

    def test_es_disponible_slot_explicitamente_disponible(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        d = DisponibilidadDocente(
            usuario_id=usuario_id, dia_semana="Miércoles", franja_orden=1, disponible=True
        )
        repo.upsert_disponibilidad(d)
        assert repo.es_disponible(usuario_id, "Miércoles", 1) is True

    def test_cargar_disponibilidad_lote(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        slots = [
            {"dia_semana": "Lunes", "franja_orden": 1},
            {"dia_semana": "Lunes", "franja_orden": 2},
            {"dia_semana": "Martes", "franja_orden": 3},
        ]
        count = repo.cargar_disponibilidad_lote(usuario_id, slots)
        assert count == 3
        assert repo.es_disponible(usuario_id, "Lunes", 1) is False
        assert repo.es_disponible(usuario_id, "Lunes", 2) is False

    def test_limpiar_disponibilidad_docente(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        usuario_id = seed_result.usuario_ids["prof_test"]
        slots = [
            {"dia_semana": "Lunes", "franja_orden": 1},
            {"dia_semana": "Martes", "franja_orden": 2},
        ]
        repo.cargar_disponibilidad_lote(usuario_id, slots)
        borradas = repo.limpiar_disponibilidad_docente(usuario_id)
        assert borradas >= 2
        lista = repo.listar_disponibilidad_docente(usuario_id)
        assert lista == []


# =============================================================================
# Config generación
# =============================================================================

class TestConfigGeneracion:

    def _make_config(self, seed_result, nombre="Test cfg") -> ConfigGeneracion:
        return ConfigGeneracion(
            nombre=nombre,
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=1,
        )

    def test_crear_y_leer(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        cfg = ConfigGeneracion(
            nombre="Config A",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
        )
        creada = repo.crear_config_generacion(cfg)
        assert creada.id is not None
        leida = repo.get_config_generacion(creada.id)
        assert leida is not None
        assert leida.nombre == "Config A"
        assert leida.estado == "borrador"

    def test_listar_configs(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        configs = repo.listar_configs_generacion()
        # seed_test crea "Config inicial"
        assert len(configs) >= 1

    def test_listar_por_periodo(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        periodo_id = seed_result.periodo_ids[0]
        configs = repo.listar_configs_generacion(periodo_id=periodo_id)
        assert all(c.periodo_id == periodo_id for c in configs)

    def test_eliminar_config(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        cfg = ConfigGeneracion(
            nombre="Config eliminar",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
        )
        creada = repo.crear_config_generacion(cfg)
        assert repo.eliminar_config_generacion(creada.id) is True
        assert repo.get_config_generacion(creada.id) is None

    def test_cambiar_estado_borrador_a_generado(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        cfg = ConfigGeneracion(
            nombre="Config estado",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
        )
        creada = repo.crear_config_generacion(cfg)
        actualizada = repo.cambiar_estado_config(creada.id, "generado")
        assert actualizada.estado == "generado"

    def test_cambiar_estado_invalido_lanza_error(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        cfg = ConfigGeneracion(
            nombre="Config trans inv",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
            estado="borrador",
        )
        creada = repo.crear_config_generacion(cfg)
        # Poner en generado primero, luego en aplicado
        repo.cambiar_estado_config(creada.id, "generado")
        repo.cambiar_estado_config(creada.id, "aplicado")
        # Desde aplicado no hay transición válida
        with pytest.raises(ValueError, match="inválida"):
            repo.cambiar_estado_config(creada.id, "borrador")

    def test_duplicar_config(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        cfg = ConfigGeneracion(
            nombre="Original",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
        )
        orig = repo.crear_config_generacion(cfg)
        copia = repo.duplicar_config_generacion(orig.id)
        assert copia.id != orig.id
        assert copia.nombre == "Original (copia)"
        assert copia.estado == "borrador"
        assert copia.escenario_destino_id is None

    def test_seed_creo_al_menos_una_config_borrador(self, db_conn):
        repo = make_repo(db_conn)
        configs = repo.listar_configs_generacion()
        borradores = [c for c in configs if c.estado == "borrador"]
        assert len(borradores) >= 1

    def test_pesos_json_serializado_correctamente(self, db_conn, seed_result):
        repo = make_repo(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        pesos = PesosGeneracion(huecos=0.5, distribucion=1.5, compactacion=0.25)
        cfg = ConfigGeneracion(
            nombre="Config pesos json",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
            pesos=pesos,
        )
        creada = repo.crear_config_generacion(cfg)
        leida = repo.get_config_generacion(creada.id)
        assert leida.pesos.huecos == 0.5
        assert leida.pesos.distribucion == 1.5
        assert leida.pesos.compactacion == 0.25

    def test_actualizar_pesos_como_dict_no_lanza_y_persiste(
        self, db_conn, seed_result
    ):
        # Regresión: la página "Generar horario" pasa pesos como dict crudo.
        # actualizar_config_generacion debe envolverlo en PesosGeneracion antes
        # del model_copy para que el repo pueda serializarlo (c.pesos.model_dump()).
        service = make_service(db_conn)
        plantilla_id = db_conn.execute(
            "SELECT id FROM plantillas_franja LIMIT 1"
        ).fetchone()[0]
        creada = service.crear_config_generacion(
            nombre="Config pesos dict",
            periodo_id=seed_result.periodo_ids[0],
            anio_id=seed_result.anio_id,
            plantilla_id=plantilla_id,
        )
        # No debe lanzar AttributeError al pasar pesos como dict.
        service.actualizar_config_generacion(
            creada.id,
            pesos={"huecos": 1.5, "distribucion": 0.5, "compactacion": 0.2},
        )
        leida = service.get_config_generacion(creada.id)
        assert isinstance(leida.pesos, PesosGeneracion)
        assert leida.pesos.huecos == 1.5
        assert leida.pesos.distribucion == 0.5
        assert leida.pesos.compactacion == 0.2
