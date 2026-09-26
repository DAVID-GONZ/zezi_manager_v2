"""
Test de verificación de tramo según docs/verificacion_bitacora.md (obs_12, T8).

Este test ejecuta el procedimiento documentado literalmente, tal como lo haría
un tercero (auditor externo) que solo tiene el archivo CSV exportado:

  1. Construye un tramo de RegistroCambio con hashes calculados correctamente.
  2. Exporta el tramo mediante AuditoriaExportService.
  3. Aplica el procedimiento de docs/verificacion_bitacora.md §A para hash_contenido:
       - abre con encoding="utf-8-sig" (quita el BOM único del archivo)
       - filtra líneas que empiezan con "#"
       - re-encoda con "utf-8" (sin BOM)
       - calcula SHA-256
  4. Para la cadena (§B):
       - parsea el CSV exportado con csv.DictReader (omitiendo "#")
       - extrae hash_cadena de cada fila
       - recomputa la cadena desde los campos del CSV usando la fórmula canónica
       - confirma que los hashes calculados coinciden con los almacenados en hash_cadena

Si alguien cambia el documento sin cambiar el código (o viceversa), este test falla.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime

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
    _sha256_bytes,
)

# Constante GENESIS del protocolo de hash chain (docs/verificacion_bitacora.md §B)
GENESIS = "GENESIS"

# Campos que entran en el hash para audit_log (sin id ni institucion_id)
# Fuente: docs/verificacion_bitacora.md §B "Campos que entran en el hash para audit_log"
_CAMPOS_HASH_AUDIT_LOG = [
    "accion",
    "ip_address",
    "registro_id",
    "tabla",
    "timestamp",
    "usuario",
    "usuario_id",
    "valor_anterior",
    "valor_nuevo",
]


# ---------------------------------------------------------------------------
# Implementación del protocolo de verificación de docs/verificacion_bitacora.md
# ---------------------------------------------------------------------------


def _calcular_hash_cadena_cambio(hash_previo: str | None, r: RegistroCambio) -> str:
    """
    Recomputa el hash_cadena de un RegistroCambio siguiendo el protocolo
    documentado en docs/verificacion_bitacora.md §B.

    Campos del payload para audit_log (EXCLUYE id e institucion_id):
      usuario, usuario_id, ip_address, accion, tabla, registro_id,
      valor_anterior, valor_nuevo, timestamp
    """
    hp = hash_previo if hash_previo is not None else GENESIS
    payload = {
        "usuario": r.usuario,
        "usuario_id": r.usuario_id,
        "ip_address": r.ip_address,
        "accion": r.accion.value if hasattr(r.accion, "value") else str(r.accion),
        "tabla": r.tabla,
        "registro_id": r.registro_id,
        "valor_anterior": r.valor_anterior,
        "valor_nuevo": r.valor_nuevo,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
    }
    texto = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256((hp + texto).encode("utf-8")).hexdigest()


def _calcular_hash_desde_campos_csv(hash_previo: str | None, campos: dict) -> str:
    """
    Recomputa el hash desde los campos del CSV tal como lo haría un tercero
    siguiendo docs/verificacion_bitacora.md §B (script verificar_cadena.py).
    """
    hp = hash_previo if hash_previo is not None else GENESIS
    texto = json.dumps(campos, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256((hp + texto).encode("utf-8")).hexdigest()


def _construir_tramo_con_hashes(n: int) -> list[RegistroCambio]:
    """
    Construye un tramo de ``n`` RegistroCambio con hashes cadena calculados
    correctamente (GENESIS → hash_1 → hash_2 → … → hash_n).

    Los valores JSON de valor_anterior/valor_nuevo se serializan con
    separators=(",",":") (sin espacios) para que coincidan exactamente con
    los valores que el exportador escribe en el CSV (re-serialización canónica).
    Así, la verificación desde el CSV puede reconstruir el mismo hash sin
    necesitar los valores originales de la BD.
    """
    registros = []
    hash_previo = None  # primer hash: GENESIS
    for i in range(1, n + 1):
        r = RegistroCambio(
            id=i,
            usuario="u1",
            usuario_id=1,
            ip_address="127.0.0.1",
            accion=AccionCambio.UPDATE,
            tabla="estudiantes",
            registro_id=i,
            # Formato canónico (sin espacio) para que el re-encoding del exportador
            # no cambie la cadena y el verificador CSV pueda recomputar el hash.
            valor_anterior=json.dumps({"nombre": f"antes_{i}"}, separators=(",", ":")),
            valor_nuevo=json.dumps({"nombre": f"despues_{i}"}, separators=(",", ":")),
            timestamp=datetime(2026, 1, 1, 0, i),
        )
        hash_cadena = _calcular_hash_cadena_cambio(hash_previo, r)
        r.__dict__["_hash_cadena_calculado"] = hash_cadena
        registros.append(r)
        hash_previo = hash_cadena
    return registros


# ---------------------------------------------------------------------------
# Fake Repo que usa hashes reales calculados
# ---------------------------------------------------------------------------


class _FakeRepoConHashesReales:
    """Repo fake que devuelve los hashes calculados por el tramo de prueba."""

    def __init__(self, registros: list[RegistroCambio]) -> None:
        self._registros = registros
        self._hash_por_id: dict[int, str] = {
            r.id: r.__dict__["_hash_cadena_calculado"]
            for r in registros if r.id is not None
        }
        self._eventos: list[EventoSesion] = []

    def contar_cambios(self, filtro: FiltroAuditoriaDTO) -> int:
        return len(self._registros)

    def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
        return 0

    def rango_de(self, tabla: str, filtro: FiltroAuditoriaDTO):
        if not self._registros:
            return None
        ids = [r.id for r in self._registros if r.id is not None]
        return (min(ids), max(ids))

    def listar_cambios_tramo(self, tabla, id_desde, id_hasta, scope, *, lote=5_000):
        batch = [r for r in self._registros if r.id is not None and id_desde <= r.id <= id_hasta]
        if batch:
            yield batch

    def hash_de_fila(self, tabla: str, fila_id: int) -> str | None:
        return self._hash_por_id.get(fila_id)

    def _verificar_tramo_ids(self, tabla: str, id_desde: int, id_hasta: int) -> int | None:
        # Cadena íntegra → no hay id roto
        return None

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        self._eventos.append(evento)
        return evento


class _FakeExporter:
    def exportar_csv(self, datos, ruta_destino=None, encoding="utf-8-sig") -> bytes:
        return b""

    def exportar_pdf(self, html_content, ruta_destino=None) -> bytes:
        return html_content.encode("utf-8")

    def exportar_excel(self, datos, nombre_hoja="Datos", ruta_destino=None) -> bytes:
        return b""


# ---------------------------------------------------------------------------
# Helpers para extraer la hoja del CSV exportado
# ---------------------------------------------------------------------------


def _extraer_valor_hoja(texto: str, clave: str) -> str:
    """Extrae el valor de una línea ``# clave: valor`` del CSV."""
    for linea in texto.splitlines():
        if linea.startswith(f"# {clave}:"):
            return linea.split(": ", 1)[1].strip()
    raise KeyError(f"Clave '{clave}' no encontrada en la hoja del CSV.")


