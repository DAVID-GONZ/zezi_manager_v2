# Tasks: Página única de horarios y dedup (paso_18_horarios_unificado)

> Fase 1 (dedup) primero y verificada antes de la fase 2 (unificación). No se toca el
> render de la parrilla (R11).

## Fase 1 — Deduplicación (bajo riesgo)
- [x] T1: Exportar `_opciones_eje` desde `parrilla_widget.py` (`__all__`) y eliminar
          las copias locales en `horarios.py` (`_parrilla_opciones_eje`) y
          `horario_generar.py` (`_opciones_eje`); ajustar llamadas.
  Verifica: `python scripts/check_imports.py --layer interface` ✅
- [x] T2: Eliminar el código muerto `_cargar_bloques` de `horarios.py`.
  Verifica: `python -m pytest -q` ✅
- [x] T3: Eliminar el doble registro `@ui.page`: quitar los decoradores de
          `horarios.py` y `horario_generar.py`; dejar el registro único con guard en
          `main.py`. Extendido `check_page_decorators` con `# page-delegate` exemption.
  Verifica: `python init.py` ✅

## Fase 2 — Página única
- [x] T4: Crear el hub con control segmentado semántico (Preparar/Generar/Visualizar/
          Editar) y `_s["seccion"]`, con visibilidad por rol.
  `horarios_hub.py` — 2210 líneas. `hub_refreshable` despacha por sección.
  Verifica: `python init.py` ✅ Design system ✅
- [x] T5: Integrar las secciones Visualizar y Editar (desde `horarios.py`) y Generar
          (desde `horario_generar.py`), reutilizando los handlers existentes.
  Estado unificado `_s` con prefijos `gen_*` / `doc_*`. 6 refreshables top-level.
  Verifica: `python scripts/check_imports.py --layer interface` ✅
- [x] T6: Integrar la sección Preparar (panel + accesos de captura de paso_17).
  Sección Preparar con links a disponibilidad, salas, plantillas, generador.
  Verifica: `python init.py` ✅
- [x] T7: Compatibilidad de rutas en `main.py` (`/horarios`→visualizar respetando
          `?escenario=`; `/academico/generar-horario`→generar; nueva `/academico/horarios`).
  Verifica: `python init.py` ✅

## Cierre
- [x] T8: Verificación completa y no-regresión.
  Resultado: `python init.py` → ✅ ENTORNO OK — 920 passed, 1 skipped (2026-06-14)
  Verifica: `python init.py` ✅ · `python -m pytest -q` ✅
