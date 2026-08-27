"""
src/interface/pages/convivencia/_shared_observacion_form.py
============================================================
Helper compartido para el diálogo de creación de ObservacionPeriodo.

Consumidores:
  - observaciones.py  → llama con la lista completa del multi-select
  - notas_convivencia.py → llama con [sel_estudiante_id] (un solo estudiante)

La lógica de construcción del DTO, iteración por estudiantes y manejo de
errores vive aquí para evitar duplicación. Los consumidores sólo pasan el
contexto, la lista de IDs, las asignaciones del grupo y el callback de éxito.

Regla de capas:
  No importa nada de src.domain.models.* directamente.
  Los DTOs se acceden a través del módulo de servicios.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from container import Container
from src.interface.design.components import (
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.services.convivencia_service import NuevaObservacionDTO

logger = logging.getLogger("SHARED_OBS_FORM")


def abrir_crear_observacion_dialog(
    *,
    ctx,
    estudiante_ids: list[int],
    periodo_id: int,
    asignaciones: list,
    on_success: Callable[[int, int], None],
    plantilla_id: int | None = None,
    texto_prefill: str = "",
    categoria_id_prefill: int | None = None,
    nombre_unico: str | None = None,
) -> None:
    """
    Abre el diálogo de creación de ObservacionPeriodo.

    Args:
        ctx:                  SessionContext del usuario activo.
        estudiante_ids:       IDs de los estudiantes destino.
                              Un elemento desde Notas, varios desde Observaciones.
        periodo_id:           ID del periodo activo (ya conocido por el llamador).
        asignaciones:         Lista de AsignacionInfo del grupo para el dropdown de asignatura.
        on_success:           Callback (exitos: int, errores: int) → None.
                              Se invoca sólo cuando al menos una observación se guardó.
        plantilla_id:         Si se indica, usa registrar_observacion_desde_plantilla.
        texto_prefill:        Texto inicial del campo texto.
        categoria_id_prefill: Categoría pre-seleccionada en el dropdown.
        nombre_unico:         Nombre legible del estudiante cuando len(estudiante_ids)==1.
                              Si no se provee y es selección única, se muestra el ID.
    """
    if not estudiante_ids:
        toast_warning("No hay estudiantes destino para la observación.")
        return
    if not asignaciones:
        toast_warning("No hay asignaturas disponibles para el grupo activo.")
        return

    # Opciones de asignatura: {asignatura_id: nombre} — sin duplicados por periodo
    opciones_asig: dict[int, str] = {}
    for a in asignaciones:
        aid = getattr(a, "asignatura_id", None)
        if aid is not None and aid not in opciones_asig:
            opciones_asig[aid] = getattr(a, "asignatura_nombre", "")

    # Índice para resolver asignatura_id+periodo → asignacion_id al guardar
    _asig_index = {
        (getattr(a, "asignatura_id", None), getattr(a, "periodo_id", None)): getattr(a, "asignacion_id", None)
        for a in asignaciones
    }

    # Opciones de categoría: {id: nombre}
    try:
        cats = Container.convivencia_service().listar_categorias(solo_activas=True)
        opciones_cat = {getattr(c, "id", None): getattr(c, "nombre", "") for c in cats}
    except Exception as exc:
        logger.warning("Error cargando categorias: %s", exc)
        opciones_cat = {}

    if len(estudiante_ids) == 1:
        subtitulo = nombre_unico if nombre_unico else f"Estudiante #{estudiante_ids[0]}"
    else:
        subtitulo = f"Se aplicará a {len(estudiante_ids)} estudiantes seleccionados."

    campos = [
        {
            "key": "asignatura_id",
            "label": "Asignatura",
            "tipo": "select",
            "opciones": opciones_asig,
            "requerido": True,
        },
        {
            "key": "categoria_id",
            "label": "Categoría",
            "tipo": "select",
            "opciones": opciones_cat,
            "valor": categoria_id_prefill,
            "requerido": True,
        },
        {
            "key": "texto",
            "label": "Texto de la observación",
            "tipo": "textarea",
            "placeholder": "Máximo 2000 caracteres...",
            "valor": texto_prefill,
            "requerido": True,
        },
        {
            "key": "es_publica",
            "label": "Incluir en el boletín",
            "tipo": "checkbox",
            "valor": True,
        },
    ]

    # Captura por valor para que la closure no comparta estado entre aperturas
    _plantilla_id = plantilla_id
    _estudiante_ids = list(estudiante_ids)
    _periodo_id = periodo_id

    def _on_submit(datos: dict) -> bool | None:
        asignatura_id = datos.get("asignatura_id")
        categoria_id = datos.get("categoria_id")
        texto = str(datos.get("texto", "")).strip()
        es_publica = bool(datos.get("es_publica", True))

        if not texto:
            toast_warning("El texto de la observación es requerido.")
            return False
        if not categoria_id:
            toast_warning("Selecciona una categoría.")
            return False
        if not asignatura_id:
            toast_warning("Selecciona una asignatura.")
            return False

        asignacion_id = _asig_index.get((asignatura_id, _periodo_id))
        if not asignacion_id:
            toast_warning("No se encontró asignación para esa asignatura en el periodo activo.")
            return False

        exitos = 0
        errores = 0
        svc = Container.convivencia_service()

        for est_id in _estudiante_ids:
            try:
                dto = NuevaObservacionDTO(
                    estudiante_id=int(est_id),
                    asignacion_id=int(asignacion_id),
                    periodo_id=int(_periodo_id),
                    texto=texto,
                    categoria_id=int(categoria_id),
                    es_publica=es_publica,
                )
                if _plantilla_id:
                    svc.registrar_observacion_desde_plantilla(
                        dto, _plantilla_id, ctx.usuario_id, ctx.usuario_rol
                    )
                else:
                    svc.registrar_observacion(dto, ctx.usuario_id, ctx.usuario_rol)
                exitos += 1
            except PermissionError as exc:
                toast_warning(f"Sin permiso (id={est_id}): {exc}")
                errores += 1
            except ValueError as exc:
                toast_warning(f"Validación: {exc}")
                errores += 1
            except Exception as exc:
                logger.error("Error creando obs est=%s: %s", est_id, exc, exc_info=True)
                errores += 1

        if exitos > 0:
            msg = (
                "Observación guardada."
                if exitos == 1
                else f"Observaciones guardadas ({exitos} de {len(_estudiante_ids)})."
            )
            toast_success(msg)
            on_success(exitos, errores)
            return None

        toast_error(f"No se pudo guardar ninguna observación ({errores} error(es)).")
        return False

    form_dialog(
        titulo="Nueva observación",
        subtitulo=subtitulo,
        campos=campos,
        on_submit=_on_submit,
        texto_submit="Guardar",
        max_width="max-w-lg",
    )


__all__ = ["abrir_crear_observacion_dialog"]