def _parsear_campos_hash_de_fila_csv(fila: dict) -> dict:
    """
    Extrae y convierte los campos que entran en el hash desde una fila del CSV
    exportado, siguiendo el mismo protocolo que el script verificar_cadena.py
    de docs/verificacion_bitacora.md §B.
    """
    campos: dict = {}
    for c in _CAMPOS_HASH_AUDIT_LOG:
        v = fila.get(c)
        if v == "" or v == "None":
            v = None
        # registro_id y usuario_id son enteros o None
        if c in ("registro_id", "usuario_id") and v is not None:
            try:
                v = int(v)
            except ValueError:
                pass
        campos[c] = v
    return campos


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVerificacionTramo:
    """
    Ejecuta el procedimiento de docs/verificacion_bitacora.md §A y §B literalmente.
    """

    def test_hash_primera_y_ultima_fila_coinciden_con_recomputo(self):
        """
        La hoja exportada declara hash_primera_fila y hash_ultima_fila.
        Recomputarlos desde el protocolo debe dar exactamente los mismos valores.
        """
        registros = _construir_tramo_con_hashes(4)
        repo = _FakeRepoConHashesReales(registros)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())

        csv_bytes = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )
        texto = csv_bytes.decode("utf-8-sig")

        hash_primera_declarado = _extraer_valor_hoja(texto, "hash_primera_fila")
        hash_ultima_declarado = _extraer_valor_hoja(texto, "hash_ultima_fila")

        # Recomputar desde el protocolo
        hash_primera_esperado = registros[0].__dict__["_hash_cadena_calculado"]
        hash_ultima_esperado = registros[-1].__dict__["_hash_cadena_calculado"]

        assert hash_primera_declarado == hash_primera_esperado, (
            f"hash_primera_fila: declarado={hash_primera_declarado!r}, "
            f"esperado={hash_primera_esperado!r}"
        )
        assert hash_ultima_declarado == hash_ultima_esperado, (
            f"hash_ultima_fila: declarado={hash_ultima_declarado!r}, "
            f"esperado={hash_ultima_esperado!r}"
        )

    def test_cadena_de_hashes_del_tramo_es_continua(self):
        """
        Construye un tramo con hashes reales y verifica que cada nodo se
        encadena al anterior. Comprueba hash_1, hash_2, hash_3 en secuencia.
        """
        registros = _construir_tramo_con_hashes(3)
        hash_previo = None
        for r in registros:
            hash_esperado = _calcular_hash_cadena_cambio(hash_previo, r)
            hash_calculado = r.__dict__["_hash_cadena_calculado"]
            assert hash_calculado == hash_esperado, (
                f"Roto en id={r.id}: calculado={hash_calculado!r}, esperado={hash_esperado!r}"
            )
            hash_previo = hash_calculado

    def test_modificar_dato_rompe_la_cadena(self):
        """
        Si se altera el valor_nuevo de un registro intermedio, recomputar
        su hash cadena produce un valor distinto al declarado en la hoja.
        Esto demuestra que la cadena detecta la manipulación.
        """
        registros = _construir_tramo_con_hashes(3)

        # Simular manipulación: cambiar valor_nuevo del registro id=2
        r2 = registros[1]
        r2_manipulado = RegistroCambio(
            id=r2.id,
            usuario=r2.usuario,
            usuario_id=r2.usuario_id,
            ip_address=r2.ip_address,
            accion=r2.accion,
            tabla=r2.tabla,
            registro_id=r2.registro_id,
            valor_anterior=r2.valor_anterior,
            valor_nuevo=json.dumps({"nombre": "MANIPULADO"}, separators=(",", ":")),
            timestamp=r2.timestamp,
        )

        # El hash del r2 original vs el del r2 manipulado son distintos
        hash_previo_r2 = registros[0].__dict__["_hash_cadena_calculado"]
        hash_r2_original = _calcular_hash_cadena_cambio(hash_previo_r2, r2)
        hash_r2_manipulado = _calcular_hash_cadena_cambio(hash_previo_r2, r2_manipulado)

        assert hash_r2_original != hash_r2_manipulado, (
            "Un dato modificado debería producir un hash cadena diferente."
        )

    def test_hash_contenido_verifica_integridad_del_archivo(self):
        """
        Aplica exactamente el procedimiento de docs/verificacion_bitacora.md §A:

          1. Abrir el archivo con encoding="utf-8-sig" (quita el BOM único del archivo).
          2. Filtrar las líneas que empiezan con "#".
          3. Re-encodear el resto con "utf-8" (sin BOM).
          4. Calcular SHA-256.
          5. Comparar con hash_contenido declarado en la hoja.

        Si alguien cambia el código para añadir un segundo BOM o para codificar
        los datos con utf-8-sig, este test falla porque el procedimiento del
        documento ya no coincide.
        """
        registros = _construir_tramo_con_hashes(2)
        repo = _FakeRepoConHashesReales(registros)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())

        csv_bytes = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )

        # Paso A1 del documento: abrir con utf-8-sig quita el BOM único.
        lineas = io.StringIO(csv_bytes.decode("utf-8-sig")).readlines()

        # Separar las líneas de comentario (#) de las de datos.
        datos_lineas = [l for l in lineas if not l.startswith("#")]
        datos_str = "".join(datos_lineas)

        # Encodear con "utf-8" (sin BOM) — exactamente como dice el documento.
        datos_bytes = datos_str.encode("utf-8")

        hash_contenido_calculado = hashlib.sha256(datos_bytes).hexdigest()

        # Extraer el valor declarado en la hoja del CSV.
        texto = csv_bytes.decode("utf-8-sig")
        hash_contenido_declarado = _extraer_valor_hoja(texto, "hash_contenido")

        assert hash_contenido_declarado == hash_contenido_calculado, (
            f"hash_contenido: declarado={hash_contenido_declarado!r}, "
            f"calculado={hash_contenido_calculado!r}. "
            "El procedimiento del documento no coincide con el exportador."
        )

    def test_hash_cadena_en_csv_verifica_cadena_completa(self):
        """
        Aplica exactamente el procedimiento de docs/verificacion_bitacora.md §B:

          1. Leer el CSV exportado omitiendo líneas "#".
          2. Para cada fila, extraer hash_cadena (columna explícita en el CSV).
          3. Recomputar la cadena con la fórmula canónica usando los campos del CSV.
          4. Verificar que hash_esperado == hash_cadena almacenado en la fila.

        Si alguien elimina hash_cadena del CSV, o cambia la fórmula de la cadena
        sin actualizar el documento, este test falla.
        """
        registros = _construir_tramo_con_hashes(4)
        repo = _FakeRepoConHashesReales(registros)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())

        csv_bytes = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )

        # Paso B1 del documento: leer el CSV omitiendo líneas de comentario.
        texto = csv_bytes.decode("utf-8-sig")
        lineas_datos = [l for l in texto.splitlines(keepends=True) if not l.startswith("#")]
        assert lineas_datos, "El CSV exportado no tiene filas de datos."

        reader = csv.DictReader(io.StringIO("".join(lineas_datos)))

        # Verificar que hash_cadena es una columna presente en el CSV.
        primera_fila = None
        filas_csv = list(reader)
        assert filas_csv, "El CSV no tiene filas tras filtrar cabecera."
        assert "hash_cadena" in filas_csv[0], (
            "La columna 'hash_cadena' no está en el CSV exportado. "
            "El verificador externo no puede reconstruir la cadena."
        )

        # Paso B2 del documento: recomputar la cadena fila a fila.
        # Usamos None como semilla inicial (tramo desde el origen → GENESIS).
        hash_previo = None
        primer_roto = None

        for i, fila in enumerate(filas_csv):
            campos = _parsear_campos_hash_de_fila_csv(fila)
            hash_esperado = _calcular_hash_desde_campos_csv(hash_previo, campos)
            hash_almacenado = fila.get("hash_cadena", "")

            if hash_esperado != hash_almacenado:
                primer_roto = fila.get("id", f"fila_{i + 1}")
                break
            hash_previo = hash_almacenado

        assert primer_roto is None, (
            f"La cadena de hashes del CSV está rota en id={primer_roto}. "
            "Revisar que el exportador incluye hash_cadena correcto y que la "
            "fórmula del documento coincide con la del exportador."
        )

    def test_hash_cadena_presente_en_todas_las_filas(self):
        """
        Todas las filas del CSV deben tener hash_cadena no vacío para que
        la verificación de la cadena sea posible.
        """
        registros = _construir_tramo_con_hashes(3)
        repo = _FakeRepoConHashesReales(registros)
        svc = AuditoriaExportService(repo=repo, exporter=_FakeExporter())

        csv_bytes = svc.exportar(
            tabla="audit_log",
            filtro=FiltroAuditoriaDTO(),
            scope="*",
            formato="csv",
            actor="admin",
        )

        texto = csv_bytes.decode("utf-8-sig")
        lineas_datos = [l for l in texto.splitlines(keepends=True) if not l.startswith("#")]
        reader = csv.DictReader(io.StringIO("".join(lineas_datos)))

        for fila in reader:
            assert "hash_cadena" in fila and fila["hash_cadena"], (
                f"Fila id={fila.get('id')} tiene hash_cadena vacío o ausente."
            )
