"""
UsuarioService
================
Orquesta los casos de uso del módulo de Usuarios.
"""
from __future__ import annotations

import secrets
import string

from src.services.solo_lectura import requiere_escritura

from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.service_ports import IAuthenticationService
from src.domain.models.usuario import (
    DocenteInfoDTO,
    FiltroUsuariosDTO,
    NuevoUsuarioDTO,
    ActualizarUsuarioDTO,
    Rol,
    Usuario,
    UsuarioResumenDTO,
    ResumenUsuariosDTO,
)
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    RegistroCambio,
    TipoEventoSesion,
)
from src.domain.policies.rbac_usuarios import (
    puede_gestionar,
    roles_asignables,
)
from src.domain.policies.password_policy import (
    errores_password,
    requisitos_password,
    validar_password,
)


class UsuarioService:
    """
    Orquesta los casos de uso del módulo de Usuarios.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IUsuarioRepository,
        auth_service: IAuthenticationService | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo      = repo
        self._auth      = auth_service
        self._auditoria = auditoria

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auditar(
        self,
        accion: AccionCambio,
        tabla: str,
        registro_id: int | None,
        datos_ant: dict | None,
        datos_nue: dict | None,
        usuario_id: int | None,
    ) -> None:
        if self._auditoria is None:
            return
        if accion == AccionCambio.CREATE:
            cambio = RegistroCambio.para_creacion(
                tabla, datos_nue or {}, registro_id, usuario_id
            )
        elif accion == AccionCambio.UPDATE:
            cambio = RegistroCambio.para_actualizacion(
                tabla, datos_ant or {}, datos_nue or {}, registro_id, usuario_id
            )
        else:
            cambio = RegistroCambio.para_eliminacion(
                tabla, datos_ant or {}, registro_id, usuario_id
            )
        self._auditoria.registrar_cambio(cambio)

    @staticmethod
    def _resolver_institucion(institucion_id: int | None) -> int | None:
        """
        Resuelve el tenant al CREAR un usuario, en este orden (espejo de
        estudiante_service/infraestructura_service):
          1. `institucion_id` explícito (el caller manda y no se toca).
          2. `institucion_actual()` — scope de la sesión (director → su
             institución; admin → None).
          3. `id_por_defecto()` (#1) — fallback de arranque/seed sin sesión.

        Devuelve None si no hay catálogo de instituciones todavía (single-tenant
        temprano) o si el Container no está disponible (tests con repos falsos).
        """
        if institucion_id is not None:
            return institucion_id
        from src.services.contexto_tenant import institucion_actual
        scope = institucion_actual()
        if scope is not None:
            return scope
        try:
            from container import Container
            return Container.institucion_service().id_por_defecto()
        except Exception:
            return None

    def _get_usuario_o_lanzar(self, usuario_id: int) -> Usuario:
        usuario = self._repo.get_by_id(usuario_id)
        if usuario is None:
            raise ValueError(f"Usuario con id {usuario_id} no existe.")
        # Autorización a nivel de objeto (paso_36): el target debe pertenecer a
        # la institución activa. Se verifica contra el institucion_id LEÍDO del
        # repo, no el que pueda venir del caller. Scope None (admin/seed) → pasa.
        from src.services.contexto_tenant import verificar_pertenencia
        verificar_pertenencia(usuario.institucion_id)
        return usuario

    def _registrar_evento(
        self,
        tipo_evento: TipoEventoSesion,
        usuario: Usuario,
        actor_id: int | None,
        detalles: str | None = None,
    ) -> None:
        """Registra un evento de sesión en la auditoría (no-op si no hay repo)."""
        if self._auditoria is None:
            return
        self._auditoria.registrar_evento(
            EventoSesion(
                usuario     = usuario.usuario,
                usuario_id  = usuario.id,
                tipo_evento = tipo_evento,
                detalles    = detalles,
            )
        )

    @staticmethod
    def _verificar_gestion(actor_rol: str | None, target: Usuario) -> None:
        """Defensa en profundidad: valida que el actor pueda gestionar al destino.

        `actor_rol=None` desactiva el enforcement (callers internos / tests).
        """
        if actor_rol is None:
            return
        if not puede_gestionar(actor_rol, target.rol):
            raise ValueError(
                f"Tu rol no tiene permiso para gestionar al usuario "
                f"'{target.usuario}'."
            )

    @staticmethod
    def _generar_password_temporal() -> str:
        """
        Genera una contraseña temporal fuerte y aleatoria (A2 — seguridad_01).

        Usa ``secrets`` (CSPRNG): 16 caracteres alfanuméricos. Se entrega al
        admin una sola vez para que la comunique al usuario; el flag
        ``debe_cambiar_password`` obliga a cambiarla en el primer acceso.

        Cumple la política de contraseñas (seguridad_02) POR CONSTRUCCIÓN:
        garantiza al menos una letra y al menos un dígito (no puede salir
        solo-letras ni solo-dígitos) y longitud 16 (>= 8). Los dos caracteres
        fijados se insertan en posiciones aleatorias para no ser predecibles.

        NO se loguea ni se persiste en claro: solo viaja como hash (vía
        IAuthenticationService) y como valor de retorno efímero.
        """
        alfabeto = string.ascii_letters + string.digits
        # Garantía por construcción: al menos una letra y al menos un dígito.
        chars = [
            secrets.choice(string.ascii_letters),
            secrets.choice(string.digits),
        ]
        chars += [secrets.choice(alfabeto) for _ in range(14)]
        # Barajado criptográfico para que las dos posiciones fijadas no sean
        # predecibles (no usar random.shuffle: no es CSPRNG).
        for i in range(len(chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            chars[i], chars[j] = chars[j], chars[i]
        return "".join(chars)

    # ------------------------------------------------------------------
    # Consultas de política (solo lectura) — para gating en la vista
    # ------------------------------------------------------------------

    def roles_asignables(self, actor_rol: str | None) -> set[str]:
        """Roles (strings) que `actor_rol` puede asignar o crear."""
        return roles_asignables(actor_rol)

    def puede_gestionar(self, actor_rol: str | None, target_rol: str) -> bool:
        """True si `actor_rol` puede gestionar a un usuario con rol `target_rol`."""
        if actor_rol is None:
            return False
        return puede_gestionar(actor_rol, target_rol)

    @staticmethod
    def requisitos_password() -> list[str]:
        """
        Textos legibles de las reglas de la política de contraseñas (M4).

        Passthrough de la policy de dominio que devuelve primitivos (strings),
        para que la UI muestre los requisitos sin importar `src.domain.*`.
        """
        return requisitos_password()

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    @requiere_escritura
    def crear_usuario(
        self,
        dto: NuevoUsuarioDTO,
        creado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """
        Crea un usuario nuevo.

        - Si `actor_rol` se provee, valida que pueda asignar `dto.rol` (RBAC).
        - Verifica que el username no exista.
        - Si NO se provee contraseña explícita, genera una temporal aleatoria
          fuerte (A2) y marca `debe_cambiar_password=True`; el usuario deberá
          cambiarla en el primer acceso.
        - Guarda el usuario y audita la creación.

        Returns:
            El `Usuario` creado. Cuando se generó una contraseña temporal (sin
            contraseña explícita), viaja en `usuario.password_temporal` para que
            el admin la comunique; es `None` cuando el admin fijó una contraseña.
            Ese campo es efímero: no se persiste ni se serializa (no se loguea).
        """
        if actor_rol is not None:
            rol_str = dto.rol.value if hasattr(dto.rol, "value") else str(dto.rol)
            if rol_str not in roles_asignables(actor_rol):
                raise ValueError(
                    f"Tu rol no tiene permiso para crear usuarios con rol "
                    f"'{rol_str}'."
                )
        usuario = dto.to_usuario()
        # Username ÚNICO GLOBAL (paso_37): un username no puede repetirse en
        # ninguna institución. Se valida la unicidad GLOBAL antes de insertar.
        # La institución del nuevo usuario se sigue resolviendo (scope de sesión
        # o #1 en seed/arranque) para scopear todo lo demás del multi-tenant.
        if self._repo.existe_usuario(dto.usuario):
            raise ValueError(
                f"Ya existe un usuario con el nombre '{dto.usuario}'."
            )

        # A2 — credencial inicial. Sin contraseña explícita → temporal fuerte
        # aleatoria + cambio forzado (nunca el username, que es predecible).
        if dto.password:
            # M4: si el admin fija una contraseña explícita, debe cumplir la
            # política de dominio (>=8, letra+dígito, != username).
            validar_password(dto.password, username=dto.usuario)
            password = dto.password
            temporal: str | None = None
            debe_cambiar = False
        else:
            password = self._generar_password_temporal()
            temporal = password
            debe_cambiar = True

        institucion_id = self._resolver_institucion(usuario.institucion_id)
        usuario = usuario.model_copy(update={
            "institucion_id": institucion_id,
            "debe_cambiar_password": debe_cambiar,
        })
        usuario = self._repo.guardar(usuario)

        # Hash de contraseña (delegado a IAuthenticationService).
        if self._auth is not None:
            self._auth.resetear_password(usuario.id, password)

        self._auditar(
            AccionCambio.CREATE, "usuarios", usuario.id,
            None, usuario.model_dump(mode="json"), creado_por_id,
        )
        # La temporal viaja en la entidad retornada (campo efímero, no persistido
        # ni serializado). model_dump de la auditoría arriba ya la excluye.
        return usuario.model_copy(update={"password_temporal": temporal})

    @requiere_escritura
    def actualizar(
        self,
        usuario_id: int,
        dto: ActualizarUsuarioDTO,
        actualizado_por_id: int | None = None,
    ) -> Usuario:
        """Actualiza nombre completo, email y/o teléfono de un usuario."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
        datos_ant = usuario.model_dump(mode="json")
        usuario_actualizado = dto.aplicar_a(usuario)
        self._repo.actualizar(usuario_actualizado)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            datos_ant, usuario_actualizado.model_dump(mode="json"),
            actualizado_por_id,
        )
        return usuario_actualizado

    @requiere_escritura
    def cambiar_rol(
        self,
        usuario_id: int,
        nuevo_rol: Rol,
        cambiado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """Cambia el rol de un usuario.

        Si `actor_rol` se provee, valida (defensa en profundidad) que el actor
        pueda asignar `nuevo_rol` Y pueda gestionar el rol actual del destino.
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        if actor_rol is not None:
            self._verificar_gestion(actor_rol, usuario)
            rol_str = (
                nuevo_rol.value if hasattr(nuevo_rol, "value") else str(nuevo_rol)
            )
            if rol_str not in roles_asignables(actor_rol):
                raise ValueError(
                    f"Tu rol no tiene permiso para asignar el rol '{rol_str}'."
                )
        if not usuario.activo:
            raise ValueError(
                f"El usuario '{usuario.usuario}' está desactivado y no puede modificarse."
            )
        datos_ant = usuario.model_dump(mode="json")
        self._repo.cambiar_rol(usuario_id, nuevo_rol)
        usuario_actualizado = usuario.model_copy(update={"rol": nuevo_rol})
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            datos_ant, usuario_actualizado.model_dump(mode="json"),
            cambiado_por_id,
        )
        self._registrar_evento(
            TipoEventoSesion.CAMBIAR_ROL, usuario_actualizado, cambiado_por_id,
            detalles=f"Rol cambiado a '{usuario_actualizado.rol.value}'",
        )
        return usuario_actualizado

    @requiere_escritura
    def desactivar(
        self,
        usuario_id: int,
        desactivado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """Desactiva un usuario (soft delete).

        Si `actor_rol` se provee, valida que pueda gestionar al destino (RBAC).
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        self._verificar_gestion(actor_rol, usuario)
        usuario_desactivado = usuario.desactivar()  # lanza si ya está inactivo
        self._repo.desactivar(usuario_id)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            usuario.model_dump(mode="json"),
            usuario_desactivado.model_dump(mode="json"),
            desactivado_por_id,
        )
        self._registrar_evento(
            TipoEventoSesion.DESACTIVAR_USUARIO, usuario_desactivado,
            desactivado_por_id,
        )
        return usuario_desactivado

    @requiere_escritura
    def reactivar(
        self,
        usuario_id: int,
        reactivado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """Reactiva un usuario desactivado.

        Si `actor_rol` se provee, valida que pueda gestionar al destino (RBAC).
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        self._verificar_gestion(actor_rol, usuario)
        usuario_reactivado = usuario.reactivar()  # lanza si ya está activo
        self._repo.reactivar(usuario_id)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            usuario.model_dump(mode="json"),
            usuario_reactivado.model_dump(mode="json"),
            reactivado_por_id,
        )
        self._registrar_evento(
            TipoEventoSesion.ACTIVAR_USUARIO, usuario_reactivado,
            reactivado_por_id,
        )
        return usuario_reactivado

    @requiere_escritura
    def resetear_password(
        self,
        usuario_id: int,
        nueva_password: str,
        actor_rol: str | None = None,
        reset_por_id: int | None = None,
    ) -> str | None:
        """
        Restablece la contraseña de un usuario SIN verificar la anterior.

        Flujo administrativo (admin/director recuperando una cuenta):
        - Si `actor_rol` se provee, valida que pueda gestionar al destino (RBAC).
        - Si `nueva_password` viene vacía, genera una temporal aleatoria fuerte
          (A2) en lugar del username (predecible) y la retorna para comunicarla.
        - En ambos casos marca `debe_cambiar_password=True`: tras un reset
          administrativo el dueño debe re-elegir su contraseña.
        - Delega el hash al servicio de autenticación.
        - Audita el evento con TipoEventoSesion.RESETEAR_PASSWORD.

        Returns:
            La contraseña temporal generada cuando no se dio una explícita
            (para comunicarla), o `None` cuando el admin fijó una. NUNCA se loguea.
        """
        if self._auth is None:
            raise ValueError(
                "El servicio de autenticación no está configurado."
            )
        usuario = self._get_usuario_o_lanzar(usuario_id)
        self._verificar_gestion(actor_rol, usuario)
        explicita = (nueva_password or "").strip()
        if explicita:
            # M4: una contraseña explícita debe cumplir la política de dominio.
            validar_password(explicita, username=usuario.usuario)
            password = explicita
            temporal: str | None = None
        else:
            password = self._generar_password_temporal()
            temporal = password
        self._auth.resetear_password(usuario_id, password)
        # A2: reset administrativo → el dueño debe re-elegir en el primer acceso.
        self._repo.marcar_debe_cambiar_password(usuario_id, True)
        self._registrar_evento(
            TipoEventoSesion.RESETEAR_PASSWORD, usuario, reset_por_id,
            detalles=f"Contraseña restablecida para '{usuario.usuario}'",
        )
        return temporal

    @requiere_escritura
    def cambiar_password(
        self,
        usuario_id: int,
        password_actual: str,
        password_nuevo: str,
    ) -> None:
        """
        Cambia la contraseña verificando la actual.
        Lanza ValueError si la contraseña actual es incorrecta.
        """
        if self._auth is None:
            raise ValueError(
                "El servicio de autenticación no está configurado."
            )
        # M4: la nueva contraseña debe cumplir la política de dominio ANTES de
        # delegar al auth (>=8, letra+dígito, != username). Se resuelve el
        # username del usuario para la regla anti-igualdad (lectura best-effort:
        # si el repo no lo encuentra, se valida sin username).
        usuario = self._repo.get_by_id(usuario_id)
        username = usuario.usuario if usuario is not None else None
        validar_password(password_nuevo, username=username)

        exito = self._auth.cambiar_password(
            usuario_id, password_actual, password_nuevo
        )
        if not exito:
            raise ValueError("La contraseña actual no es correcta.")
        # A2: el dueño cambió su contraseña → ya no está forzado.
        self._repo.marcar_debe_cambiar_password(usuario_id, False)

    def listar_docentes(
        self,
        periodo_id: int | None = None,
    ) -> list[DocenteInfoDTO]:
        """Retorna los docentes con su carga académica calculada."""
        return self._repo.listar_docentes_info(
            periodo_id=periodo_id, solo_activos=True
        )

    @staticmethod
    def _aplicar_scope(filtro: FiltroUsuariosDTO) -> FiltroUsuariosDTO:
        """
        Auto-scope por institución (frente C — paso_28).

        Si el `filtro.institucion_id` viene None, lo resuelve desde el scope
        de la sesión (`institucion_actual()`): None para admin → ve TODAS;
        institución para director → filtrado. Un `institucion_id` explícito
        (selector del admin "Todas"/concreta) NO se toca. `solo_activos` y el
        resto del filtro se conservan.
        """
        if filtro.institucion_id is not None:
            return filtro
        from src.services.contexto_tenant import institucion_actual
        scope = institucion_actual()
        if scope is None:
            return filtro
        return filtro.model_copy(update={"institucion_id": scope})

    def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]:
        """Retorna usuarios según los filtros indicados (auto-scope por tenant)."""
        return self._repo.listar_filtrado(self._aplicar_scope(filtro))

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        """Retorna la vista resumida de usuarios (auto-scope por tenant)."""
        return self._repo.listar_resumenes(self._aplicar_scope(filtro))

    def listar_para_ver_como(
        self, institucion_id: int | None = None
    ) -> list[UsuarioResumenDTO]:
        """
        Listado de SOLO LECTURA de usuarios activos candidatos a 'Ver como',
        con scope por institución (multi-tenant, paso_24 / frente C paso_28).

        `institucion_id`:
          - None  → resuelve desde el scope de la sesión (`institucion_actual()`):
                    None para admin → todos los usuarios activos (plataforma);
                    institución para director → solo los de su institución.
          - int   → solo los usuarios activos de esa institución (explícito).

        El filtro se aplica en el repositorio (FiltroUsuariosDTO.institucion_id),
        de modo que el resumen ya viene scopeado por tenant.
        """
        return self._repo.listar_resumenes(
            self._aplicar_scope(
                FiltroUsuariosDTO(
                    solo_activos=True,
                    por_pagina=200,
                    institucion_id=institucion_id,
                )
            )
        )

    def get_by_id(self, usuario_id: int) -> Usuario:
        """Retorna un usuario por id. Lanza si no existe."""
        return self._get_usuario_o_lanzar(usuario_id)

    def resumen_por_rol(self) -> ResumenUsuariosDTO:
        """
        Agregación de SOLO LECTURA para el dashboard de plataforma.

        Cuenta usuarios por rol (incluye inactivos en el total) y expone el
        número de activos. No muta nada.
        """
        todos = self._repo.listar_resumenes(
            FiltroUsuariosDTO(solo_activos=False, por_pagina=200)
        )
        por_rol: dict[str, int] = {}
        activos = 0
        for u in todos:
            rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
            por_rol[rol_str] = por_rol.get(rol_str, 0) + 1
            if u.activo:
                activos += 1
        return ResumenUsuariosDTO(
            por_rol=por_rol, total=len(todos), activos=activos
        )

    def carga_horaria_max(self, usuario_id: int) -> int | None:
        """Retorna la carga horaria máxima del usuario, o None si no está definida."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
        return usuario.carga_horaria_max

    @requiere_escritura
    def configurar_carga(
        self,
        usuario_id: int,
        carga_horaria_max: int | None,
        horas_extra: int = 0,
        actualizado_por_id: int | None = None,
    ) -> Usuario:
        """Configura el tope semanal y las horas extra de un docente.

        `carga_horaria_max=None` significa sin límite. `horas_extra` amplía el
        tope efectivo. Valida rangos vía el modelo Usuario.
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        if carga_horaria_max is not None and carga_horaria_max < 0:
            raise ValueError("La carga máxima no puede ser negativa.")
        if horas_extra < 0:
            raise ValueError("Las horas extra no pueden ser negativas.")
        datos_ant = usuario.model_dump(mode="json")
        self._repo.actualizar_carga(usuario_id, carga_horaria_max, horas_extra)
        actualizado = usuario.model_copy(update={
            "carga_horaria_max": carga_horaria_max,
            "horas_extra": horas_extra,
        })
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            datos_ant, actualizado.model_dump(mode="json"), actualizado_por_id,
        )
        return actualizado


__all__ = ["UsuarioService"]
