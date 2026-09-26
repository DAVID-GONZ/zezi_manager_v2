"""
Tests del servicio de retención de la bitácora (obs_12, T11).

Cubre:
  (a) Si la escritura del archivo falla, no se borra ninguna fila (R9).
  (b) Si el hash releído no cuadra, no se borra ninguna fila (R9).
  (c) Tras una purga correcta, el evento AUDITORIA_PURGADA contiene ruta,
      hash, rango y número de filas; y el checkpoint queda reancalado (R10/R11).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import ReglaDeNegocioError
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    TipoEventoSesion,
)
from src.services.auditoria_retencion_service import AuditoriaRetencionService


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _hacer_cambio(id_: int) -> RegistroCambio:
    return RegistroCambio(
        id=id_,
        usuario="u1",
        usuario_id=1,
        accion=AccionCambio.UPDATE,
        tabla="estudiantes",
        registro_id=id_,
        valor_anterior=json.dumps({"nombre": f"antes_{id_}"}),
        valor_nuevo=json.dumps({"nombre": f"despues_{id_}"}),
        timestamp=datetime(2026, 1, id_, 10, 0),
    )


class _FakeRepo:
    """Repo mínimo para tests del servicio de retención."""

    def __init__(
        self,
        cambios: list[RegistroCambio] | None = None,
        id_roto: int | None = None,
    ) -> None:
        self._cambios = cambios or []
        self._id_roto = id_roto
        self._eliminados_hasta: int | None = None
        self._checkpoint_guardado: tuple[str, int, str | None] | None = None
        self._eventos: list[EventoSesion] = []

    def rango_de(self, tabla: str, filtro: FiltroAuditoriaDTO):
        if not self._cambios:
            return None
        ids = [r.id for r in self._cambios if r.id is not None]
        return (min(ids), max(ids))

    def listar_cambios_tramo(self, tabla, id_desde, id_hasta, scope, *, lote=5_000):
        batch = [r for r in self._cambios if r.id is not None and id_desde <= r.id <= id_hasta]
        if batch:
            yield batch

    def hash_de_fila(self, tabla: str, fila_id: int) -> str | None:
        return f"hash_{fila_id}"

    def _verificar_tramo_ids(self, tabla: str, id_desde: int, id_hasta: int) -> int | None:
        return self._id_roto

    def eliminar_hasta(self, tabla: str, id_hasta: int, scope) -> int:
        """Simula la eliminación y registra el id hasta el que se borró."""
        self._eliminados_hasta = id_hasta
        return len([r for r in self._cambios if r.id is not None and r.id <= id_hasta])

    def _guardar_checkpoint(self, tabla: str, ultimo_id: int, ultimo_hash: str | None) -> None:
        self._checkpoint_guardado = (tabla, ultimo_id, ultimo_hash)

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        self._eventos.append(evento)
        return evento


# ---------------------------------------------------------------------------
# Tests (a): escritura del archivo falla → no se borra ninguna fila
# ---------------------------------------------------------------------------


class TestFalloEscritura:
    def test_no_borra_si_escritura_falla(self, tmp_path: Path):
        """(a) Si _escribir_jsonl lanza IOError, ninguna fila debe eliminarse."""
        cambios = [_hacer_cambio(1), _hacer_cambio(2), _hacer_cambio(3)]
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        with patch.object(
            AuditoriaRetencionService,
            "_escribir_jsonl",
            side_effect=OSError("Disco lleno"),
        ):
            with pytest.raises(OSError, match="Disco lleno"):
                svc.archivar_y_purgar(
                    tabla="audit_log",
                    hasta=datetime(2026, 12, 31),
                    scope="*",
                    actor="admin",
                )

        # La operación no llegó a eliminar ninguna fila
        assert repo._eliminados_hasta is None  # (a)


# ---------------------------------------------------------------------------
# Tests (b): hash releído no cuadra → no se borra ninguna fila
# ---------------------------------------------------------------------------


class TestFalloHashReleido:
    def test_no_borra_si_hash_releido_no_coincide(self, tmp_path: Path):
        """(b) Si el hash del archivo releído no coincide, no se eliminan filas."""
        cambios = [_hacer_cambio(1), _hacer_cambio(2)]
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        # _escribir_jsonl devuelve un hash correcto,
        # pero hacemos que _sha256_file devuelva algo diferente.
        with patch(
            "src.services.auditoria_retencion_service._sha256_file",
            return_value="hash_incorrecto_que_no_coincide",
        ):
            with pytest.raises(ReglaDeNegocioError, match="Hash del archivo releído"):
                svc.archivar_y_purgar(
                    tabla="audit_log",
                    hasta=datetime(2026, 12, 31),
                    scope="*",
                    actor="admin",
                )

        # No se borró ninguna fila
        assert repo._eliminados_hasta is None  # (b)


# ---------------------------------------------------------------------------
# Tests (c): purga correcta → evento AUDITORIA_PURGADA con toda la info
# ---------------------------------------------------------------------------


class TestPurgaCorrecta:
    def test_purga_correcta_emite_evento_auditoria_purgada(self, tmp_path: Path):
        """(c) Purga correcta → evento AUDITORIA_PURGADA con ruta, hash, rango y filas."""
        cambios = [_hacer_cambio(i) for i in range(1, 4)]  # ids 1, 2, 3
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        resultado = svc.archivar_y_purgar(
            tabla="audit_log",
            hasta=datetime(2026, 12, 31),
            scope="*",
            actor="admin",
            actor_id=1,
        )

        # Debe haber un evento de tipo AUDITORIA_PURGADA
        assert len(repo._eventos) == 1  # (c)
        evento = repo._eventos[0]
        assert evento.tipo_evento == TipoEventoSesion.AUDITORIA_PURGADA
        assert evento.usuario == "admin"

        # El evento debe contener ruta, hash, rango y número de filas
        detalles = evento.detalles or ""
        assert "archivo=" in detalles or resultado.ruta_archivo in detalles
        assert "hash=" in detalles or resultado.hash_archivo in detalles
        assert "id_desde=1" in detalles
        assert "id_hasta=3" in detalles
        assert "filas=3" in detalles

    def test_purga_correcta_checkpoint_reancalado(self, tmp_path: Path):
        """(c) Tras purga correcta, el checkpoint apunta al último id purgado."""
        cambios = [_hacer_cambio(i) for i in range(1, 4)]  # ids 1, 2, 3
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        svc.archivar_y_purgar(
            tabla="audit_log",
            hasta=datetime(2026, 12, 31),
            scope="*",
            actor="admin",
        )

        # El checkpoint debe haberse guardado con el último id del tramo
        assert repo._checkpoint_guardado is not None
        tabla_cp, ultimo_id_cp, hash_cp = repo._checkpoint_guardado
        assert tabla_cp == "audit_log"
        assert ultimo_id_cp == 3  # id_hasta del tramo
        assert hash_cp == "hash_3"  # hash_de_fila para id=3

    def test_purga_correcta_retorna_dto_completo(self, tmp_path: Path):
        """(c) ResultadoArchivadoDTO contiene todos los campos requeridos."""
        cambios = [_hacer_cambio(i) for i in range(1, 3)]  # ids 1, 2
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        resultado = svc.archivar_y_purgar(
            tabla="audit_log",
            hasta=datetime(2026, 12, 31),
            scope="*",
            actor="admin",
        )

        assert resultado.tabla == "audit_log"
        assert resultado.id_desde == 1
        assert resultado.id_hasta == 2
        assert resultado.filas_eliminadas == 2
        assert resultado.ruta_archivo != ""
        assert resultado.hash_archivo != ""
        assert isinstance(resultado.verificacion_previa_ok, bool)

    def test_purga_elimina_filas_en_el_repo(self, tmp_path: Path):
        """(c) La purga llama a eliminar_hasta con el id correcto."""
        cambios = [_hacer_cambio(i) for i in range(1, 4)]
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        svc.archivar_y_purgar(
            tabla="audit_log",
            hasta=datetime(2026, 12, 31),
            scope="*",
            actor="admin",
        )

        # Se llamó a eliminar_hasta con el id_hasta del tramo
        assert repo._eliminados_hasta == 3

    def test_purga_tramo_vacio_lanza_regla_negocio(self, tmp_path: Path):
        """Si no hay filas anteriores a la fecha, se lanza ReglaDeNegocioError sin borrar nada."""
        repo = _FakeRepo(cambios=[])  # sin datos
        svc = AuditoriaRetencionService(repo=repo, archivo_dir=tmp_path)

        with pytest.raises(ReglaDeNegocioError):
            svc.archivar_y_purgar(
                tabla="audit_log",
                hasta=datetime(2026, 12, 31),
                scope="*",
                actor="admin",
            )

        assert repo._eliminados_hasta is None  # nada borrado
