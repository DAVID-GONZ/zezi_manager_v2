"""
src/domain/models/clock.py
==========================
Origen único del instante actual en ZECI Manager v2.0.

Provee ``hoy()`` y ``ahora()`` en la zona horaria configurada
(``config.ZONA_HORARIA``, por omisión ``"America/Bogota"``).

Ambas funciones aceptan un parámetro ``_now`` opcional que permite fijar
el instante en los tests sin parchear el módulo ``datetime``.

Zona horaria: ``zoneinfo`` de la biblioteca estándar (Python ≥ 3.9).
No añade dependencias de terceros.

Uso habitual:
    from src.domain.models.clock import ahora, hoy

    fecha = hoy()          # date en la zona configurada
    ts    = ahora()        # datetime tz-aware en la zona configurada

Uso en tests:
    import datetime
    from src.domain.models.clock import hoy

    momento = datetime.datetime(2026, 9, 9, 0, 50, tzinfo=datetime.timezone.utc)
    assert hoy(_now=momento) == datetime.date(2026, 9, 8)  # 19:50 COT
"""

from __future__ import annotations

import datetime as _dt
from zoneinfo import ZoneInfo


def _zona() -> ZoneInfo:
    """
    Resuelve la zona horaria desde ``config.ZONA_HORARIA``.

    Se importa dentro de la función para evitar importación circular y para
    que los tests puedan sobreescribir ``config.ZONA_HORARIA`` en tiempo
    de ejecución sin reiniciar el módulo.
    """
    import config as _cfg

    nombre = getattr(_cfg, "ZONA_HORARIA", "America/Bogota")
    return ZoneInfo(nombre)


def ahora(_now: _dt.datetime | None = None) -> _dt.datetime:
    """
    Retorna el instante actual con ``tzinfo`` en la zona configurada.

    Args:
        _now: Si se provee, convierte este instante a la zona configurada
              y lo retorna. Debe tener ``tzinfo``. Usar solo en tests para
              fijar el reloj sin parchear el módulo ``datetime``.

    Returns:
        ``datetime`` con ``tzinfo`` apuntando a la zona de referencia.
    """
    if _now is not None:
        return _now.astimezone(_zona())
    return _dt.datetime.now(tz=_zona())


def hoy(_now: _dt.datetime | None = None) -> _dt.date:
    """
    Retorna la fecha actual en la zona horaria configurada.

    A las 19:50 hora Colombia (UTC−5), retorna la fecha del día en curso
    en Colombia — **no** la fecha UTC (que ya sería mañana).

    Args:
        _now: Si se provee, convierte este instante a la zona configurada
              y retorna su ``.date()``. Usar solo en tests.

    Returns:
        ``date`` en la zona de referencia.
    """
    return ahora(_now=_now).date()


__all__ = ["ahora", "hoy"]
