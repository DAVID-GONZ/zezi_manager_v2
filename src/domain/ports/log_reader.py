"""
src/domain/ports/log_reader.py
================================
Puerto de lectura de log estructurado (obs_13 — R5).

Abstrae el acceso al archivo JSONL de seguridad. El servicio no abre
archivos: delega en ILogReader.

Regla de capas: solo stdlib (ABC) — sin infraestructura ni nicegui.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ILogReader(ABC):
    """
    Contrato de lectura del log de seguridad estructurado.

    El implementador concreto abre el archivo y aplica los filtros.
    El servicio de observabilidad lo consume sin saber dónde vive el archivo.
    """

    @abstractmethod
    def leer_ultimos(
        self,
        n: int = 200,
        *,
        nivel: str | None = None,
        tipo_evento: str | None = None,
    ) -> list[dict]:
        """
        Últimas ``n`` entradas del log estructurado, más recientes primero.

        Args:
            n:           Número máximo de entradas a devolver.
            nivel:       Filtrar por nivel de log (``"WARNING"``, ``"INFO"``…).
                         None → sin filtro.
            tipo_evento: Filtrar por el campo ``tipo_evento`` del JSON.
                         None → sin filtro.

        Returns:
            Lista de dicts de primitivos (R8: solo campos de la whitelist).
            Una línea ilegible se descarta sin romper la lectura.
            Un archivo ausente devuelve lista vacía.

        Contrato:
          - No lanza excepciones: un archivo inexistente o ilegible devuelve [].
          - Los dicts solo contienen campos de ``_CAMPOS_PERMITIDOS``; cualquier
            otro campo se descarta (R8).
          - Lee solo la cola del archivo para evitar cargar archivos grandes
            completos en memoria (R6).
        """
        ...

    @abstractmethod
    def disponible(self) -> bool:
        """
        Indica si el archivo de log configurado existe y es legible.

        Permite distinguir «no hay eventos» de «no puedo leer el log»
        (R7): lista vacía tranquila vs. estado vacío que exige acción.

        Returns:
            True si el archivo existe y puede leerse; False en otro caso.
        """
        ...


__all__ = ["ILogReader"]
