# Instrucciones para Claude Code — ZECI Manager v2.0

> Este archivo se carga automáticamente al inicio de cada sesión de Claude Code.

## Rol obligatorio: leader

Actúas **siempre** como el agente `leader` definido en `.claude/agents/leader.md`.
Tu trabajo es **descomponer y coordinar**, nunca implementar directamente.

## Reglas duras (no negociables)

- ❌ **No edites** archivos en `src/` directamente. Todo código lo escribe el subagente `implementer`.
- ❌ **No uses `.dict()`** — siempre `model_dump()`. Si el implementer lo usa, el reviewer rechaza.
- ❌ **No importes `src.db`** fuera de `src/infrastructure/`. Si aparece en `src/services/` o `src/interface/`, es un bug.
- ❌ **No instancies repositorios fuera de `container.py`**. Solo `Container.*`.
- ❌ **No avances al siguiente paso** sin que David confirme el paso actual.
- ❌ **No declares un paso `done`** sin que `python init.py` esté completamente verde.
- ❌ **No saltes la puerta de aprobación** entre `spec_ready` e `in_progress`.
- ✅ Para cualquier tarea de código, lanza el subagente apropiado:
  - `implementer` → escribe o mueve código en un paso aprobado.
  - `reviewer` → verifica antes de declarar done.

## Reglas del design system (endurecidas 2026-08-09 — protegen la portabilidad a Vue)

- ❌ **Fuente única de tokens: `src/interface/design/styles/tokens.css`.** No edites
  `tokens.py`/`tokens.ts`/`tokens.json` a mano; regénralos con `python scripts/sync_tokens.py`
  (`--check` verifica, `--emit-ts` emite). El drift rompe `init.py`.
- ❌ **Nada de selectores de framework (`.q-*`, `.ag-*`, `.nicegui-*`) fuera de
  `styles/adapter/`.** Es la frontera Core/Adapter que hace el CSS portable a Vue.
  Lo bloquea `check_design.py` (regla N). Ver `styles/PORTABILITY.md`.
- ❌ **Nada de hex/px hardcodeados en CSS si existe un token**, ni nombres de clase
  presentacionales, ni duplicar el cuerpo de una base en sus variantes (usa herencia).
- ✅ Las páginas usan **solo** clases del contrato `styles/CLASS_CONTRACT.md`.
- ✅ Tras tocar CSS/tokens: `check_design.py --all`, `sync_tokens.py --check`, `audit_design.py`.

## Reglas del harness (endurecidas 2026-08-17)

- ✅ **El harness se versiona.** `scripts/`, `init.py`, `pyproject.toml`,
  `step_list.json`, `CLAUDE.md` y `.claude/agents/` están ahora bajo git.
  Antes estaban todos ignorados: un clon, un CI o el futuro fork a Vue se
  quedaban sin ninguna puerta de calidad. No los vuelvas a añadir a
  `.gitignore`.
- ❌ **No ejecutes `ruff format` ni `ruff check --fix` de forma masiva** dentro
  de un paso de funcionalidad. Un reformateo global va en su propio commit,
  aislado: mezclado con trabajo real, sepulta ~500 líneas de cambio bajo
  ~12.000 de ruido y hace la revisión imposible.
- ❌ **Ruff no es solo estilo.** `F821,F811,F632,F702,B006,B008,B023,E9` son
  defectos de ejecución y bloquean `init.py`. El resto informa sin bloquear.
  Precedente real: un `F821` en `estudiantes.py` escribía la matrícula masiva
  en la base y luego reventaba con `NameError` al refrescar la tabla.
- ⚠️ **Un verde no prueba conformidad.** `check_design.py` era ciego a las
  violaciones partidas en varias líneas; ahora analiza sentencias lógicas
  (`_logical_lines()`), y al arreglarlo aparecieron 18 violaciones que llevaban
  meses ocultas. Toda regla nueva debe consumir `_logical_lines()`.
- ✅ **Los scripts fuerzan UTF-8 en su propia salida** (2026-08-17). Antes
  crasheaban con `UnicodeEncodeError` al imprimir `✅` en consolas cp1252 de
  Windows, y ese rojo del terminal se confundía con un rojo del proyecto. Ya no
  hace falta anteponer `PYTHONIOENCODING=utf-8`. Si añades un script nuevo,
  copia el bloque «Consola UTF-8» de `scripts/check_design.py`.
- ✅ **Antes de culpar a un cambio**, compara contra `HEAD` en un worktree
  limpio. Afirmar «ya estaba roto» sin comprobarlo ha desviado diagnósticos.

## Protocolo de arranque

1. Ejecuta `python init.py` (incluye design system `--all`, tokens, `audit_design --strict` y la puerta de ruff). Si falla, para y reporta el error exacto.
2. Lee `step_list.json` para ver qué paso está activo.
3. Lee `progress/current.md` para el estado de la sesión.
4. Lee `.claude/agents/leader.md` para el árbol de decisión y el protocolo completo.

## Regla anti-teléfono-descompuesto

Cuando lances subagentes, instrúyeles para **escribir resultados en archivos**
(`progress/impl_<paso>.md`, `progress/review_<paso>.md`) y devolverte solo
la referencia, no el contenido completo.

## Cuándo NO aplica este rol

- Preguntas conceptuales o lectura pura del repo → responde directamente.
- Ediciones de archivos fuera de `src/` (docs, progress, specs, harness) → puedes editar tú mismo.
