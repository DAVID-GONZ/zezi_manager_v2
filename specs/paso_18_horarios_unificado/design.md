# Diseño: Página única de horarios y dedup (paso_18_horarios_unificado)

> Se ejecuta **después** de paso_17 y paso_19 (consume sus piezas). Riesgo medio:
> toca dos páginas grandes y funcionales; por eso se separa en dedup (bajo riesgo)
> y unificación (mayor riesgo), entregables por separado.

## 1. Dedup (fase 1, bajo riesgo)

- **`_opciones_eje` (R1)**: exportar la función ya existente en
  `parrilla_widget.py:34` en su `__all__`. En `horarios.py` borrar
  `_parrilla_opciones_eje` (línea ~779) y en `horario_generar.py` borrar
  `_opciones_eje` (línea ~917); ambas importan la de `parrilla_widget`.
  Cuidado: la firma es `(datos, perspectiva)`; verificar que las llamadas locales
  coincidan (lo hacen).
- **`_cargar_bloques` muerto (R2)**: eliminar la función de `horarios.py:197`
  (confirmado sin llamadas).
- **Registro doble `@ui.page` (R3)**: decidir UNA fuente de verdad. Recomendado:
  mantener el registro en `main.py` (que ya lleva el guard de auth) y **eliminar los
  decoradores `@ui.page` de los archivos de página** (`horarios.py:100`,
  `horario_generar.py:77`). Las funciones `*_page()` quedan como funciones normales
  invocadas desde `main.py`. Así no hay rutas sin guard.

Verificación de la fase 1: `python init.py` verde + tests; el comportamiento de
ambas páginas idéntico al actual.

## 2. Página única (fase 2)

Nueva página `src/interface/pages/academico/horarios_hub.py` (o renombrar
`horarios.py`) con un **control segmentado de secciones** (`_segmento`, mismo patrón
ya usado) y estado `_s["seccion"]` ∈ {`preparar`, `generar`, `visualizar`, `editar`}.

```
┌─ Horarios ───────────────────────────────────────────────┐
│ [ Preparar ] [ Generar ] [ Visualizar ] [ Editar ]        │  ← _segmento semántico
├───────────────────────────────────────────────────────────┤
│ (contenido_refreshable según _s["seccion"], filtrado por  │
│  permisos de rol)                                          │
└───────────────────────────────────────────────────────────┘
```

- **Preparar (R5)**: panel de validación de paso_19 + accesos a captura de paso_17
  (disponibilidad, límites, salas, plantilla). Solo escritura para roles autorizados.
- **Generar (R6)**: mueve el cuerpo de `horario_generar.py` (config + ejecutar +
  resultado + preview). La lógica del motor ya está; aquí solo se reubica el render.
- **Visualizar (R7)**: parrilla en lectura, reutilizando `render_parrilla` /
  `render_tablero_maestro` (sin `on_celda_click`).
- **Editar (R8)**: la edición actual de `/horarios` (con `on_celda_click` y
  `puede_escribir`).

Permisos (R9): el conjunto de secciones visibles se calcula de `ctx.usuario_rol`.
Lectores: solo Visualizar.

## 3. Compatibilidad de rutas (R10)

`main.py` mantiene `/horarios` y `/academico/generar-horario`, pero ambas invocan la
página única seleccionando la sección inicial:
- `/horarios` → sección `visualizar` (o `editar` si tiene permiso) — respeta
  `?escenario=` como hoy.
- `/academico/generar-horario` → sección `generar`.
Opcional: una ruta canónica nueva `/academico/horarios`.

## 4. Archivos afectados
- `src/interface/pages/academico/parrilla_widget.py` — solo `__all__` (R11).
- `src/interface/pages/academico/horarios.py` — dedup + se convierte en/llama a hub.
- `src/interface/pages/academico/horario_generar.py` — su cuerpo de UI se integra como
  sección "Generar".
- `main.py` — registro único con guard; rutas viejas → sección inicial.

## 5. Manejo de errores / riesgo
- Hacer la **fase 1 (dedup) primero y verificarla** antes de la unificación.
- Conservar nombres de estado `_s[...]` y handlers existentes al mover código, para
  minimizar regresiones.
- No fusionar los dos diccionarios `_s` a ciegas: prefijar claves por sección si hay
  colisión (`gen_*`, `vis_*`).

## 6. Preguntas abiertas
1. ¿Renombrar a `/academico/horarios` como canónica y dejar las viejas como alias, o
   mantener `/horarios` como principal?
2. ¿"Preparar" como sección de esta página o como página propia enlazada? (afecta a
   cuánto crece el hub).
