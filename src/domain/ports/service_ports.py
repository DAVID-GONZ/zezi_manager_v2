"""
Ports: Servicios transversales
================================
Contratos de servicio (no de repositorio) para capacidades técnicas
que atraviesan múltiples módulos del dominio.

Cubre tres servicios de infraestructura:
  IAuthenticationService — verificación y gestión de credenciales
  INotificationService   — envío de notificaciones (email, SMS, push)
  IExporterService       — exportación de datos a formatos externos (PDF, Excel)

Diferencia con los repositorios:
  Los repositorios modelan el acceso a datos (CRUD contra la BD).
  Los service ports modelan capacidades técnicas externas o transversales
  que los servicios de dominio necesitan pero no deben implementar.

Principios:
  - No importan nada de infraestructura (SQLite, smtp, openpyxl, etc.).
  - Solo dependen de tipos primitivos y modelos del dominio.
  - Cada interface tiene una única responsabilidad.
  - Las implementaciones concretas viven en src/infrastructure/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Solo en tiempo de análisis estático; en runtime la anotación es string
    # gracias a `from __future__ import annotations`.
    from src.domain.models.usuario import Usuario


# =============================================================================
# Autenticación
# =============================================================================

class IAuthenticationService(ABC):
    """
    Gestión de credenciales de usuarios.

    Responsabilidades:
      - Hashear contraseñas al crear/cambiar.
      - Verificar contraseñas en el login.
      - Cambiar contraseñas con validación de la contraseña actual.

    Nunca:
      - Gestiona sesiones (eso es responsabilidad de la capa de interfaz).
      - Accede directamente a la BD (usa IUsuarioRepository para leer users).
    """

    @abstractmethod
    def hashear_password(self, password_plain: str) -> str:
        """
        Retorna el hash seguro de una contraseña en texto plano.
        El algoritmo y los parámetros (salt, iteraciones) son
        responsabilidad de la implementación concreta.
        Nunca almacena ni registra la contraseña en texto plano.
        """
        ...

    @abstractmethod
    def verificar_password(
        self,
        password_plain: str,
        password_hash: str,
    ) -> bool:
        """
        True si la contraseña en texto plano coincide con el hash almacenado.
        Usado en el proceso de login y en el cambio de contraseña.
        """
        ...

    @abstractmethod
    def cambiar_password(
        self,
        usuario_id: int,
        password_actual: str,
        password_nueva: str,
    ) -> bool:
        """
        Verifica password_actual y, si es correcta, persiste el hash
        de password_nueva en la BD.
        Retorna True si el cambio fue exitoso.
        Retorna False si password_actual no coincide con el hash almacenado.
        """
        ...

    @abstractmethod
    def resetear_password(
        self,
        usuario_id: int,
        password_nueva: str,
    ) -> None:
        """
        Establece una nueva contraseña sin verificar la anterior.
        Solo debe llamarse desde flujos administrativos autorizados
        (admin reseteando contraseña de un docente, por ejemplo).
        """
        ...

    @abstractmethod
    def autenticar_usuario(
        self,
        nombre_usuario: str,
        password_plain: str,
    ) -> "Usuario":
        """
        Autentica un usuario por nombre de usuario y contraseña en texto plano.

        Es el único punto de entrada para el flujo de login: encapsula la
        búsqueda del usuario, la verificación del hash y la comprobación
        del estado de la cuenta. La capa de interfaz NO debe acceder al
        repositorio directamente para ninguno de estos pasos.

        Returns:
            La entidad ``Usuario`` autenticada y activa.

        Raises:
            ValueError("credenciales_invalidas"):
                Si el usuario no existe en la BD o la contraseña no coincide.
                Se usa un mensaje genérico para no facilitar enumeración de
                usuarios a un atacante.
            ValueError("cuenta_inactiva"):
                Si las credenciales son correctas pero la cuenta está
                desactivada. Permite mostrar un mensaje diferenciado al
                usuario sin revelar información a atacantes (el mensaje solo
                se muestra tras verificar exitosamente la contraseña).
            RuntimeError:
                Si el servicio fue construido sin repositorio inyectado.
        """
        ...


# =============================================================================
# Notificaciones
# =============================================================================

class INotificationService(ABC):
    """
    Envío de notificaciones a usuarios, docentes y acudientes.

    El servicio de dominio decide CUÁNDO y A QUIÉN notificar;
    este port define CÓMO se envía la notificación.
    La implementación concreta decide el canal (email, SMS, push).
    """

    @abstractmethod
    def notificar_acudiente(
        self,
        acudiente_id: int,
        asunto: str,
        cuerpo: str,
    ) -> bool:
        """
        Envía una notificación al acudiente indicado.
        Retorna True si el envío fue exitoso.
        Los canales disponibles dependen de la implementación concreta
        y de los datos de contacto del acudiente.
        """
        ...

    @abstractmethod
    def notificar_docente(
        self,
        usuario_id: int,
        asunto: str,
        cuerpo: str,
    ) -> bool:
        """
        Envía una notificación a un docente.
        Retorna True si el envío fue exitoso.
        """
        ...

    @abstractmethod
    def notificar_directivos(
        self,
        asunto: str,
        cuerpo: str,
    ) -> int:
        """
        Envía una notificación a todos los usuarios con rol
        director o coordinador.
        Retorna el número de notificaciones enviadas exitosamente.
        """
        ...


# =============================================================================
# Exportación
# =============================================================================

class IExporterService(ABC):
    """
    Exportación de datos a formatos externos para descarga.

    El servicio de dominio prepara los datos en estructuras del dominio
    (DTOs, listas); este port los convierte al formato de salida.
    La implementación concreta gestiona las dependencias de librerías
    (openpyxl, reportlab, weasyprint, etc.).
    """

    @abstractmethod
    def exportar_excel(
        self,
        datos: list[dict],
        nombre_hoja: str = "Datos",
        ruta_destino: Path | None = None,
    ) -> bytes:
        """
        Genera un archivo Excel (.xlsx) con los datos indicados.
        Si ruta_destino es None, retorna el contenido como bytes
        (para envío directo al navegador).
        Si ruta_destino se provee, guarda el archivo y retorna bytes vacíos.
        """
        ...

    @abstractmethod
    def exportar_pdf(
        self,
        html_content: str,
        ruta_destino: Path | None = None,
    ) -> bytes:
        """
        Genera un PDF a partir de HTML con estilos CSS.
        Si ruta_destino es None, retorna el contenido como bytes.
        Usado para boletines, informes de convivencia y certificados.
        """
        ...

    @abstractmethod
    def exportar_csv(
        self,
        datos: list[dict],
        ruta_destino: Path | None = None,
        encoding: str = "utf-8-sig",
    ) -> bytes:
        """
        Genera un archivo CSV con los datos indicados.
        Usa utf-8-sig por defecto para compatibilidad con Excel en Windows.
        Si ruta_destino es None, retorna el contenido como bytes.
        """
        ...


__all__ = [
    "IAuthenticationService",
    "INotificationService",
    "IExporterService",
]
