"""
Test estructural (obs_06 — T17): análisis por AST de src/interface/.

Verifica que ningún archivo de la capa de interfaz instancie `EventoSesion`
directamente, SALVO `src/interface/context/eventos_sesion.py`.

Fundamento: el patrón de llamada inline es invisible a grep cuando el
constructor se parte en varias líneas — lección de check_design.py ciego
a multilínea. El análisis AST opera sobre sentencias lógicas completas
y no puede ser engañado por saltos de línea.

Regla (R6): toda construcción de EventoSesion desde la interfaz DEBE pasar
por `construir_evento()` de `eventos_sesion.py`.
Los emisores de la capa de servicios (solo_lectura, contexto_tenant) quedan
exentos porque NO pueden importar interfaz — los tests de servicios los cubren.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# Raíz del proyecto: sube desde tests/unit/interface/ hasta el raíz.
_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
_INTERFACE_DIR = _ROOT / "src" / "interface"

# Único archivo autorizado a construir EventoSesion directamente.
_ARCHIVO_AUTORIZADO = _ROOT / "src" / "interface" / "context" / "eventos_sesion.py"

# Nombre del constructor cuya aparición se vigila.
_CLASE_VIGILADA = "EventoSesion"


# ---------------------------------------------------------------------------
# Lógica de análisis
# ---------------------------------------------------------------------------

def _buscar_llamadas_evento_sesion(ruta: Path) -> list[int]:
    """
    Devuelve las líneas donde aparece una llamada `EventoSesion(...)` en `ruta`.

    Analiza el AST completo del archivo para detectar tanto llamadas directas
    (EventoSesion(...)) como atributo-llamadas (módulo.EventoSesion(...)).
    Ignora importaciones (solo queremos las instanciaciones).
    """
    try:
        source = ruta.read_text(encoding="utf-8")
    except Exception:
        return []

    try:
        tree = ast.parse(source, filename=str(ruta))
    except SyntaxError:
        return []

    lineas: list[int] = []

    for nodo in ast.walk(tree):
        if not isinstance(nodo, ast.Call):
            continue
        func = nodo.func
        # Caso simple: EventoSesion(...)
        if (isinstance(func, ast.Name) and func.id == _CLASE_VIGILADA) or (isinstance(func, ast.Attribute) and func.attr == _CLASE_VIGILADA):
            lineas.append(nodo.lineno)

    return lineas


def _recolectar_archivos_py(directorio: Path) -> list[Path]:
    """Lista recursiva de archivos .py en `directorio`."""
    return sorted(directorio.rglob("*.py"))


# ---------------------------------------------------------------------------
# Test principal
# ---------------------------------------------------------------------------

def test_evento_sesion_solo_en_archivo_autorizado():
    """
    Falla si algún archivo de src/interface/ instancia EventoSesion(...)
    fuera del archivo autorizado (src/interface/context/eventos_sesion.py).

    Los servicios (solo_lectura, contexto_tenant) no pertenecen a src/interface/
    y quedan fuera del scope de esta regla.
    """
    archivos = _recolectar_archivos_py(_INTERFACE_DIR)
    violaciones: list[str] = []

    for archivo in archivos:
        if archivo.resolve() == _ARCHIVO_AUTORIZADO.resolve():
            # El archivo autorizado puede (y debe) instanciar EventoSesion.
            continue

        lineas = _buscar_llamadas_evento_sesion(archivo)
        for linea in lineas:
            relativa = archivo.relative_to(_ROOT)
            violaciones.append(f"  {relativa}:{linea}")

    if violaciones:
        mensaje = (
            f"Se encontraron {len(violaciones)} instanciación(es) directa(s) de "
            f"`{_CLASE_VIGILADA}` fuera del archivo autorizado.\n\n"
            "Archivo autorizado:\n"
            f"  src/interface/context/eventos_sesion.py\n\n"
            "Violaciones:\n"
            + "\n".join(violaciones)
            + "\n\n"
            "Solución: usa `construir_evento()` de "
            "`src.interface.context.eventos_sesion` en vez de instanciar "
            f"`{_CLASE_VIGILADA}` directamente."
        )
        # Imprimir con sys.stdout para máxima visibilidad
        sys.stdout.write(f"\n{mensaje}\n")
        raise AssertionError(mensaje)
