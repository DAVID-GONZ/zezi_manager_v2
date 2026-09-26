"""
Tests de contrato de conteos, verificación incremental y rendimiento a volumen.

T4  — `contar_eventos` y `contar_cambios` con filtros.
T7  — verificación incremental: checkpoint, detección de roto, compromiso §2.
T13 — test de rendimiento: 50 000 filas sembradas con cadena válida.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    SeveridadEvento,
    TipoEventoSesion,
)
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
# T4 — Conteo de eventos con filtros
# ---------------------------------------------------------------------------

class TestContarEventos:
    def _sembrar_eventos(self, repo, n: int, tipo=TipoEventoSesion.LOGIN_EXITOSO,
                         usuario_id=None, institucion_id=None) -> list[EventoSesion]:
        resultado = []
        for i in range(n):
            ev = EventoSesion(
                usuario=f"user_{i}",
                usuario_id=usuario_id,
                tipo_evento=tipo,
                institucion_id=institucion_id,
            )
            resultado.append(repo.registrar_evento(ev))
        return resultado

    def test_contar_sin_filtros_devuelve_total(self, repo):
        self._sembrar_eventos(repo, 7)
        total = repo.contar_eventos(FiltroAuditoriaDTO())
        assert total == 7

    def test_contar_filtra_por_tipo_evento(self, repo):
        self._sembrar_eventos(repo, 5, tipo=TipoEventoSesion.LOGIN_EXITOSO)
        self._sembrar_eventos(repo, 3, tipo=TipoEventoSesion.LOGOUT)
        filtro = FiltroAuditoriaDTO(tipo_evento=TipoEventoSesion.LOGOUT)
        assert repo.contar_eventos(filtro) == 3

    def test_contar_ignora_pagina_y_por_pagina(self, repo):
        """M eventos con filtro que selecciona M filas: conteo == M
        independientemente de pagina y por_pagina."""
        self._sembrar_eventos(repo, 10)
        # Contar con paginación muy pequeña: debería devolver el total real
        filtro_p1 = FiltroAuditoriaDTO(pagina=1, por_pagina=2)
        filtro_p3 = FiltroAuditoriaDTO(pagina=3, por_pagina=2)
        assert repo.contar_eventos(filtro_p1) == 10
        assert repo.contar_eventos(filtro_p3) == 10

    def test_contar_filtro_usuario_id(self, repo):
        self._sembrar_eventos(repo, 4, usuario_id=99)
        self._sembrar_eventos(repo, 2, usuario_id=42)
        filtro = FiltroAuditoriaDTO(usuario_id=99)
        assert repo.contar_eventos(filtro) == 4

    def test_contar_db_vacia_devuelve_cero(self, repo):
        assert repo.contar_eventos(FiltroAuditoriaDTO()) == 0


class TestContarCambios:
    def _sembrar_cambios(self, repo, n: int, tabla="notas",
                         accion=AccionCambio.UPDATE) -> list[RegistroCambio]:
        resultado = []
        for i in range(n):
            r = RegistroCambio(
                accion=accion,
                tabla=tabla,
                registro_id=i + 1,
                valor_nuevo=f'{{"v": {i}}}',
            )
            resultado.append(repo.registrar_cambio(r))
        return resultado

    def test_contar_sin_filtros_devuelve_total(self, repo):
        self._sembrar_cambios(repo, 6)
        assert repo.contar_cambios(FiltroAuditoriaDTO()) == 6

    def test_contar_filtra_por_tabla(self, repo):
        self._sembrar_cambios(repo, 3, tabla="estudiantes")
        self._sembrar_cambios(repo, 2, tabla="notas")
        filtro = FiltroAuditoriaDTO(tabla="estudiantes")
        assert repo.contar_cambios(filtro) == 3

    def test_contar_ignora_pagina_y_por_pagina(self, repo):
        self._sembrar_cambios(repo, 8)
        filtro_pg = FiltroAuditoriaDTO(pagina=2, por_pagina=3)
        assert repo.contar_cambios(filtro_pg) == 8

    def test_contar_filtra_por_accion(self, repo):
        self._sembrar_cambios(repo, 5, accion=AccionCambio.CREATE)
        self._sembrar_cambios(repo, 2, accion=AccionCambio.DELETE)
        filtro = FiltroAuditoriaDTO(accion=AccionCambio.DELETE)
        assert repo.contar_cambios(filtro) == 2


# ---------------------------------------------------------------------------
# T7 — Verificación incremental de la cadena
# ---------------------------------------------------------------------------

def _sembrar_eventos_n(repo, n: int) -> list[EventoSesion]:
    result = []
    for i in range(n):
        ev = EventoSesion(
            usuario=f"user_{i}",
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
        )
        result.append(repo.registrar_evento(ev))
    return result


def _sembrar_cambios_n(repo, n: int) -> list[RegistroCambio]:
    result = []
    for i in range(n):
        r = RegistroCambio(
            accion=AccionCambio.UPDATE,
            tabla="test",
            registro_id=i + 1,
            valor_nuevo=f'{{"v": {i}}}',
        )
        result.append(repo.registrar_cambio(r))
    return result


class TestVerificacionIncremental:
    def test_a_cadena_integra_checkpoint_avanzado(self, repo, conn):
        """(a) Cadena íntegra → None y checkpoint avanzado.

        Protocolo: sembrar 5 filas, verificación completa establece el
        checkpoint, luego sembrar 5 más y la verificación incremental las
        verifica y avanza el checkpoint.
        """
        _sembrar_cambios_n(repo, 5)
        # Primera verificación completa crea el checkpoint
        assert repo.verificar_cadena_cambios(completa=True) is None
        cp_id_1, _ = repo._leer_checkpoint("audit_log")
        assert cp_id_1 == 5

        # Sembrar 5 filas más
        _sembrar_cambios_n(repo, 5)

        # Verificación incremental (default) avanza el checkpoint
        assert repo.verificar_cadena_cambios() is None
        cp_id_2, _ = repo._leer_checkpoint("audit_log")
        assert cp_id_2 == 10, "El checkpoint debe avanzar a la última fila verificada"

    def test_b_alterar_fila_posterior_al_checkpoint_la_detecta(self, repo, conn):
        """(b) Alterar una fila POSTERIOR al checkpoint → devuelve su id y el
        checkpoint no se mueve."""
        _sembrar_cambios_n(repo, 5)

        # Establecer checkpoint con completa=True
        assert repo.verificar_cadena_cambios(completa=True) is None
        cp_id_antes, _ = repo._leer_checkpoint("audit_log")
        assert cp_id_antes == 5

        # Insertar una fila nueva (id=6)
        nueva = repo.registrar_cambio(RegistroCambio(
            accion=AccionCambio.CREATE, tabla="test", registro_id=99,
            valor_nuevo='{"v": 99}',
        ))

        # Alterar la fila nueva por SQL (posterior al checkpoint)
        conn.execute(
            "UPDATE audit_log SET valor_nuevo = '{\"v\": 999}' WHERE id = ?",
            (nueva.id,),
        )
        conn.commit()

        # La verificación incremental debe detectarla
        id_roto = repo.verificar_cadena_cambios()
        assert id_roto == nueva.id

        # El checkpoint NO debe haberse movido (R10)
        cp_id_despues, _ = repo._leer_checkpoint("audit_log")
        assert cp_id_despues == cp_id_antes

    def test_c_alterar_fila_anterior_al_checkpoint_pasa_incremental(self, repo, conn):
        """(c) Alterar una fila ANTERIOR al checkpoint → la incremental pasa en
        verde; la completa (`completa=True`) la detecta.

        Documenta el compromiso de §2 del diseño: no es un bug.
        """
        _sembrar_cambios_n(repo, 10)

        # Establecer checkpoint
        assert repo.verificar_cadena_cambios(completa=True) is None
        cp_id, _ = repo._leer_checkpoint("audit_log")
        assert cp_id == 10

        # Alterar una fila ANTERIOR al checkpoint (id=5)
        conn.execute(
            "UPDATE audit_log SET valor_nuevo = '{\"alterado\": true}' WHERE id = 5",
        )
        conn.commit()

        # Incremental: no ve filas nuevas → pasa en verde (compromiso §2)
        id_roto_incremental = repo.verificar_cadena_cambios()
        assert id_roto_incremental is None, (
            "La verificación incremental NO detecta tamperado previo al checkpoint "
            "(compromiso documentado §2 del diseño)"
        )

        # Completa: detecta la fila rota
        id_roto_completa = repo.verificar_cadena_cambios(completa=True)
        assert id_roto_completa == 5


class TestResumenEventos:
    def test_resumen_eventos_vacio(self, repo):
        from datetime import datetime
        agg = repo.resumen_eventos(datetime(2000, 1, 1))
        assert agg.get("logins_hoy", 0) == 0
        assert agg.get("usuarios_distintos", 0) == 0
        assert agg.get("denegados_criticos", 0) == 0

    def test_resumen_eventos_por_tipo(self, repo):
        from datetime import datetime
        for _ in range(3):
            repo.registrar_evento(EventoSesion(
                usuario="u1", usuario_id=1,
                tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
            ))
        repo.registrar_evento(EventoSesion(
            usuario="u2", usuario_id=2,
            tipo_evento=TipoEventoSesion.LOGOUT,
        ))
        agg = repo.resumen_eventos(datetime(2000, 1, 1))
        por_tipo = agg.get("por_tipo", {})
        assert por_tipo.get("LOGIN_EXITOSO", 0) == 3
        assert por_tipo.get("LOGOUT", 0) == 1
        assert agg.get("usuarios_distintos", 0) == 1  # solo u1 tiene logins

    def test_resumen_eventos_denegados_criticos(self, repo):
        from datetime import datetime
        repo.registrar_evento(EventoSesion(
            usuario="u1", tipo_evento=TipoEventoSesion.ACCESO_DENEGADO,
            severidad=SeveridadEvento.CRITICA,
        ))
        repo.registrar_evento(EventoSesion(
            usuario="u2", tipo_evento=TipoEventoSesion.ACCESO_DENEGADO,
            severidad=SeveridadEvento.ADVERTENCIA,
        ))
        agg = repo.resumen_eventos(datetime(2000, 1, 1))
        assert agg.get("denegados_criticos", 0) == 1


# ---------------------------------------------------------------------------
# T13 — Test de rendimiento: 50 000 filas (marcado como slow)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_volumen_50000_filas_verificacion_incremental(conn):
    """
    Siembra 50 000 filas en audit_log con cadena válida, verifica que:
    - La primera verificación completa termina sin error.
    - La segunda verificación incremental (sin filas nuevas) responde
      en menos de UMBRAL_SEGUNDOS.

    Marcado como @pytest.mark.slow para excluirlo de la suite rápida.
    """
    UMBRAL_SEGUNDOS = 2.0  # la incremental sin cambios debe ser casi instantánea

    repo = SqliteAuditoriaRepository(conn=conn)

    # Sembrar 50 000 filas con cadena válida usando registrar_cambios_masivos
    LOTE = 1_000
    for offset in range(0, 50_000, LOTE):
        registros = [
            RegistroCambio(
                accion=AccionCambio.UPDATE,
                tabla="volumen_test",
                registro_id=offset + i + 1,
                valor_nuevo=f'{{"v": {offset + i}}}',
            )
            for i in range(LOTE)
        ]
        repo.registrar_cambios_masivos(registros)

    # Primera verificación completa: verifica toda la cadena y guarda checkpoint
    time.perf_counter()
    id_roto = repo.verificar_cadena_cambios(completa=True)
    time.perf_counter()
    assert id_roto is None, f"La cadena de 50 000 filas debería ser íntegra; id_roto={id_roto}"

    # Checkpoint debe estar en 50 000
    cp_id, _ = repo._leer_checkpoint("audit_log")
    assert cp_id == 50_000

    # Segunda verificación incremental sin filas nuevas: debe ser rápida
    t2 = time.perf_counter()
    id_roto2 = repo.verificar_cadena_cambios()
    t3 = time.perf_counter()
    assert id_roto2 is None
    duracion_incremental = t3 - t2
    assert duracion_incremental < UMBRAL_SEGUNDOS, (
        f"La verificación incremental sin filas nuevas tardó {duracion_incremental:.3f}s "
        f"(umbral: {UMBRAL_SEGUNDOS}s)"
    )
