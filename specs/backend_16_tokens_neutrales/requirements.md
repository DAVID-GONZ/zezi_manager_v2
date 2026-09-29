# Requisitos: backend_16_tokens_neutrales

> Ambito: establecer `tokens.json` como fuente canonica del design system,
> siguiendo el formato W3C Design Tokens. `sync_tokens.py` genera
> `tokens.css` + `tokens.ts` + `tokens.py` DESDE el JSON. Invierte el
> flujo actual (CSS -> Python) para que el formato neutral sea la fuente.
>
> Fase 5 del backend. Paralelo con la Fase 3; no tiene dependencias de
> la API REST.
>
> IMPORTA para el split: `tokens.json` viaja a `avedra-shared-contracts`
> como fuente unica de tokens consumible por backend y frontend.

---

## Fuente canonica JSON

R1: EL SISTEMA DEBE tener un archivo `tokens.json` como fuente unica
    de verdad de los tokens del design system. Formato W3C Design Tokens
    (Community Group Draft, estructura de 3 niveles).

R2: LA estructura de `tokens.json` DEBE distinguir formalmente:
    - **Primitivos:** valores crudos (colores hex, px, rem, pesos de fuente).
    - **Semanticos:** proposito (color-primary, spacing-md, font-body).
    - **Componente:** especificos de componente (button-bg, input-border).

R3: `tokens.json` DEBE contener TODOS los tokens que hoy existen en
    `tokens.css` (187 variables al 2026-09-09). Ninguno se pierde.

---

## Generacion de derivados

R4: `sync_tokens.py` DEBE generar desde `tokens.json`:
    - `tokens.css` — variables CSS custom properties (formato actual).
    - `tokens.ts` — constantes TypeScript exportadas.
    - `tokens.py` — constantes Python (formato actual).
    Cada derivado DEBE ser identico al actual (salvo orden/formato).

R5: `sync_tokens.py --check` DEBE verificar que los derivados estan
    sincronizados con `tokens.json`. Falla si hay drift. Se ejecuta
    en `init.py`.

R6: `sync_tokens.py --emit-ts` DEBE generar `tokens.ts` y `tokens.json`
    (para el frontend Vue). El JSON ya existe como fuente; el TS se
    genera desde el.

---

## Compatibilidad

R7: `tokens.css` generado DEBE ser identico en contenido al actual.
    Los componentes CSS, las paginas NiceGUI y el theme.py no deben
    romperse. Diferencias cosmeticas (orden, whitespace) son aceptables
    si la verificacion visual pasa.

R8: `tokens.py` generado DEBE mantener las mismas constantes que hoy
    existen. Los imports existentes de `tokens.py` no se rompen.

---

## Verificacion

R9: `check_design.py --all` DEBE pasar tras el cambio.

R10: `audit_design.py` DEBE pasar tras el cambio.

R11: Un test DEBE verificar round-trip: leer `tokens.json`, generar
     los 3 derivados, verificar que los derivados son identicos.

---

## Fuera de alcance

- Refactorizar los tokens existentes (renombrar, eliminar, reorganizar).
  Eso se hara en Fase 1 del fork Vue (vue_02_tokens).
- Adoptar herramientas externas de tokens (Style Dictionary, Tokens Studio).
  El script propio es suficiente para el volumen actual.
