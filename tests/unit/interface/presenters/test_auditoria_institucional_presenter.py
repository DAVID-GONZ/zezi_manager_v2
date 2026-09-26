"""
Tests de AuditoriaInstitucionalPresenter (obs_11, T6).

Llama al presenter real (no reimplementa la lógica) y verifica:
  - El scope devuelve el institucion_id del constructor.
  - El estado no contiene las claves prohibidas («institucion_id»,
    «sin_institucion»), que son las que haría posible un cruce de tenant.
  - construir_filtro() siempre emite institucion_id == scope y
    sin_institucion == False, independientemente de los filtros del usuario.
"""
from __future__ import annotations

from src.interface.presenters.institucion.auditoria_presenter import (
    AuditoriaInstitucionalPresenter,
)


def test_scope_devuelve_el_institucion_id_del_constructor() -> None:
    """R4: el scope proviene del constructor y no cambia."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=7)
    assert presenter.scope == 7  # R4


def test_estado_no_contiene_clave_institucion_id() -> None:
    """R5: la clave «institucion_id» no existe en el estado (la UI no puede mutar el scope)."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=1)
    assert "institucion_id" not in presenter.estado, (
        "«institucion_id» no debe existir en el estado del presenter institucional"
    )


def test_estado_no_contiene_clave_sin_institucion() -> None:
    """R5: la clave «sin_institucion» no existe en el estado."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=1)
    assert "sin_institucion" not in presenter.estado, (
        "«sin_institucion» no debe existir en el estado del presenter institucional"
    )


def test_construir_filtro_fuerza_institucion_id_del_scope() -> None:
    """R4: construir_filtro siempre emite institucion_id == scope, incluso sin filtros activos."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=3)
    filtro = presenter.construir_filtro(por_pagina=50)
    assert filtro.institucion_id == 3, (
        f"construir_filtro debe forzar institucion_id=3, obtuvo {filtro.institucion_id!r}"
    )


def test_construir_filtro_nunca_emite_sin_institucion() -> None:
    """R5: construir_filtro siempre emite sin_institucion=False."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=2)
    filtro = presenter.construir_filtro(por_pagina=50)
    assert filtro.sin_institucion is False, (
        f"construir_filtro debe emitir sin_institucion=False, obtuvo {filtro.sin_institucion!r}"
    )


def test_construir_filtro_scope_no_cambia_con_filtros_usuario() -> None:
    """R4: los filtros que modifica el usuario no alteran el scope."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=5)
    presenter.set_rango("2025-01-01", "2025-12-31")
    presenter.set_usuario("42")
    presenter.set_tabla("estudiantes")
    filtro = presenter.construir_filtro(por_pagina=50)
    assert filtro.institucion_id == 5, (
        "el scope debe mantenerse en 5 aunque el usuario haya modificado otros filtros"
    )
    assert filtro.sin_institucion is False


def test_scope_es_solo_lectura_no_en_estado() -> None:
    """El scope no es mutable desde fuera ni desde el estado."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=9)
    # El scope es una propiedad, no una clave del estado
    assert presenter.scope == 9
    # Aunque alguien intente escribir en el estado, el scope no cambia
    presenter.estado["_intento_trampa"] = 999
    assert presenter.scope == 9


def test_nombre_actor_fallback_sin_actores() -> None:
    """nombre_actor devuelve «—» cuando no hay usuario_id ni snapshot."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=1)

    class _FakeCambio:
        usuario_id = None
        usuario = None

    assert presenter.nombre_actor(_FakeCambio()) == "—"


def test_nombre_actor_usa_snapshot_cuando_no_hay_mapa() -> None:
    """nombre_actor usa el username del snapshot cuando el mapa de actores está vacío."""
    presenter = AuditoriaInstitucionalPresenter(institucion_id=1)

    class _FakeCambio:
        usuario_id = 10
        usuario = "jdoe"

    resultado = presenter.nombre_actor(_FakeCambio())
    assert resultado == "jdoe"
