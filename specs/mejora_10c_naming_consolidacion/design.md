# Design: mejora_10c — Consolidación de convención de nombres (opcional / baja prioridad)

> **Origen:** auditoría del design system (2026-08-09), `scripts/audit_design.py`.
> **Tipo:** higiene. **Baja prioridad** — hacer solo si sobra margen antes del fork.
> **Prerrequisitos:** ninguno.

---

## Problema

El sistema es 88.5% semántico, pero conviven varias convenciones de prefijo
(`andes-*`, plano, `u-*`, dominio `asis-*`/`tablero-*`) y un puñado de nombres
**presentacionales** que describen apariencia, no rol (`audit_design.py` los lista):
`text-xs-meta`, y similares. No es un bug; es coherencia. Un rename masivo (`andes-*`)
sería caro y riesgoso (migrar cientos de `.classes()`), con poco retorno.

## Objetivo (mínimo, sin rename masivo)

1. **Renombrar solo los nombres presentacionales con reemplazo semántico claro** y baja
   frecuencia de uso (empezando por `text-xs-meta` → `meta-text`), migrando sus usos.
2. **Fijar y documentar UNA convención** en `CLASS_CONTRACT.md` para clases nuevas:
   - Componentes: `componente` + `componente--variante` (kebab, sin prefijo `andes-`).
   - Utilidades semánticas: prefijo `u-`.
   - No introducir nombres presentacionales nuevos (lo vigila `audit_design.py`).
3. **NO** tocar el prefijo `andes-*` histórico ni los prefijos de dominio (`asis-`, `tablero-`,
   `parrilla-`): son coherentes dentro de su contexto y migrarlos no aporta.

> Alternativa consciente: si se prefiere, el prefijo `andes-*` puede quedar como el
> namespace oficial del design system y documentarse como tal — también resuelve la
> inconsistencia. La decisión la toma David; este spec asume "sin prefijo para clases nuevas".

## Estrategia de rename seguro

Por cada clase a renombrar:
1. `grep` de todos los usos (CSS + `.classes()`/f-strings en `.py`).
2. Renombrar en CSS y migrar cada uso.
3. `check_design.py --all` (regla G confirma que no quedó ninguna clase indefinida).

---

## Verificación

- `python scripts/audit_design.py` → la lista de "presentacionales" baja (los renombrados salen).
- `python scripts/check_design.py --all` y `python init.py` en verde.
- `CLASS_CONTRACT.md` incluye la sección "Convención de nombres para clases nuevas".
