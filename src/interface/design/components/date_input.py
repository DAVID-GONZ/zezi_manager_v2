"""
date_input.py — Componentes de fecha del design system Andes Minimal v2.
=========================================================================

Provee dos componentes reutilizables que reemplazan el patrón suelto
`ui.input(...).props("type=date")` repartido por las páginas:

  - `date_input(...)`       → una sola fecha (calendario nativo), formato
                              "YYYY-MM-DD".
  - `date_range_input(...)` → rango Desde/Hasta con presets rápidos
                              (Hoy, Últimos 7 días, Últimos 30 días,
                              Periodo activo) y validación `desde <= hasta`.

Reglas del design system respetadas:
  - Sólo clases CSS definidas en `styles/components/date_input.css`.
  - `ThemeManager.icono()` para iconos (nunca `ui.icon`).
  - Sin `.style()` estático sin `# DYNAMIC`, sin colores quemados.
  - Sin imports de dominio ni de servicios (capa de presentación pura).

Formato de fecha: SIEMPRE strings "YYYY-MM-DD" (o None / "" para vacío),
que es exactamente lo que produce el input nativo `type=date` del navegador
y lo que ya consumían las páginas migradas (`date.fromisoformat`).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from nicegui import ui


def _hoy_iso() -> str:
    return date.today().isoformat()


def date_input(
    label: str = "Fecha",
    *,
    value: str | None = None,
    on_change: Callable[[str | None], None] | None = None,
    placeholder: str = "YYYY-MM-DD",
    clases: str = "",
    classes: str = "",
) -> ui.input:
    """
    Campo de una sola fecha con date-picker nativo (calendario del navegador).

    Args:
        label:       Etiqueta visible del campo.
        value:       Valor inicial "YYYY-MM-DD" o None/"".
        on_change:   Callback(valor) donde `valor` es "YYYY-MM-DD" o None.
        placeholder: Texto de ayuda cuando está vacío.
        clases:      Clases CSS adicionales para el wrapper del campo.
        classes:     Alias en inglés de `clases` (compatibilidad).

    Returns:
        El `ui.input` creado (para que el llamador pueda actualizar `.value`).
    """
    extra = (clases + " " + classes).strip()
    wrap_classes = ("ds-date-field " + extra).strip()

    def _emit(raw) -> None:
        if on_change is None:
            return
        val = (raw or "").strip() or None
        on_change(val)

    with ui.element("div").classes(wrap_classes):
        inp = (
            ui.input(label=label, placeholder=placeholder, value=value or "",
                     on_change=lambda e: _emit(e.value))
            .props("type=date dense outlined")
            .classes("ds-date-input andes-input")
        )
    return inp


def date_range_input(
    *,
    label_desde: str = "Desde",
    label_hasta: str = "Hasta",
    desde: str | None = None,
    hasta: str | None = None,
    on_change: Callable[[str | None, str | None], None] | None = None,
    periodo_desde: str | None = None,
    periodo_hasta: str | None = None,
    presets: bool = True,
    clases: str = "",
) -> dict:
    """
    Rango de fechas Desde/Hasta con presets rápidos y validación.

    Presets disponibles:
      - "Hoy"             → desde = hasta = hoy
      - "Últimos 7 días"  → desde = hoy-6, hasta = hoy
      - "Últimos 30 días" → desde = hoy-29, hasta = hoy
      - "Periodo activo"  → desde = `periodo_desde`, hasta = `periodo_hasta`
                            (sólo se muestra si ambos se proporcionan; el
                            componente NO consulta servicios — el llamador
                            inyecta el rango del periodo activo).

    Validación: si `desde > hasta`, se muestra un mensaje de error y NO se
    propaga el cambio inválido al callback.

    Args:
        desde / hasta:  Valores iniciales "YYYY-MM-DD" o None.
        on_change:      Callback(desde, hasta) con strings "YYYY-MM-DD" o None.
        periodo_desde / periodo_hasta:
                        Rango del periodo activo para el preset (opcional).
        presets:        Si False, no se renderiza la barra de presets.
        clases:         Clases CSS adicionales para el contenedor raíz.

    Returns:
        dict con las referencias útiles:
          {"desde": ui.input, "hasta": ui.input, "error": ui.label}
        para que el llamador pueda actualizar valores externamente.
    """
    estado: dict = {"desde": desde or None, "hasta": hasta or None}
    refs: dict = {}

    root_classes = ("ds-daterange " + clases).strip()

    def _validar() -> bool:
        d, h = estado["desde"], estado["hasta"]
        if d and h and d > h:
            refs["error"].set_text("La fecha 'Desde' no puede ser posterior a 'Hasta'.")
            return False
        refs["error"].set_text("")
        return True

    def _emitir() -> None:
        if not _validar():
            return
        if on_change is not None:
            on_change(estado["desde"], estado["hasta"])

    def _set_desde(raw) -> None:
        estado["desde"] = (raw or "").strip() or None
        _emitir()

    def _set_hasta(raw) -> None:
        estado["hasta"] = (raw or "").strip() or None
        _emitir()

    def _aplicar_preset(d: str | None, h: str | None) -> None:
        estado["desde"] = d
        estado["hasta"] = h
        refs["desde"].value = d or ""
        refs["hasta"].value = h or ""
        _emitir()

    with ui.element("div").classes(root_classes):
        with ui.element("div").classes("ds-daterange-fields"):
            refs["desde"] = (
                ui.input(label=label_desde, placeholder="YYYY-MM-DD",
                         value=estado["desde"] or "",
                         on_change=lambda e: _set_desde(e.value))
                .props("type=date dense outlined")
                .classes("ds-date-input andes-input")
            )
            ui.label("–").classes("ds-daterange-sep")
            refs["hasta"] = (
                ui.input(label=label_hasta, placeholder="YYYY-MM-DD",
                         value=estado["hasta"] or "",
                         on_change=lambda e: _set_hasta(e.value))
                .props("type=date dense outlined")
                .classes("ds-date-input andes-input")
            )

        if presets:
            with ui.element("div").classes("ds-date-presets"):
                ui.label("Rápido:").classes("ds-date-presets-label")
                _preset_chip("Hoy", lambda: _aplicar_preset(_hoy_iso(), _hoy_iso()))
                _preset_chip(
                    "Últimos 7 días",
                    lambda: _aplicar_preset(
                        (date.today() - timedelta(days=6)).isoformat(), _hoy_iso()
                    ),
                )
                _preset_chip(
                    "Últimos 30 días",
                    lambda: _aplicar_preset(
                        (date.today() - timedelta(days=29)).isoformat(), _hoy_iso()
                    ),
                )
                if periodo_desde and periodo_hasta:
                    _preset_chip(
                        "Periodo activo",
                        lambda: _aplicar_preset(periodo_desde, periodo_hasta),
                    )

        refs["error"] = ui.label("").classes("ds-date-error")

    return refs


def _preset_chip(texto: str, on_click: Callable[[], None]) -> None:
    """Chip-botón de preset. Div clicable con clase del design system."""
    with ui.element("div").classes("ds-date-preset").on("click", lambda: on_click()):
        ui.label(texto)


__all__ = ["date_input", "date_range_input"]
