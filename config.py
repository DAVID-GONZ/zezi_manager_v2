"""
config.py — Configuración centralizada de ZECI Manager v2.0
============================================================

Fuentes de configuración (en orden de prioridad):
  1. Variables de entorno del sistema operativo.
  2. Archivo .env en la raíz del proyecto.
  3. Valores por defecto definidos en Settings.

Uso:
    from config import settings, DATABASE_PATH, IS_PRODUCTION

    if settings.is_production:
        ...

    with get_connection() as conn:   # usa DATABASE_PATH internamente
        ...

Variables de entorno relevantes:
    APP_ENV             development | production | test  (default: development)
    DATABASE_PATH       Ruta al archivo SQLite           (default: data/app.db)
    JWT_SECRET          Clave para firmar tokens JWT     (requerida en producción)
    JWT_EXPIRE_MINUTES  Minutos de vida del token        (default: 480)
    HOST                Host para NiceGUI                (default: 127.0.0.1)
    PORT                Puerto para NiceGUI              (default: 8080)
    LOG_LEVEL           DEBUG | INFO | WARNING | ERROR   (default: INFO)

Entorno de test:
    pytest pone PYTEST_CURRENT_TEST automáticamente.
    connection.py detecta ese flag y usa DB_PATH_OVERRIDE si existe,
    permitiendo tests con BD en archivo temporal sin alterar esta config.
"""

from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del proyecto (directorio que contiene este archivo)
_PROJECT_ROOT = Path(__file__).parent


class Settings(BaseSettings):
    """
    Configuración de la aplicación leída desde el entorno y .env.

    Todos los campos tienen valores por defecto seguros para desarrollo.
    En producción, APP_ENV y JWT_SECRET deben setearse explícitamente.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",           # ignorar vars de entorno no declaradas
    )

    # ------------------------------------------------------------------
    # Entorno
    # ------------------------------------------------------------------
    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_NAME: str = "ZECI Manager"
    APP_VERSION: str = "2.0.0"

    # ------------------------------------------------------------------
    # Base de datos
    # ------------------------------------------------------------------
    DATABASE_PATH: Path = Field(
        default=_PROJECT_ROOT / "data" / "app.db",
        description="Ruta al archivo SQLite. Relativa a la raíz del proyecto.",
    )
    DB_TIMEOUT: float = Field(
        default=5.0,
        gt=0,
        description="Segundos de espera máxima cuando la BD está bloqueada.",
    )
    DB_JOURNAL_MODE: Literal["WAL", "DELETE", "TRUNCATE", "PERSIST", "MEMORY"] = "WAL"

    # ------------------------------------------------------------------
    # Autenticación y seguridad
    # ------------------------------------------------------------------
    JWT_SECRET: str = Field(
        default="cambia-esta-clave-en-produccion-ahora",
        min_length=32,
        description="Clave secreta para firmar tokens JWT. DEBE cambiarse en producción.",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = Field(
        default=480,   # 8 horas — jornada escolar completa
        gt=0,
        le=1440,       # máximo 24 horas
    )

    # ------------------------------------------------------------------
    # NiceGUI / servidor
    # ------------------------------------------------------------------
    HOST: str = "127.0.0.1"
    PORT: int = Field(default=8080, gt=0, le=65535)
    RELOAD: bool = False           # True solo en desarrollo con hot-reload

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FILE: Path | None = None   # None → solo consola; Path → también archivo

    # ------------------------------------------------------------------
    # Validadores
    # ------------------------------------------------------------------

    @field_validator("DATABASE_PATH", mode="before")
    @classmethod
    def resolver_db_path(cls, v: str | Path) -> Path:
        """Convierte rutas relativas en absolutas respecto a la raíz del proyecto."""
        path = Path(v)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
        return path

    @field_validator("LOG_FILE", mode="before")
    @classmethod
    def resolver_log_path(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        path = Path(v)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
        return path

    @model_validator(mode="after")
    def advertir_jwt_inseguro(self) -> "Settings":
        """Emite advertencia si JWT_SECRET tiene el valor por defecto en producción."""
        if (
            self.APP_ENV == "production"
            and "cambia-esta-clave" in self.JWT_SECRET
        ):
            import warnings
            warnings.warn(
                "JWT_SECRET tiene el valor por defecto. "
                "Define una clave segura en .env antes de desplegar.",
                stacklevel=2,
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades derivadas
    # ------------------------------------------------------------------

    @cached_property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @cached_property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @cached_property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"

    @cached_property
    def db_config(self) -> dict:
        """
        Diccionario de configuración SQLite consumido por connection.py.
        Centraliza los pragmas en un solo lugar.
        """
        return {
            "journal_mode":     self.DB_JOURNAL_MODE,
            "timeout":          self.DB_TIMEOUT,
            "foreign_keys":     True,
            "check_same_thread": False,   # NiceGUI usa múltiples hilos
        }

    def configure_logging(self) -> None:
        """
        Aplica la configuración de logging definida en Settings.
        Llamar UNA SOLA VEZ desde main.py antes de arrancar la aplicación.
        """
        handlers: list[logging.Handler] = [logging.StreamHandler()]

        if self.LOG_FILE:
            self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(self.LOG_FILE, encoding="utf-8"))

        logging.basicConfig(
            level=self.LOG_LEVEL,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=handlers,
            force=True,
        )


# ---------------------------------------------------------------------------
# Instancia singleton — se crea una vez al importar el módulo
# ---------------------------------------------------------------------------
settings = Settings()


# ---------------------------------------------------------------------------
# Exports de compatibilidad
# Los módulos internos (connection.py, etc.) importan directamente estas vars.
# ---------------------------------------------------------------------------
DATABASE_PATH: Path = settings.DATABASE_PATH
DB_CONFIG: dict    = settings.db_config
IS_PRODUCTION: bool = settings.is_production


__all__ = [
    "settings",
    "DATABASE_PATH",
    "DB_CONFIG",
    "IS_PRODUCTION",
    "Settings",
]