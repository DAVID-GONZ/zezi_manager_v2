"""
Funciones de consulta SQL — ZECI Manager v2.0
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

from .connection import get_connection, _normalize_params

logger = logging.getLogger("DB.QUERIES")


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
        with get_connection() as conn:
            df = pd.read_sql(query, conn, params=_normalize_params(params))
            logger.debug("fetch_df: %d filas", len(df))
            return df
    except Exception as exc:
        logger.error("Error en fetch_df | query=%s | params=%s | error=%s",
                     query, params, exc)
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
        with get_connection() as conn:
            row = conn.execute(query, _normalize_params(params)).fetchone()
            if row is None:
                logger.debug("fetch_one: sin resultados")
                return None
            result = dict(row)
            logger.debug("fetch_one: %d columnas", len(result))
            return result
    except Exception as exc:
        logger.error("Error en fetch_one | query=%s | params=%s | error=%s",
                     query, params, exc)
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
        with get_connection() as conn:
            rows = conn.execute(query, _normalize_params(params)).fetchall()
            if not rows:
                logger.debug("fetch_all: sin resultados")
                return []
            result = [dict(row) for row in rows]
            logger.debug("fetch_all: %d filas", len(result))
            return result
    except Exception as exc:
        logger.error("Error en fetch_all | query=%s | params=%s | error=%s",
                     query, params, exc)
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
        with get_connection() as conn:
            row = conn.execute(query, _normalize_params(params)).fetchone()
            if row is None:
                logger.debug("get_scalar: sin resultados, retornando default=%s", default)
                return default
            logger.debug("get_scalar: %s", row[0])
            return row[0]
    except Exception as exc:
        logger.error("Error en get_scalar | query=%s | params=%s | error=%s",
                     query, params, exc)
        return default


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

    Examples:
        >>> execute(
        ...     "INSERT INTO grupos (codigo, nombre) VALUES (?, ?)",
        ...     ("601", "Sexto A")
        ... )
        True

        >>> result = execute(
        ...     "INSERT INTO estudiantes (nombre, apellido) VALUES (:nombre, :apellido)",
        ...     {"nombre": "Ana", "apellido": "García"},
        ...     return_metadata=True,
        ... )
        >>> nuevo_id = result["lastrowid"]
    """
    params = params or ()
    try:
        with get_connection() as conn:
            cursor = conn.execute(query, _normalize_params(params)
                                  if not isinstance(params, dict) else params)
            conn.commit()
            logger.debug("execute: %d fila(s) afectada(s), lastrowid=%s",
                         cursor.rowcount, cursor.lastrowid)
            if return_metadata:
                return {
                    "success":   True,
                    "lastrowid": cursor.lastrowid,
                    "rowcount":  cursor.rowcount,
                }
            return True

    except Exception as exc:
        logger.error("Error en execute | query=%s | params=%s | error=%s",
                     query, params, exc)
        if return_metadata:
            return {"success": False, "lastrowid": None, "rowcount": 0}
        return False


__all__ = ["fetch_df", "fetch_one", "fetch_all", "get_scalar", "execute"]