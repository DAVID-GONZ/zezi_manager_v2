"""
Tests de la política de encadenamiento por hash (src/domain/policies/audit_chain.py).

Cubren:
  - determinismo y canonicidad de calcular_hash (orden de claves irrelevante).
  - encadenamiento real (GENESIS para el primero, hash previo para el resto).
  - detección del primer eslabón roto ante edición/inserción/borrado intermedio.
"""
from __future__ import annotations

from src.domain.policies.audit_chain import (
    GENESIS,
    calcular_hash,
    primer_eslabon_roto,
)


def _construir_cadena(lista_campos: list[dict]) -> list[tuple[dict, str]]:
    """Helper: encadena los campos dados produciendo (campos, hash) íntegros."""
    secuencia: list[tuple[dict, str]] = []
    hash_previo: str | None = None
    for campos in lista_campos:
        h = calcular_hash(hash_previo, campos)
        secuencia.append((campos, h))
        hash_previo = h
    return secuencia


class TestCalcularHash:

    def test_es_determinista(self):
        campos = {"usuario": "ana", "tipo": "LOGIN", "ip": "1.2.3.4"}
        assert calcular_hash(None, campos) == calcular_hash(None, campos)

    def test_hex_sha256_de_64_chars(self):
        h = calcular_hash(None, {"a": 1})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_orden_de_claves_irrelevante(self):
        h1 = calcular_hash("prev", {"a": 1, "b": 2})
        h2 = calcular_hash("prev", {"b": 2, "a": 1})
        assert h1 == h2

    def test_none_y_genesis_equivalen(self):
        campos = {"x": 1}
        assert calcular_hash(None, campos) == calcular_hash(GENESIS, campos)

    def test_cadena_vacia_distinta_de_previo(self):
        campos = {"x": 1}
        assert calcular_hash(None, campos) != calcular_hash("otro", campos)

    def test_cambiar_un_campo_cambia_el_hash(self):
        assert calcular_hash("p", {"v": 1}) != calcular_hash("p", {"v": 2})


class TestPrimerEslabonRoto:

    def test_cadena_vacia_es_integra(self):
        assert primer_eslabon_roto([]) is None

    def test_cadena_integra_devuelve_none(self):
        secuencia = _construir_cadena([
            {"i": 1, "d": "a"},
            {"i": 2, "d": "b"},
            {"i": 3, "d": "c"},
        ])
        assert primer_eslabon_roto(secuencia) is None

    def test_edicion_intermedia_se_detecta(self):
        secuencia = _construir_cadena([
            {"i": 1, "d": "a"},
            {"i": 2, "d": "b"},
            {"i": 3, "d": "c"},
        ])
        # Manipular los campos del segundo registro sin recalcular su hash.
        campos_alterados, hash_viejo = secuencia[1]
        secuencia[1] = ({**campos_alterados, "d": "HACK"}, hash_viejo)
        assert primer_eslabon_roto(secuencia) == 1

    def test_primer_registro_alterado_se_detecta_en_indice_0(self):
        secuencia = _construir_cadena([{"i": 1}, {"i": 2}])
        campos, hash_viejo = secuencia[0]
        secuencia[0] = ({**campos, "i": 99}, hash_viejo)
        assert primer_eslabon_roto(secuencia) == 0

    def test_borrado_intermedio_rompe_la_cadena(self):
        secuencia = _construir_cadena([
            {"i": 1},
            {"i": 2},
            {"i": 3},
        ])
        # Borrar el segundo eslabón: el tercero deja de cuadrar con el primero.
        del secuencia[1]
        assert primer_eslabon_roto(secuencia) == 1

    def test_insercion_intermedia_rompe_la_cadena(self):
        secuencia = _construir_cadena([{"i": 1}, {"i": 2}])
        # Insertar un registro forjado entre ambos: su hash no encadena.
        forjado = ({"i": 999}, calcular_hash(None, {"i": 999}))
        secuencia.insert(1, forjado)
        assert primer_eslabon_roto(secuencia) == 1
