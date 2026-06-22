"""
EstudianteService
==================
Orquesta los casos de uso del módulo de Estudiantes y PIARs.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.ports.acudiente_repo import IAcudienteRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.estudiante import (
    Estudiante,
    EstadoMatricula,
    NuevoEstudianteDTO,
    ActualizarEstudianteDTO,
    FiltroEstudiantesDTO,
    EstudianteResumenDTO,
)
from src.domain.models.piar import PIAR, NuevoPIARDTO, ActualizarPIARDTO
from src.domain.models.dtos import MatriculaMasivaResultadoDTO
from src.domain.models.auditoria import AccionCambio, RegistroCambio


class EstudianteService:
    """
    Orquesta los casos de uso del módulo de Estudiantes.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IEstudianteRepository,
        acudiente_repo: IAcudienteRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo           = repo
        self._acudiente_repo = acudiente_repo
        self._auditoria      = auditoria

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

    def _get_estudiante_o_lanzar(self, estudiante_id: int) -> Estudiante:
        est = self._repo.get_by_id(estudiante_id)
        if est is None:
            raise ValueError(f"Estudiante con id {estudiante_id} no existe.")
        # Autorización a nivel de objeto (paso_36): el estudiante debe pertenecer
        # a la institución activa. Se verifica contra el institucion_id LEÍDO del
        # repo. Scope None (admin/seed) → pasa.
        from src.services.contexto_tenant import verificar_pertenencia
        verificar_pertenencia(est.institucion_id)
        return est

    @staticmethod
    def _resolver_institucion(institucion_id: int | None) -> int | None:
        """
        Resuelve el tenant al CREAR/IMPORTAR estudiantes, en este orden
        (espejo de infraestructura_service):
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

    # ------------------------------------------------------------------
    # Casos de uso — estudiantes
    # ------------------------------------------------------------------

    @requiere_escritura
    def matricular(
        self,
        dto: NuevoEstudianteDTO,
        usuario_id: int | None = None,
    ) -> Estudiante:
        """
        Matricula un estudiante nuevo.

        Verifica que el documento no esté duplicado, construye la
        entidad desde el DTO y la persiste.
        """
        estudiante = dto.to_estudiante()
        # Multi-tenant (paso_30): resuelve la institución del scope (o #1 en
        # seed/arranque sin sesión) ANTES de verificar el documento, porque el
        # documento es único POR institución: el mismo documento puede existir
        # en otra institución sin colisionar.
        institucion_id = self._resolver_institucion(estudiante.institucion_id)
        if self._repo.existe_documento(dto.numero_documento, institucion_id=institucion_id):
            raise ValueError(
                f"Ya existe un estudiante con el documento '{dto.numero_documento}'."
            )
        estudiante = estudiante.model_copy(update={"institucion_id": institucion_id})
        estudiante = self._repo.guardar(estudiante)
        self._auditar(
            AccionCambio.CREATE, "estudiantes", estudiante.id,
            None, estudiante.model_dump(mode="json"), usuario_id,
        )
        return estudiante

    @requiere_escritura
    def actualizar(
        self,
        estudiante_id: int,
        dto: ActualizarEstudianteDTO,
        usuario_id: int | None = None,
    ) -> Estudiante:
        """Actualiza los datos de un estudiante existente."""
        estudiante = self._get_estudiante_o_lanzar(estudiante_id)
        datos_ant = estudiante.model_dump(mode="json")
        estudiante_actualizado = dto.aplicar_a(estudiante)
        self._repo.actualizar(estudiante_actualizado)
        self._auditar(
            AccionCambio.UPDATE, "estudiantes", estudiante_id,
            datos_ant, estudiante_actualizado.model_dump(mode="json"), usuario_id,
        )
        return estudiante_actualizado

    def retirar(
        self,
        estudiante_id: int,
        motivo: str | None = None,
        usuario_id: int | None = None,
    ) -> Estudiante:
        """
        Retira un estudiante del establecimiento.

        Lanza ValueError si el estudiante ya está retirado.
        """
        estudiante = self._get_estudiante_o_lanzar(estudiante_id)
        if estudiante.estado_matricula == EstadoMatricula.RETIRADO:
            raise ValueError("El estudiante ya está en estado RETIRADO.")
        datos_ant = estudiante.model_dump(mode="json")
        estudiante_retirado = estudiante.model_copy(
            update={"estado_matricula": EstadoMatricula.RETIRADO}
        )
        self._repo.actualizar_estado_matricula(
            estudiante_id, EstadoMatricula.RETIRADO.value
        )
        self._auditar(
            AccionCambio.UPDATE, "estudiantes", estudiante_id,
            datos_ant, estudiante_retirado.model_dump(mode="json"), usuario_id,
        )
        return estudiante_retirado

    @requiere_escritura
    def asignar_grupo(
        self,
        estudiante_id: int,
        grupo_id: int,
    ) -> Estudiante:
        """
        Asigna o cambia el grupo de un estudiante.

        El trigger de BD registra automáticamente el historial de cambios de grupo.
        """
        estudiante = self._get_estudiante_o_lanzar(estudiante_id)
        self._repo.asignar_grupo(estudiante_id, grupo_id)
        return estudiante.model_copy(update={"grupo_id": grupo_id})

    def _con_scope(self, filtro: FiltroEstudiantesDTO) -> FiltroEstudiantesDTO:
        """
        Inyecta el scope multi-tenant (paso_30) en el filtro de listados.

        Resuelve desde `institucion_actual()`: None (admin / arranque) → sin
        filtro de institución (ve todo); institución → filtra. NO se cae al
        id_por_defecto en listados: admin debe ver todas las instituciones.
        Respeta un institucion_id ya presente en el filtro (caller explícito).
        """
        if filtro.institucion_id is not None:
            return filtro
        from src.services.contexto_tenant import institucion_actual
        return filtro.model_copy(update={"institucion_id": institucion_actual()})

    def listar_por_grupo(
        self,
        grupo_id: int,
        solo_activos: bool = True,
    ) -> list[Estudiante]:
        """
        Retorna todos los estudiantes de un grupo.

        Scope multi-tenant (paso_30): None (admin / arranque) → sin filtro;
        director → su institución.
        """
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_por_grupo(
            grupo_id,
            solo_activos=solo_activos,
            institucion_id=institucion_actual(),
        )

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        """Retorna estudiantes según los filtros indicados (scopeado por tenant)."""
        return self._repo.listar_filtrado(self._con_scope(filtro))

    def listar_resumenes(
        self,
        filtro: FiltroEstudiantesDTO,
    ) -> list[EstudianteResumenDTO]:
        """Retorna la vista resumida de estudiantes para selects (scopeado)."""
        return self._repo.listar_resumenes(self._con_scope(filtro))

    def listar_resumenes_plano(
        self,
        filtro: FiltroEstudiantesDTO,
    ) -> list[dict]:
        """
        Igual que listar_resumenes pero serializado a dicts planos.

        Todos los enums se convierten a strings (mode='json') para que
        la capa de interfaz trabaje con primitivos puros sin conocer
        tipos del dominio.

        Campos por fila:
          id, nombre_completo, documento_display, grupo_id,
          estado_matricula (str), genero (str|None), posee_piar (bool)
        """
        resumenes = self._repo.listar_resumenes(self._con_scope(filtro))
        resultado = []
        for r in resumenes:
            datos = r.model_dump(mode="json")
            resultado.append({
                "id":               datos["id"],
                "nombre_completo":  datos["nombre_completo"],
                "documento_display": datos["documento_display"],
                "grupo_id":         datos.get("grupo_id"),
                "estado_matricula": datos["estado_matricula"],   # str plano
                "genero":           datos.get("genero"),
                "posee_piar":       datos["posee_piar"],
            })
        return resultado

    def get_by_id(self, estudiante_id: int) -> Estudiante:
        """Retorna un estudiante por id. Lanza si no existe."""
        return self._get_estudiante_o_lanzar(estudiante_id)

    def get_para_edicion(self, estudiante_id: int) -> dict:
        """
        Retorna los campos editables de un estudiante como dict plano.

        Convierte todos los enums a sus valores string (mode="json") para
        que la capa de interfaz no necesite conocer ni importar tipos del
        dominio. El dict resultante contiene:
          id, nombre, apellido, genero, grupo_id, posee_piar,
          estado_matricula, nombre_completo, documento_display
        """
        est = self._get_estudiante_o_lanzar(estudiante_id)
        datos = est.model_dump(mode="json")
        # Exponemos solo los campos que la UI necesita para el formulario
        return {
            "id":               datos["id"],
            "nombre":           datos["nombre"],
            "apellido":         datos["apellido"],
            "genero":           datos.get("genero"),          # str | None
            "grupo_id":         datos.get("grupo_id"),        # int | None
            "posee_piar":       datos["posee_piar"],
            "estado_matricula": datos["estado_matricula"],    # str plano
            "nombre_completo":  est.nombre_completo,
            "documento_display": est.documento_display,
        }

    # ------------------------------------------------------------------
    # Casos de uso — PIAR
    # ------------------------------------------------------------------

    @requiere_escritura
    def registrar_piar(
        self,
        dto: NuevoPIARDTO,
        usuario_id: int | None = None,
    ) -> PIAR:
        """
        Registra un PIAR para un estudiante en un año lectivo.

        Lanza ValueError si ya existe un PIAR para ese estudiante y año.
        """
        if self._repo.existe_piar(dto.estudiante_id, dto.anio_id):
            raise ValueError(
                f"Ya existe un PIAR para el estudiante {dto.estudiante_id} "
                f"en el año {dto.anio_id}. Actualice el existente."
            )
        piar = dto.to_piar()
        piar = self._repo.guardar_piar(piar)
        # Marcar al estudiante como poseedor de PIAR
        estudiante = self._get_estudiante_o_lanzar(dto.estudiante_id)
        if not estudiante.posee_piar:
            self._repo.actualizar(
                estudiante.model_copy(update={"posee_piar": True})
            )
        self._auditar(
            AccionCambio.CREATE, "piars", piar.id,
            None, piar.model_dump(mode="json"), usuario_id,
        )
        return piar

    @requiere_escritura
    def actualizar_piar(
        self,
        estudiante_id: int,
        anio_id: int,
        dto: ActualizarPIARDTO,
        usuario_id: int | None = None,
    ) -> PIAR:
        """
        Actualiza un PIAR existente.

        Lanza ValueError si no existe PIAR para ese estudiante y año.
        """
        # Autorización a nivel de objeto (paso_36): el PIAR cuelga de un
        # estudiante; verificamos la pertenencia contra el institucion_id del
        # estudiante leído del repo (lanza OperacionFueraDeInstitucionError si es
        # de otra institución). Si el estudiante no existe, dejamos que el chequeo
        # de "no existe PIAR" de abajo produzca el mensaje habitual.
        est = self._repo.get_by_id(estudiante_id)
        if est is not None:
            from src.services.contexto_tenant import verificar_pertenencia
            verificar_pertenencia(est.institucion_id)
        piar_actual = self._repo.get_piar(estudiante_id, anio_id)
        if piar_actual is None:
            raise ValueError(
                f"No existe PIAR para el estudiante {estudiante_id} "
                f"en el año {anio_id}. Regístralo primero."
            )
        datos_ant = piar_actual.model_dump(mode="json")
        piar_nuevo = dto.aplicar_a(piar_actual)
        piar_nuevo = self._repo.actualizar_piar(piar_nuevo)
        self._auditar(
            AccionCambio.UPDATE, "piars", piar_nuevo.id,
            datos_ant, piar_nuevo.model_dump(mode="json"), usuario_id,
        )
        return piar_nuevo

    def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None:
        """Retorna el PIAR del estudiante para el año indicado."""
        return self._repo.get_piar(estudiante_id, anio_id)

    # ------------------------------------------------------------------
    # Carga masiva CSV
    # ------------------------------------------------------------------

    @requiere_escritura
    def matricular_masivo_csv(
        self,
        filas: list[dict],
        mapa_grupos: dict[str, int],
        usuario_id: int | None = None,
    ) -> MatriculaMasivaResultadoDTO:
        """
        Matricula una lista de estudiantes proveniente de un CSV.

        Args:
            filas:        Lista de dicts con claves del CSV (una por fila).
            mapa_grupos:  Mapeo codigo_grupo → grupo_id para resolver grupos.
            usuario_id:   ID del usuario que realiza la carga (auditoría).

        Returns:
            DTO con totales y lista de errores por fila.
        """
        resultado = MatriculaMasivaResultadoDTO(
            total_procesadas=len(filas),
            exitosas=0,
            fallidas=0,
            errores=[],
        )
        for i, fila in enumerate(filas, start=2):
            num_doc = fila.get("numero_documento", "").strip()
            try:
                codigo_grupo = fila.get("grupo_codigo", "").strip()
                grupo_id     = mapa_grupos.get(codigo_grupo) if codigo_grupo else None
                dto = NuevoEstudianteDTO(
                    tipo_documento=fila.get("tipo_documento", "TI").strip() or "TI",
                    numero_documento=num_doc,
                    nombre=fila.get("nombre", "").strip(),
                    apellido=fila.get("apellido", "").strip(),
                    genero=fila.get("genero", "").strip() or None,
                    grupo_id=grupo_id,
                )
                self.matricular(dto, usuario_id=usuario_id)
                resultado.exitosas += 1
            except Exception as exc:
                resultado.agregar_error(fila=i, dato=num_doc or "?", motivo=str(exc))

        return resultado


__all__ = [
    "EstudianteService",
    # DTOs re-exportados explícitamente para que la capa de interfaz
    # los importe desde el servicio y no desde el dominio directamente.
    "NuevoEstudianteDTO",
    "ActualizarEstudianteDTO",
    "FiltroEstudiantesDTO",
    "NuevoPIARDTO",
    "ActualizarPIARDTO",
]
