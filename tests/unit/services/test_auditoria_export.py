"""
Tests del servicio de exportación de la bitácora (obs_12, T6).

Cubre los requisitos R1-R7:
  - R1/R2: la hoja de verificación contiene hash_primera_fila, hash_ultima_fila
           y hash_contenido.
  - R4: con la cadena rota, la exportación se produce igualmente e integridad_ok=False.
  - R6: un campo sensible no aparece en el CSV exportado.
  - R7: superar el tope lanza ReglaDeNegocioError con código AUDITORIA_EXPORT_TOPE.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

import pytest

from src.domain.exceptions import ReglaDeNegocioError
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    SeveridadEvento,
    TipoEventoSesion,
)
from src.services.auditoria_export_service import (
    AuditoriaExportService,
    _CODIGO_TOPE,
    _sha256_bytes,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeExporter:
    """IExporterService mínimo para tests de exportación."""

    def exportar_csv(self, datos, ruta_destino=None, encoding="utf-8-sig") -> bytes:
        if not datos:
            return b""
        import io
        buf = io.StringIO()
        if datos:
            cols = list(datos[0].keys())
            buf.write(",".join(cols) + "\r\n")
            for fila in datos:
                buf.write(",".join(str(fila.get(c, "")) for c in cols) + "\r\n")
        return buf.getvalue().encode("utf-8-sig")

    def exportar_pdf(self, html_content, ruta_destino=None) -> bytes:
        return html_content.encode("utf-8")

    def exportar_excel(self, datos, nombre_hoja="Datos", ruta_destino=None) -> bytes:
        return b""


def _hacer_cambio(
    id_: int,
    tabla: str = "estudiantes",
    usuario: str = "u1",
    valor_anterior: dict | None = None,
    valor_nuevo: dict | None = None,
    hash_cadena: str | None = None,
) -> RegistroCambio:
    r = RegistroCambio(
        id=id_,
        usuario=usuario,
        usuario_id=1,
        accion=AccionCambio.UPDATE,
        tabla=tabla,
        registro_id=id_,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        timestamp=datetime(2026, 1, 1, 10, id_),
    )
    r.__dict__["_hash_cadena"] = hash_cadena or f"hash_{id_}"
    return r


class _FakeRepo:
    """Repo de auditoría mínimo para tests del exportador."""

    def __init__(
        self,
        cambios: list[RegistroCambio] | None = None,
        id_roto: int | None = None,
    ):
        self._cambios = cambios or []
        self._id_roto = id_roto
        self._eventos_registrados: list[EventoSesion] = []

    # Métodos requeridos por AuditoriaExportService

    def contar_cambios(self, filtro: FiltroAuditoriaDTO) -> int:
        return len(self._cambios)

    def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
        return 0

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

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        self._eventos_registrados.append(evento)
        return evento


# ---------------------------------------------------------------------------
# Tests R2: la hoja incluye hash_primera_fila, hash_ultima_fila y hash_contenido
# ---------------------------------------------------------------------------


class TestHojaVerificacion:
    def _svc(self, cambios, id_roto=None, max_filas=50_000):
        repo = _FakeRepo(cambios=cambios, id_roto=id_roto)
        return AuditoriaExportService(repo=repo, exporter=_FakeExporter(), max_filas=max_filas), repo

    def test_hoja_contiene_hash_primera_ultima_fila(self):
        """R2: la hoja lleva hash_cadena del primer y último registro."""
        cambios = [_hacer_cambio(1), _hacer_cambio(2)]
        svc, repo = self._svc(cambios)
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = resultado.decode("utf-8-sig")
        # Las líneas de cabecera deben incluir los hashes extremos
        assert "hash_primera_fila: hash_1" in texto  # hash del id=1
        assert "hash_ultima_fila: hash_2" in texto     # hash del id=2

    def test_hoja_contiene_hash_contenido(self):
        """R2: la hoja lleva SHA-256 de los datos (sin la hoja).

        El archivo CSV tiene un único BOM al inicio (cabecera de verificación
        en utf-8-sig) y los datos en utf-8 sin BOM adicional. El procedimiento
        de verificación (docs/verificacion_bitacora.md §A) es:
          1. Abrir con encoding="utf-8-sig" (quita el único BOM).
          2. Filtrar líneas que empiezan con "#".
          3. Re-encodear el resto con "utf-8" (sin BOM).
          4. Calcular SHA-256.
        """
        import io as _io
        import hashlib as _hashlib
        cambios = [_hacer_cambio(1)]
        svc, repo = self._svc(cambios)
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = resultado.decode("utf-8-sig")
        # Extraer el hash_contenido de la cabecera
        hash_line = next(l for l in texto.splitlines() if "hash_contenido:" in l)
        hash_declarado = hash_line.split(": ", 1)[1].strip()

        # Procedimiento del documento §A: filtrar # y encodear con utf-8.
        lineas = _io.StringIO(texto).readlines()
        datos_lineas = [l for l in lineas if not l.startswith("#")]
        datos_bytes = "".join(datos_lineas).encode("utf-8")
        hash_calculado = _hashlib.sha256(datos_bytes).hexdigest()

        assert hash_declarado == hash_calculado  # R2


# ---------------------------------------------------------------------------
# Tests R4: con cadena rota la exportación se produce e integridad_ok=False
# ---------------------------------------------------------------------------


class TestIntegridadRota:
    def test_exportacion_con_cadena_rota(self):
        """R4: exportar aunque la cadena esté rota; integridad_ok=False en hoja."""
        cambios = [_hacer_cambio(1), _hacer_cambio(2)]
        repo = _FakeRepo(cambios=cambios, id_roto=2)  # cadena rota en id=2
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = resultado.decode("utf-8-sig")
        assert "integridad_ok: False" in texto  # R4: la hoja dice que falló
        assert "id_roto: 2" in texto             # señala el id roto

    def test_exportacion_con_cadena_sana_integridad_ok(self):
        """Cuando la cadena está íntegra, integridad_ok=True en la hoja."""
        cambios = [_hacer_cambio(1), _hacer_cambio(2)]
        repo = _FakeRepo(cambios=cambios, id_roto=None)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = resultado.decode("utf-8-sig")
        assert "integridad_ok: True" in texto


# ---------------------------------------------------------------------------
# Tests R6: campos sensibles no aparecen en el CSV
# ---------------------------------------------------------------------------


class TestCamposSensibles:
    def test_password_hash_no_en_csv(self):
        """R6: 'password_hash' se redacta en la exportación."""
        cambio = _hacer_cambio(
            1,
            valor_nuevo={"nombre": "Ana", "password_hash": "secreto_bcrypt"},
        )
        repo = _FakeRepo(cambios=[cambio])
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = resultado.decode("utf-8-sig")
        assert "secreto_bcrypt" not in texto  # R6: el valor sensible no aparece
        assert "•••" in texto or "password_hash" in texto  # el campo aparece redactado

    def test_campo_no_sensible_si_aparece(self):
        """Los campos no sensibles sí aparecen en el CSV."""
        cambio = _hacer_cambio(1, valor_nuevo={"nombre": "Ana"})
        repo = _FakeRepo(cambios=[cambio])
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = resultado.decode("utf-8-sig")
        assert "Ana" in texto  # el valor no sensible aparece


# ---------------------------------------------------------------------------
# Tests R7: tope de filas
# ---------------------------------------------------------------------------


class TestTopeDeFila:
    def test_superar_tope_lanza_error_con_codigo_estable(self):
        """R7: superar el tope lanza ReglaDeNegocioError con código AUDITORIA_EXPORT_TOPE."""
        cambios = [_hacer_cambio(i) for i in range(1, 11)]  # 10 cambios
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter(), max_filas=5)
        with pytest.raises(ReglaDeNegocioError) as exc_info:
            svc.exportar(
                tabla="audit_log",
                filtro=FiltroAuditoriaDTO(),
                scope="*",
                formato="csv",
                actor="admin",
            )
        assert str(exc_info.value.codigo) == _CODIGO_TOPE  # R7

    def test_dentro_del_tope_no_lanza_error(self):
        """Con el filtro dentro del tope, la exportación procede normalmente."""
        cambios = [_hacer_cambio(i) for i in range(1, 4)]  # 3 cambios
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter(), max_filas=10)
        resultado = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        assert len(resultado) > 0


# ---------------------------------------------------------------------------
# Tests R5: el evento AUDITORIA_EXPORTADA queda registrado
# ---------------------------------------------------------------------------


class TestEventoExportacion:
    def test_exportacion_emite_evento_auditoria_exportada(self):
        """R5: exportar registra un evento AUDITORIA_EXPORTADA en la bitácora."""
        cambios = [_hacer_cambio(1)]
        repo = _FakeRepo(cambios=cambios)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())
        svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="director.test",
            actor_id=99,
        )
        assert len(repo._eventos_registrados) == 1  # R5
        evento = repo._eventos_registrados[0]
        assert evento.tipo_evento == TipoEventoSesion.AUDITORIA_EXPORTADA
        assert evento.usuario == "director.test"
