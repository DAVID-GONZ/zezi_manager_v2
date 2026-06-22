# paso_38 — Página de Diagnóstico/Herramientas de admin + reubicar "Ver como"

## Contexto y decisión (David)

Dos ajustes de UX en el área admin:
1. `/diagnostico` existe y está protegida (admin-only, registrada vía `registrar_pagina` en paso_35) pero es **una página inline trivial en `main.py` y está oculta del NAV** (huérfana, solo accesible escribiendo la URL).
2. **"Ver como"** no necesita ser una ruta (es un diálogo), pero **no debe ser una tarjeta de acceso rápido en el dashboard**. Debe vivir en un sitio más apropiado: la **vista de diagnóstico/herramientas de admin**.

Decisión: convertir `/diagnostico` en una **página de herramientas de plataforma** (diagnóstico del Container + lanzador "Ver como"), **surgirla en el NAV** bajo Administración (admin-only), y **quitar la tarjeta "Ver como" del dashboard**. La acción "Ver como" **por fila** en `/admin/usuarios` se mantiene como entrada principal.

## Tareas

### T1 — Página `diagnostico` propiamente dicha
- Crear `src/interface/pages/admin/diagnostico.py` con `diagnostico_page()` usando `app_layout(ctx, contenido, page_titulo="Diagnóstico", page_icono=..., mostrar_contexto=False)`. Guarda: la aplica el wrapper de ruta (admin), pero incluir el `if not ctx → /login` mínimo como las demás páginas.
- Contenido:
  - **Diagnóstico del Container:** mover aquí lo que hoy hace la página inline de `main.py` (`Container.diagnostico()` → estado por servicio, OK/error con clases del design system, sin colores quemados — usar `status_badge`/clases existentes).
  - **Lanzador "Ver como":** mover el selector de doble filtrado (institución → usuario) de `inicio.py` (`_abrir_selector_ver_como`) a esta página (botón "Ver como…" que abre el diálogo). Reutilizar la lógica existente; respetar design system (NO importar `src.domain.models`; DTOs vía servicio).

### T2 — Registro + NAV
- `main.py`: registrar `/diagnostico` vía `registrar_pagina("/diagnostico", diagnostico_page, roles={Rol.ADMIN})` apuntando a la nueva página; **eliminar la definición inline** `pagina_diagnostico` de `registrar_rutas_internas` (dejar ahí solo `/health` u otras rutas FastAPI no-NiceGUI).
- `NAV_ITEMS` (`layout.py`): añadir un ítem **"Diagnóstico"** (icono p.ej. `monitor_heart`/`build`/`troubleshoot`) bajo el grupo **Administración**, ruta `/diagnostico`. Su visibilidad la deriva `roles_de_ruta` (= admin) — NO duplicar la lista de rol. Mantener la invariante de 6 grupos raíz del NAV (es un child, no un grupo nuevo).

### T3 — Quitar la tarjeta "Ver como" del dashboard
- `inicio.py` (rama admin): eliminar la **tarjeta de acceso rápido "Ver como…"** del dashboard. Mantener las demás (Auditoría, Usuarios). Si `_abrir_selector_ver_como` queda solo usado por la nueva página, moverlo allí (no dejar código muerto en `inicio.py`).
- La acción "Ver como" **por fila** en `/admin/usuarios` se mantiene SIN cambios (entrada principal).

### T4 — Verificación
- `python init.py` VERDE (baseline 1178 passed, 1 skipped; corregir fallout). Ajustar `test_navitems` (ahora `/diagnostico` está en el NAV y en el registro de rutas) y los tests `(ruta,rol)` si listan rutas del NAV. check_design sobre la página nueva e `inicio.py` exit 0; check_imports interface exit 0.
- Test: `/diagnostico` sigue admin-only (rechaza no-admin), aparece en el NAV solo para admin, y el dashboard admin ya no tiene la tarjeta "Ver como".
- `progress/impl_paso_38.md`.

## criterio_done
`/diagnostico` es una página de herramientas de admin (diagnóstico del Container + lanzador "Ver como") surgida en el NAV bajo Administración (admin-only, vía el registro central); el dashboard admin ya no tiene la tarjeta "Ver como" (la acción por fila en Usuarios se mantiene); sin código muerto; `python init.py` verde y check_design/check_imports verdes.
