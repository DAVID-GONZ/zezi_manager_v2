# Requisitos: backend_18_css_desacoplado

> Ambito: auditar y aislar las dependencias de Quasar/NiceGUI en el CSS
> para verificar que la capa Core es reutilizable fuera de NiceGUI.
>
> Fase 5 del backend. Cierra la Fase 5 (design system portable).
>
> IMPORTA para el split: el informe confirma que transferir es
> copiar, no reescribir, y documenta exactamente que se reescribe.

---

## Auditoria de dependencias

R1: EL SISTEMA DEBE producir un informe `docs/design_system/portability_audit.md`
    que detalle:
    - Archivos CSS core (portables a Vue tal cual).
    - Archivos CSS adapter (requieren reescritura).
    - Selectores que dependen del DOM de Quasar (`.q-*`).
    - Selectores que dependen del DOM de ag-Grid (`.ag-*`).
    - Selectores que dependen del DOM de NiceGUI (`.nicegui-*`).
    - Cantidad de `!important` por archivo y razon de cada uno.

R2: EL informe DEBE cuantificar lineas de CSS por categoria:
    - Core portable: X lineas.
    - Adapter a reescribir: Y lineas.
    - Ratio de portabilidad: X / (X+Y) %.

---

## Verificacion de la frontera Core/Adapter

R3: EL SISTEMA DEBE verificar que `check_design.py` (regla N) sigue
    bloqueando selectores de framework fuera de `styles/adapter/`.

R4: TODA violacion encontrada que no este en la lista de deuda DEBE
    corregirse o documentarse con justificacion.

---

## CSS portable verificado

R5: LOS archivos CSS core DEBEN funcionar en un HTML estatico sin
    NiceGUI, Quasar ni ag-Grid. Verificacion: crear un HTML de test
    que cargue solo `tokens.css` + los archivos core y renderice
    los 18 componentes del catalogo.

R6: EL HTML de test DEBE renderizar correctamente:
    - Badge con las 5 variantes.
    - Button con las 4 variantes.
    - Card y Stat Card.
    - Alert con las 4 variantes.
    - Page Header.
    - Section Panel.
    - Layout basico (sidebar + main).

---

## Recomendaciones para el fork

R7: EL informe DEBE incluir una seccion "Recomendaciones para Vue" con:
    - Que copiar tal cual.
    - Que reescribir y contra que (DOM nativo, headless components).
    - Que eliminar (CSS muerto, overrides de Quasar innecesarios).

---

## Fuera de alcance

- Reescribir el CSS adapter (eso es vue_04/vue_05).
- Eliminar Quasar del proyecto actual.
- Cambiar el CSS core (solo auditarlo).
