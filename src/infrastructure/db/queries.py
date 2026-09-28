"""
Funciones de consulta SQL — AVEDRA v2.0
=============================================

API de acceso a datos de bajo nivel. Usada exclusivamente por los
repositorios en `src/infrastructure/db/repositories/`.

Las páginas y los servicios nunca importan desde aquí directamente.

Funciones disponibles:
  fetch_df    → pd.DataFrame        (queries de lectura, volumen medio-alto)
  fetch_one   → dict | None         (una sola fila)
  fetch_all   → list[dict]          (múltiples filas como dicts)
  get_scalar  → Any                 (un único valor)
  execute     → bool | dict         (INSERT / UPDATE / DELETE)
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from container import Container

logger = logging.getLogger("DB.QUERIES")


# ---------------------------------------------------------------------------
# Adaptación de parámetros (T1)
# ---------------------------------------------------------------------------


def _adapt_scalar(value: object) -> object:
    """Convierte escalares numpy/pandas a tipos nativos de Python.

    SQLite no acepta np.int64, np.float32, etc. directamente.
    """
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    return value


def _adapt_params(params: tuple | list | dict | None) -> tuple | dict:
    """
    Normaliza parámetros para SQLAlchemy / DBAPI.

    - Convierte escalares numpy/pandas a tipos nativos de Python.
    - Parámetros posicionales (tuple/list) → tuple (para exec_driver_sql con ?).
    - Parámetros nominales (dict) → dict (para exec_driver_sql / text() con :nombre).
    """
    if not params:
        return ()
    if isinstance(params, dict):
        return {k: _adapt_scalar(v) for k, v in params.items()}
    if not isinstance(params, (tuple, list)):
        params = (params,)
    return tuple(_adapt_scalar(p) for p in params)


# ---------------------------------------------------------------------------
# Funciones de lectura
# ---------------------------------------------------------------------------


def fetch_df(
    query: str,
    params: tuple | list | None = None,
    return_empty_on_error: bool = True,
) -> pd.DataFrame | None:
    """
    Ejecuta un SELECT y retorna un DataFrame de pandas.

    Usar cuando:
      - El resultado necesita transformaciones con pandas (groupby, merge, etc.).
      - Se van a construir estructuras de grillas (ag-grid).
      - El volumen de filas es > 20.

    Para una sola fila usar `fetch_one`. Para pocas filas sin pandas usar `fetch_all`.

    Args:
        query:               SQL SELECT con placeholders (?).
        params:              Parámetros para los placeholders.
        return_empty_on_error: Si True, retorna DataFrame vacío en error.
                               Si False, retorna None.

    Returns:
        pd.DataFrame con los resultados, o DataFrame vacío / None si hay error.

    Example:
        >>> df = fetch_df("SELECT * FROM usuarios WHERE rol = ?", ("profesor",))
        >>> df = fetch_df("SELECT COUNT(*) as total FROM estudiantes")
    """
    params = params or ()
    try:
        with Container.engine().connect() as conn:
            result = conn.exec_driver_sql(query, _adapt_params(params))
            cols = list(result.keys())
            rows = result.fetchall()
            df = pd.DataFrame(rows, columns=cols)
            logger.debug("fetch_df: %d filas", len(df))
            return df
    except Exception as exc:
        logger.error("Error en fetch_df | query=%s | params=%s | error=%s", query, params, exc)
        return pd.DataFrame() if return_empty_on_error else None


def fetch_one(
    query: str,
    params: tuple | list | None = None,
) -> dict[str, Any] | None:
    """
    Ejecuta un SELECT y retorna la primera fila como diccionario.

    Args:
        query:  SQL SELECT (idealmente con LIMIT 1).
        params: Parámetros para los placeholders.

    Returns:
        dict con columnas como keys, o None si no hay resultado.

    Example:
        >>> usuario = fetch_one("SELECT * FROM usuarios WHERE id = ?", (1,))
        >>> if usuario:
        ...     print(usuario["nombre_completo"])
    """
    params = params or ()
    try:
        with Container.engine().connect() as conn:
            result = conn.exec_driver_sql(query, _adapt_params(params))
            row = result.mappings().first()
            if row is None:
                logger.debug("fetch_one: sin resultados")
                return None
            result_dict = dict(row)
            logger.debug("fetch_one: %d columnas", len(result_dict))
            return result_dict
    except Exception as exc:
        logger.error("Error en fetch_one | query=%s | params=%s | error=%s", query, params, exc)
        return None


def fetch_all(
    query: str,
    params: tuple | list | None = None,
) -> list[dict[str, Any]]:
    """
    Ejecuta un SELECT y retorna todas las filas como lista de diccionarios.

    Usar cuando el volumen es bajo-medio (< ~200 filas) y no se necesita pandas.
    Para volúmenes mayores o transformaciones complejas, usar `fetch_df`.

    Args:
        query:  SQL SELECT.
        params: Parámetros para los placeholders.

    Returns:
        list[dict], o lista vacía si no hay resultados o hay error.

    Example:
        >>> profesores = fetch_all("SELECT * FROM usuarios WHERE rol = ?", ("profesor",))
        >>> for p in profesores:
        ...     print(p["nombre_completo"])
    """
    params = params or ()
    try:
        with Container.engine().connect() as conn:
            result = conn.exec_driver_sql(query, _adapt_params(params))
            rows = result.mappings().all()
            if not rows:
                logger.debug("fetch_all: sin resultados")
                return []
            result_list = [dict(row) for row in rows]
            logger.debug("fetch_all: %d filas", len(result_list))
            return result_list
    except Exception as exc:
        logger.error("Error en fetch_all | query=%s | params=%s | error=%s", query, params, exc)
        return []


def get_scalar(
    query: str,
    params: tuple | list | None = None,
    default: Any = None,
) -> Any:
    """
    Ejecuta un SELECT y retorna el valor de la primera columna de la primera fila.

    Ideal para COUNT(*), MAX(), SUM(), y consultas de existencia.

    Args:
        query:   SQL SELECT que retorna exactamente una columna.
        params:  Parámetros para los placeholders.
        default: Valor si no hay resultado (default: None).

    Returns:
        El valor escalar, o `default` si no hay filas.

    Example:
        >>> total = get_scalar("SELECT COUNT(*) FROM estudiantes")
        >>> existe = get_scalar(
        ...     "SELECT id FROM estudiantes WHERE numero_documento = ?",
        ...     ("123456",), default=None
        ... ) is not None
    """
    params = params or ()
    try:
        with Container.engine().connect() as conn:
            result = conn.exec_driver_sql(query, _adapt_params(params))
            row = result.fetchone()
            if row is None:
                logger.debug("get_scalar: sin resultados, retornando default=%s", default)
                return default
            logger.debug("get_scalar: %s", row[0])
            return row[0]
    except Exception as exc:
        logger.error("Error en get_scalar | query=%s | params=%s | error=%s", query, params, exc)
        return default


# ---------------------------------------------------------------------------
# Función de escritura (T5)
# ---------------------------------------------------------------------------


def execute(
    query: str,
    params: tuple | list | dict | None = None,
    return_metadata: bool = False,
) -> bool | dict[str, Any]:
    """
    Ejecuta un INSERT, UPDATE o DELETE con commit automático.

    Args:
        query:           SQL de escritura con placeholders (? o :nombre).
        params:          Parámetros posicionales (tuple/list) o nominales (dict).
        return_metadata: Si True, retorna dict con lastrowid y rowcount.

    Returns:
        bool True si exitoso (modo por defecto).
        dict {'success': bool, 'lastrowid': int | None, 'rowcount': int}
             si return_metadata=True.

    Raises:
        Exception: Propaga cualquier error de escritura al llamador.

    Examples:
        >>> execute(
        ...     "INSERT INTO grupos (codigo, nombre) VALUES (?, ?)",
        ...     ("601", "Sexto A")
        ... )
        True

        >>> result = execute(
        ...     "INSERT INTO estudiantes (nombre, apellido) VALUES (:nombre, :apellido)",
        ...     {"nombre": "Ana", "apellido": "Garcia"},
        ...     return_metadata=True,
        ... )
        >>> nuevo_id = result["lastrowid"]
    """
    params = params or ()
    with Container.engine().connect() as conn, conn.begin():
        result = conn.exec_driver_sql(query, _adapt_params(params))
        logger.debug(
            "execute: %d fila(s) afectada(s), lastrowid=%s",
            result.rowcount,
            result.lastrowid,
        )
        if return_metadata:
            return {
                "success": True,
                "lastrowid": result.lastrowid,
                "rowcount": result.rowcount,
            }
        return True


__all__ = ["execute", "fetch_all", "fetch_df", "fetch_one", "get_scalar"]
