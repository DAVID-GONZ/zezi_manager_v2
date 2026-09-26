"""
Tests de SqliteAuditoriaRepository con el esquema obs_06.

Cubre:
  - T8: usuario e ip_address se persisten y relean correctamente en audit_log.
        Alterar esos campos por SQL directo rompe la cadena de hashes.
  - T16: ráfaga de LOGIN_FALLIDO desde la misma IP dispara ALERTA_IP;
         con IP None la política no se invoca.
"""
from __future__ import annotations

import logging
import sqlite3

import pytest

from src.domain.models.auditoria import (
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    TipoEventoSesion,
)
from src.domain.policies.alerta_ip import MAX_FALLOS_IP, registrar_fallo_ip, reset_all
from src.infrastructure.db.repositories.sqlite_auditoria_repo import (
    SqliteAuditoriaRepository,
)
from src.infrastructure.db.schema import SCHEMA

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """Base de datos SQLite en memoria con el esquema completo."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    for ddl in SCHEMA:
        c.execute(ddl)
    c.commit()
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return SqliteAuditoriaRepository(conn=conn)


# ---------------------------------------------------------------------------
# T8 — usuario e ip_address se persisten y se relean (audit_log)
# ---------------------------------------------------------------------------

class TestAuditLogIdentidad:
    def test_usuario_e_ip_se_persisten(self, repo, conn):
        """Una fila insertada con usuario/ip_address se relee con esos valores."""
        registro = RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"nombre": "Ana"},
            registro_id=1,
            usuario_id=42,
            usuario="jdocente",
            ip_address="192.168.1.10",
        )
        repo.registrar_cambio(registro)

        row = conn.execute("SELECT usuario, ip_address FROM audit_log LIMIT 1").fetchone()
        assert row["usuario"] == "jdocente"
        assert row["ip_address"] == "192.168.1.10"

    def test_usuario_none_se_permite(self, repo, conn):
        """usuario e ip_address pueden ser None (cambios sin sesión identificada)."""
        registro = RegistroCambio.para_actualizacion(
            tabla="notas",
            datos_anteriores={"valor": "3.5"},
            datos_nuevos={"valor": "4.0"},
            registro_id=7,
        )
        repo.registrar_cambio(registro)

        row = conn.execute("SELECT usuario, ip_address FROM audit_log LIMIT 1").fetchone()
        assert row["usuario"] is None
        assert row["ip_address"] is None

    def test_alterar_usuario_rompe_cadena(self, repo, conn):
        """Reescribir usuario por SQL directo rompe la cadena de hashes."""
        registro = RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"nombre": "Pedro"},
            registro_id=5,
            usuario_id=10,
            usuario="autentico",
            ip_address="10.0.0.1",
        )
        guardado = repo.registrar_cambio(registro)

        # Cadena íntegra antes de manipular
        assert repo.verificar_cadena_cambios() is None

        # Reescribir el username por SQL (manipulación de la bitácora)
        conn.execute(
            "UPDATE audit_log SET usuario = 'falsificado' WHERE id = ?",
            (guardado.id,),
        )
        conn.commit()

        id_roto = repo.verificar_cadena_cambios()
        assert id_roto == guardado.id

    def test_alterar_ip_rompe_cadena(self, repo, conn):
        """Reescribir ip_address por SQL directo rompe la cadena de hashes."""
        registro = RegistroCambio.para_eliminacion(
            tabla="notas",
            datos_anteriores={"valor": "2.0"},
            registro_id=99,
            usuario="profe",
            ip_address="172.16.0.5",
        )
        guardado = repo.registrar_cambio(registro)

        assert repo.verificar_cadena_cambios() is None

        conn.execute(
            "UPDATE audit_log SET ip_address = '8.8.8.8' WHERE id = ?",
            (guardado.id,),
        )
        conn.commit()

        id_roto = repo.verificar_cadena_cambios()
        assert id_roto == guardado.id

    def test_objetivo_en_evento_se_persiste(self, repo, conn):
        """objetivo se almacena y se relee correctamente en la tabla auditoria."""
        evento = EventoSesion(
            usuario="admin",
            usuario_id=1,
            tipo_evento=TipoEventoSesion.VER_COMO_INICIO,
            objetivo="director_perez",
            ip_address="127.0.0.1",
        )
        repo.registrar_evento(evento)

        row = conn.execute("SELECT objetivo FROM auditoria LIMIT 1").fetchone()
        assert row["objetivo"] == "director_perez"


# ---------------------------------------------------------------------------
# T16 — Ráfaga de IP dispara ALERTA_IP (alerta_ip.py)
# ---------------------------------------------------------------------------

class _CapturingHandler(logging.Handler):
    def __init__(self, records: list):
        super().__init__()
        self._records = records

    def emit(self, record: logging.LogRecord) -> None:
        self._records.append(record)


class TestAlertaIP:
    def setup_method(self):
        reset_all()
        self.records: list[logging.LogRecord] = []
        self.handler = _CapturingHandler(self.records)
        logging.getLogger("zeci.security").addHandler(self.handler)
        logging.disable(logging.NOTSET)

    def teardown_method(self):
        logging.getLogger("zeci.security").removeHandler(self.handler)
        logging.disable(logging.CRITICAL)
        reset_all()

    def test_rafaga_dispara_alerta(self):
        """`MAX_FALLOS_IP` fallos desde la misma IP emiten ALERTA_IP."""
        ip = "203.0.113.42"
        for _ in range(MAX_FALLOS_IP):
            registrar_fallo_ip(ip)

        alertas = [
            r for r in self.records
            if getattr(r, "tipo_evento", None) == "ALERTA_IP"
        ]
        assert len(alertas) >= 1
        assert getattr(alertas[0], "ip", None) == ip

    def test_por_debajo_del_umbral_no_dispara(self):
        """Menos de `MAX_FALLOS_IP` fallos no emiten la alerta."""
        ip = "203.0.113.99"
        for _ in range(MAX_FALLOS_IP - 1):
            registrar_fallo_ip(ip)

        alertas = [
            r for r in self.records
            if getattr(r, "tipo_evento", None) == "ALERTA_IP"
        ]
        assert len(alertas) == 0

    def test_ip_none_no_invoca_politica(self):
        """Con IP None la política ignora el evento (no registra ni alerta)."""
        for _ in range(MAX_FALLOS_IP + 2):
            registrar_fallo_ip(None)  # type: ignore[arg-type]

        alertas = [
            r for r in self.records
            if getattr(r, "tipo_evento", None) == "ALERTA_IP"
        ]
        assert len(alertas) == 0

    def test_ip_vacia_no_invoca_politica(self):
        """Con IP vacía la política ignora el evento."""
        for _ in range(MAX_FALLOS_IP + 2):
            registrar_fallo_ip("")

        alertas = [
            r for r in self.records
            if getattr(r, "tipo_evento", None) == "ALERTA_IP"
        ]
        assert len(alertas) == 0


# ---------------------------------------------------------------------------
# T9 — filtro sin_institucion en listar_cambios (obs_09)
# ---------------------------------------------------------------------------

class TestFiltroSinInstitucion:
    """Con filas de institución 1, de institución 2 y con NULL, cada modo devuelve exactamente su subconjunto."""

    def _insertar_cambio(self, repo, registro_id: int, institucion_id: int | None) -> None:
        repo.registrar_cambio(RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"id": registro_id},
            registro_id=registro_id,
            usuario_id=1,
            institucion_id=institucion_id,
        ))

    def test_filtro_por_institucion_1(self, repo):
        """Solo devuelve filas de institución 1."""
        self._insertar_cambio(repo, 1, 1)
        self._insertar_cambio(repo, 2, 2)
        self._insertar_cambio(repo, 3, None)

        filtro = FiltroAuditoriaDTO(institucion_id=1, por_pagina=100)
        cambios = repo.listar_cambios(filtro)
        assert len(cambios) == 1
        assert cambios[0].registro_id == 1
        assert cambios[0].institucion_id == 1

    def test_filtro_por_institucion_2(self, repo):
        """Solo devuelve filas de institución 2."""
        self._insertar_cambio(repo, 1, 1)
        self._insertar_cambio(repo, 2, 2)
        self._insertar_cambio(repo, 3, None)

        filtro = FiltroAuditoriaDTO(institucion_id=2, por_pagina=100)
        cambios = repo.listar_cambios(filtro)
        assert len(cambios) == 1
        assert cambios[0].registro_id == 2

    def test_filtro_sin_institucion_devuelve_nulls(self, repo):
        """sin_institucion=True devuelve exactamente las filas con institucion_id IS NULL."""
        self._insertar_cambio(repo, 1, 1)
        self._insertar_cambio(repo, 2, 2)
        self._insertar_cambio(repo, 3, None)

        filtro = FiltroAuditoriaDTO(sin_institucion=True, por_pagina=100)
        cambios = repo.listar_cambios(filtro)
        assert len(cambios) == 1
        assert cambios[0].registro_id == 3
        assert cambios[0].institucion_id is None

    def test_sin_filtro_devuelve_todos(self, repo):
        """Sin ningún filtro de institución, se devuelven todas las filas."""
        self._insertar_cambio(repo, 1, 1)
        self._insertar_cambio(repo, 2, 2)
        self._insertar_cambio(repo, 3, None)

        filtro = FiltroAuditoriaDTO(por_pagina=100)
        cambios = repo.listar_cambios(filtro)
        assert len(cambios) == 3

    def test_sin_institucion_y_institucion_id_son_excluyentes(self, repo):
        """sin_institucion=True tiene precedencia sobre institucion_id (diseño §6)."""
        self._insertar_cambio(repo, 1, 1)
        self._insertar_cambio(repo, 2, None)

        # Aunque se pase institucion_id=1, sin_institucion=True tiene precedencia
        filtro = FiltroAuditoriaDTO(sin_institucion=True, institucion_id=1, por_pagina=100)
        cambios = repo.listar_cambios(filtro)
        # Solo los NULL deben aparecer
        assert all(c.institucion_id is None for c in cambios)

    def test_filtro_registro_id(self, repo):
        """registro_id acota la búsqueda a una entidad concreta (R11)."""
        self._insertar_cambio(repo, 10, 1)
        self._insertar_cambio(repo, 20, 1)
        self._insertar_cambio(repo, 10, 2)  # mismo registro_id, otra institución

        filtro = FiltroAuditoriaDTO(registro_id=10, por_pagina=100)
        cambios = repo.listar_cambios(filtro)
        assert len(cambios) == 2
        assert all(c.registro_id == 10 for c in cambios)

    def test_contar_cambios_respeta_sin_institucion(self, repo):
        """contar_cambios usa el mismo WHERE que listar_cambios."""
        self._insertar_cambio(repo, 1, 1)
        self._insertar_cambio(repo, 2, None)
        self._insertar_cambio(repo, 3, None)

        filtro = FiltroAuditoriaDTO(sin_institucion=True, por_pagina=100)
        assert repo.contar_cambios(filtro) == 2
