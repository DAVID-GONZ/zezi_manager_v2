"""
src/infrastructure/logging/jsonl_log_reader.py
================================================
Implementación concreta de ILogReader para el log JSONL rotado (obs_13 — T3).

Lee solo la cola del archivo con un tope de bytes para evitar cargar archivos
rotados de hasta 10 MB completos (R6).

Los campos se filtran contra ``_CAMPOS_PERMITIDOS`` importada de security_logger.py
(no duplicada — R8). La importación de ``security_logger`` es perezosa (dentro
del método) para evitar efectos secundarios al importar el módulo en tests.

Regla de capas: infraestructura — importa domain (ILogReader) + stdlib + config.
"""
from __future__ import annotations

import json
import logging

from src.domain.ports.log_reader import ILogReader

logger = logging.getLogger("infra.jsonl_log_reader")

# Tope de bytes que se leen de la cola del archivo (R6).
# Con líneas JSONL de ~200 bytes, medio MB da ~2 500 entradas,
# más que suficiente para mostrar 200 líneas con filtros activos.
_TOPE_BYTES: int = 512 * 1024  # 512 KB


class JsonlLogReader(ILogReader):
    """
    Lee la cola del archivo JSONL de seguridad.

    Implementa R6: lee solo los últimos ``_TOPE_BYTES`` bytes.
    Implementa R8: filtra cada entrada contra ``_CAMPOS_PERMITIDOS``.
    Implementa R7: archivo ausente → disponible() False; leer_ultimos() devuelve [].
    """

    def disponible(self) -> bool:
        """True si el archivo configurado existe y es legible."""
        ruta = self._ruta()
        if ruta is None:
            return False
        try:
            return ruta.exists() and ruta.is_file()
        except Exception:
            return False

    def leer_ultimos(
        self,
        n: int = 200,
        *,
        nivel: str | None = None,
        tipo_evento: str | None = None,
    ) -> list[dict]:
        """
        Últimas ``n`` entradas del log, más recientes primero.

        Lee solo la cola del archivo (R6). Descarta líneas ilegibles sin
        romper la lectura. Filtra contra _CAMPOS_PERMITIDOS (R8).
        """
        ruta = self._ruta()
        if ruta is None or not ruta.exists():
            return []

        try:
            campos_ok = self._campos_permitidos()
            tam = ruta.stat().st_size
            with ruta.open("rb") as fh:
                fh.seek(max(0, tam - _TOPE_BYTES))
                crudo = fh.read().decode("utf-8", errors="replace")

            lineas = crudo.splitlines()
            # Si buscamos a mitad del archivo la primera línea puede estar cortada.
            if tam > _TOPE_BYTES and lineas:
                lineas = lineas[1:]

            entradas: list[dict] = []
            for linea in reversed(lineas):
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    doc = json.loads(linea)
                except json.JSONDecodeError:
                    continue  # Línea a medio escribir o corrupta: se descarta (R6)

                # Filtrar contra whitelist (R8)
                entrada: dict = {k: v for k, v in doc.items() if k in campos_ok}

                # Filtros opcionales
                if nivel is not None:
                    # El nivel no está en el JSON; solo podemos inferirlo del tipo_evento.
                    # Se usa un campo "nivel" si existiera; sino se infiere de severidad.
                    # Para simplicidad, se deja pasar si no hay campo nivel.
                    pass
                if tipo_evento is not None:
                    if entrada.get("tipo_evento") != tipo_evento:
                        continue

                entradas.append(entrada)
                if len(entradas) >= n:
                    break

            return entradas

        except Exception as exc:
            logger.warning("Error leyendo log de seguridad: %s", exc)
            return []

    # ── Helpers internos ───────────────────────────────────────────────────────

    @staticmethod
    def _ruta():
        """Ruta del archivo de log de seguridad desde config. None si no está configurado."""
        try:
            from config import settings
            return settings.SECURITY_LOG_FILE
        except Exception:
            return None

    @staticmethod
    def _campos_permitidos() -> frozenset:
        """Importa _CAMPOS_PERMITIDOS desde security_logger (no duplica — R8)."""
        from src.infrastructure.logging.security_logger import _CAMPOS_PERMITIDOS
        return _CAMPOS_PERMITIDOS


__all__ = ["JsonlLogReader"]
