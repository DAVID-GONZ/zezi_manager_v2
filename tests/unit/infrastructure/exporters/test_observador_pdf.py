"""Tests del generador de PDF del observador del estudiante."""
from __future__ import annotations

from datetime import datetime

import pytest

from src.infrastructure.exporters.observador_pdf import generar_observador_pdf


def _datos_minimos() -> dict:
    return {
        "estudiante": {
            "id": 1,
            "nombre": "Ruiz Ana",
            "apellido": "Ruiz",
            "primer_nombre": "Ana",
            "documento": "1001234567",
            "grupo": "9A",
            "grado": "9°",
        },
        "institucion": {
            "nombre": "IE ZECI",
            "DANE": "111001000001",
            "rector": "Carlos García",
        },
        "anio": "2026",
        "periodo": "Periodo 1",
        "entradas": [],
        "resumen": {
            "fortalezas": 0,
            "dificultades": 0,
            "compromisos": 0,
            "citaciones": 0,
            "descargos": 0,
            "num_observaciones": 0,
            "notas_por_periodo": {},
        },
    }


class TestGenerarObservadorPdf:
    def test_retorna_bytes_no_vacios(self):
        datos = _datos_minimos()
        resultado = generar_observador_pdf(datos)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 100

    def test_pdf_valido_empieza_con_magic(self):
        datos = _datos_minimos()
        resultado = generar_observador_pdf(datos)
        assert resultado[:4] == b"%PDF"

    def test_pdf_con_entradas_narrativas(self):
        datos = _datos_minimos()
        datos["entradas"] = [
            {
                "fecha": datetime(2026, 3, 15, 10, 0),
                "tipo": "registro",
                "subtipo": "dificultad",
                "tipo_situacion": "Tipo II",
                "descripcion": "Pelea con compañero en el patio de recreo.",
                "medida": "Diálogo con acudiente",
                "responsable": "Docente Juan Pérez",
                "categoria": None,
                "seguimiento_entries": [
                    {
                        "fecha": datetime(2026, 3, 16, 8, 0),
                        "texto": "Se realizó reunión con acudiente. Acuerdo firmado.",
                        "responsable": "Coordinador",
                    }
                ],
            },
            {
                "fecha": datetime(2026, 4, 1, 9, 30),
                "tipo": "observacion",
                "subtipo": "publica",
                "tipo_situacion": None,
                "descripcion": "Muestra avances significativos en convivencia.",
                "medida": None,
                "responsable": "Docente María López",
                "categoria": "Convivencia",
                "seguimiento_entries": [],
            },
        ]
        datos["resumen"] = {
            "fortalezas": 1,
            "dificultades": 1,
            "compromisos": 0,
            "citaciones": 0,
            "descargos": 0,
            "num_observaciones": 1,
            "notas_por_periodo": {"Periodo 1": 75.0},
        }
        resultado = generar_observador_pdf(datos)
        assert isinstance(resultado, bytes)
        assert resultado[:4] == b"%PDF"
        # El PDF debe tener un tamaño razonable (tiene contenido)
        assert len(resultado) > 1000

    def test_pdf_sin_periodo_ok(self):
        datos = _datos_minimos()
        datos["periodo"] = None
        resultado = generar_observador_pdf(datos)
        assert resultado[:4] == b"%PDF"

    def test_pdf_campos_vacios_no_lanza(self):
        datos = {
            "estudiante": {},
            "institucion": {},
            "anio": "",
            "periodo": None,
            "entradas": [],
            "resumen": {},
        }
        resultado = generar_observador_pdf(datos)
        assert resultado[:4] == b"%PDF"
