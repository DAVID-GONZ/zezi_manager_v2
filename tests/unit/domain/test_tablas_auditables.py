"""
Tests del catálogo de tablas auditables (obs_09 T1/T2).

Regla: toda clave de ETIQUETAS_TABLA debe existir como tabla física en metadata.
El test protege contra entradas muertas, no exige exhaustividad.
Una tabla desconocida devuelve su nombre físico (fallback R5).
"""
from __future__ import annotations

from src.domain.tablas_auditables import ETIQUETAS_TABLA, etiqueta_de_tabla
from src.infrastructure.db.schema import metadata


def _tablas_en_schema() -> set[str]:
    """Retorna el conjunto de nombres de tabla declarados en el MetaData."""
    return set(metadata.tables.keys())


class TestCatalogoCoberturaEsquema:
    """Toda clave del catálogo debe existir como tabla real en schema.py."""

    def test_todas_las_claves_son_tablas_reales(self):
        tablas_schema = _tablas_en_schema()
        claves_sin_tabla = [k for k in ETIQUETAS_TABLA if k not in tablas_schema]
        assert claves_sin_tabla == [], (
            f"Las siguientes claves del catálogo no existen en metadata: {claves_sin_tabla}"
        )

    def test_catalogo_no_vacio(self):
        assert len(ETIQUETAS_TABLA) > 0, "El catálogo está vacío"


class TestEtiquetaDeTabla:
    def test_tabla_conocida_devuelve_etiqueta(self):
        """Una tabla catalogada devuelve su etiqueta legible."""
        # usuarios siempre estará en el catálogo
        assert etiqueta_de_tabla("usuarios") == "Cuentas de usuario"

    def test_tabla_desconocida_devuelve_nombre_fisico(self):
        """Una tabla sin entrada en el catálogo devuelve su nombre físico (R5)."""
        nombre_raro = "tabla_que_no_existe_jamas"
        assert etiqueta_de_tabla(nombre_raro) == nombre_raro

    def test_etiqueta_difiere_del_nombre_fisico(self):
        """Las entradas del catálogo producen etiquetas distintas al nombre físico."""
        for tabla, etiqueta in ETIQUETAS_TABLA.items():
            assert etiqueta != tabla, (
                f"La etiqueta '{etiqueta}' de '{tabla}' es igual al nombre físico "
                "(no tiene utilidad semántica)"
            )
