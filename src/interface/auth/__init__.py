"""
src/interface/auth — Autorización central de rutas (paso_35).

Expone el guard de ruta deny-by-default (`registrar_pagina`), los sentinels
de acceso (`PUBLICO`, `AUTENTICADO`) y el registro consultable `ruta → roles`
que es la ÚNICA fuente de verdad de autorización por ruta.
"""
from __future__ import annotations

from .route_guard import (
    AUTENTICADO,
    PUBLICO,
    registrar_pagina,
    roles_de_ruta,
    rutas_registradas,
)

__all__ = [
    "PUBLICO",
    "AUTENTICADO",
    "registrar_pagina",
    "roles_de_ruta",
    "rutas_registradas",
]
