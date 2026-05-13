"""
BcryptAuthService — implementación bcrypt de IAuthenticationService.
"""
from __future__ import annotations

import bcrypt
import hashlib

from src.domain.ports.service_ports import IAuthenticationService
from src.domain.ports.usuario_repo import IUsuarioRepository


class BcryptAuthService(IAuthenticationService):
    """
    Autenticación basada en bcrypt.
    No gestiona sesiones ni tokens: solo hashea y verifica contraseñas.
    El repositorio se inyecta en el constructor para que las firmas
    de método respeten exactamente el contrato de IAuthenticationService.
    """

    ROUNDS = 12  # balance seguridad/velocidad; aumentar en producción si el hardware lo permite

    def __init__(self, repo: IUsuarioRepository | None = None) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # IAuthenticationService
    # ------------------------------------------------------------------

    def hashear_password(self, password_plain: str) -> str:
        """Genera un hash bcrypt con salt interno aleatorio."""
        return bcrypt.hashpw(
            password_plain.encode("utf-8"),
            bcrypt.gensalt(rounds=self.ROUNDS),
        ).decode("utf-8")

    def verificar_password(self, password_plain: str, password_hash: str) -> bool:
        """
        Verifica el password contra su hash.
        Compatible con hashes sha256: (legacy del seed de desarrollo).
        Retorna False en lugar de propagar excepciones de bcrypt.
        """
        if password_hash.startswith("sha256:"):
            digest = hashlib.sha256(password_plain.encode()).hexdigest()
            return password_hash == f"sha256:{digest}"
        try:
            return bcrypt.checkpw(
                password_plain.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except Exception:
            return False

    def cambiar_password(
        self,
        usuario_id: int,
        password_actual: str,
        password_nueva: str,
    ) -> bool:
        """
        Verifica la contraseña actual y, si es correcta, persiste el nuevo hash.
        Lanza ValueError si el usuario no existe o la contraseña actual no coincide.
        Requiere que el servicio haya sido construido con un repo.
        """
        if self._repo is None:
            raise RuntimeError("BcryptAuthService requiere un repo para cambiar contraseñas.")
        hash_actual = self._repo.get_password_hash(usuario_id)
        if hash_actual is None:
            raise ValueError(f"Usuario {usuario_id} no encontrado.")
        if not self.verificar_password(password_actual, hash_actual):
            raise ValueError("La contraseña actual no es correcta.")
        self._repo.actualizar_password_hash(usuario_id, self.hashear_password(password_nueva))
        return True

    def resetear_password(self, usuario_id: int, password_nueva: str) -> None:
        """
        Establece una nueva contraseña sin verificar la anterior.
        Solo debe invocarse desde flujos administrativos autorizados.
        Requiere que el servicio haya sido construido con un repo.
        """
        if self._repo is None:
            raise RuntimeError("BcryptAuthService requiere un repo para resetear contraseñas.")
        self._repo.actualizar_password_hash(usuario_id, self.hashear_password(password_nueva))


__all__ = ["BcryptAuthService"]
