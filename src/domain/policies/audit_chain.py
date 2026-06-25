"""
Encadenamiento por hash de la bitácora de auditoría (dominio puro)
==================================================================

Funciones puras (sin estado, sin dependencias de infraestructura ni interfaz)
que codifican CÓMO se firma cada registro de auditoría encadenándolo con el
anterior, para volver detectable cualquier edición, inserción o borrado
intermedio en las tablas append-only (`auditoria` y `audit_log`).

Modelo:
  hash_cadena = SHA256(hash_previo_or_GENESIS || payload_canónico)

donde:
  - `hash_previo` es el `hash_cadena` del registro inmediatamente anterior de la
    MISMA tabla (o `GENESIS` si la tabla está vacía / es el primer eslabón).
  - `payload_canónico` es la serialización JSON estable (claves ordenadas) de los
    campos persistidos del registro, SIN el `id` (lo asigna SQLite tras el INSERT).

La verificación recalcula la cadena en orden y reporta el ÍNDICE (0-based) del
primer eslabón cuyo hash almacenado no coincide con el recalculado.

Limitación conocida (documentada, fuera de alcance aquí): el encadenamiento
detecta edición/inserción/borrado INTERMEDIO; el truncado del final (borrar los
últimos N registros) requiere un ancla externa y no se resuelve en esta capa.

Esta es la fuente de verdad del algoritmo de cadena. El repositorio SQLite
calcula `hash_cadena` al insertar llamando a `calcular_hash`, y verifica la
integridad reconstruyendo la secuencia y delegando en `primer_eslabon_roto`.
NUNCA hace IO: solo recibe primitivos y devuelve primitivos.
"""
from __future__ import annotations

import hashlib
import json


# Eslabón cero: hash previo del primer registro de una tabla vacía.
GENESIS = "GENESIS"


def calcular_hash(hash_previo: str | None, campos: dict) -> str:
    """
    Calcula el `hash_cadena` de un registro a partir del hash del anterior.

    Serializa `campos` de forma canónica (claves ordenadas, separadores estables,
    sin espacios dependientes de la plataforma) y devuelve el hex digest SHA-256
    de `(hash_previo_or_GENESIS + payload)`.

    Args:
        hash_previo: `hash_cadena` del registro anterior, o None/"" si es el
                     primer eslabón (se usa GENESIS).
        campos:      Campos persistidos del registro (sin el `id`).

    Returns:
        Hex digest SHA-256 (64 caracteres).
    """
    base = hash_previo or GENESIS
    payload = json.dumps(
        campos,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256((base + payload).encode("utf-8")).hexdigest()


def primer_eslabon_roto(secuencia: list[tuple[dict, str]]) -> int | None:
    """
    Devuelve el índice (0-based) del primer eslabón roto de la cadena, o None.

    Recibe la secuencia ORDENADA de `(campos, hash_almacenado)` y la recalcula
    encadenando desde GENESIS. Devuelve el índice del primer registro cuyo
    `hash_almacenado` no coincide con el hash recalculado (lo que delata una
    edición, inserción o borrado intermedio). `None` si la cadena es íntegra.

    Args:
        secuencia: Lista ordenada de tuplas `(campos, hash_almacenado)`.

    Returns:
        Índice del primer eslabón roto, o None si toda la cadena es íntegra.
    """
    hash_previo: str | None = None
    for indice, (campos, hash_almacenado) in enumerate(secuencia):
        esperado = calcular_hash(hash_previo, campos)
        if esperado != hash_almacenado:
            return indice
        hash_previo = hash_almacenado
    return None


__all__ = ["GENESIS", "calcular_hash", "primer_eslabon_roto"]
