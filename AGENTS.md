# AGENTS.md — Mapa de navegación para agentes

> Punto de entrada para cualquier agente que trabaje en este repositorio.
> NO es una biblia de reglas: es un **mapa**. Lee solo lo que necesites, cuando lo necesites.

---

## 1. Antes de empezar (obligatorio)

1. Ejecuta `./init.sh` — si falla, **para**. No toques código.
2. Lee `step_list.json` — identifica el paso activo (`in_progress`) o el siguiente pendiente.
3. Lee `progress/current.md` — estado de la última sesión.
4. Si el paso tiene `"sdd": true`, lee el spec en `specs/<paso>/` antes de implementar.

---

## 2. Mapa del repositorio

| Archivo / carpeta | Qué contiene | Cuándo leerlo |
|---|---|---|
| `step_list.json` | Los 10 pasos de migración con estado | Siempre, al empezar |
| `progress/current.md` | Estado vivo de la sesión actual | Siempre, al empezar |
| `progress/history.md` | Bitácora append-only | Si necesitas contexto de sesiones anteriores |
| `specs/<paso>/` | `requirements.md` + `design.md` + `tasks.md` para el paso | Antes de implementar |
| `docs/architecture.md` | Qué es Clean Architecture para este proyecto; regla de dependencias | Antes de implementar cualquier cosa |
| `docs/conventions.md` | Reglas concretas de Python/Pydantic/NiceGUI para este repo | Antes de escribir código |
| `docs/verification.md` | Criterio de done por paso; cómo demostrar que funciona | Antes de declarar done |
| `CHECKPOINTS.md` | Criterios objetivos de "estado correcto" por capa | Para auto-evaluarte |
| `.claude/agents/` | Definiciones de subagentes | Si orquestas trabajo |
| `src/` | Código de la aplicación | Para implementar |
| `tests/` | Tests automáticos | Para verificar |

---

## 3. Reglas duras

- **Un paso a la vez.** No mezcles cambios de pasos distintos en la misma sesión.
- **No declares `done` sin tests verdes.** `./init.sh` debe pasar al 100%.
- **No saltes la aprobación humana.** El leader detiene el flujo cuando el spec está listo (`spec_ready`) y espera que David apruebe antes de continuar.
- **Documenta en `progress/current.md`** mientras trabajas, no al final.
- **Si no sabes algo, busca en `docs/`** antes de inventarlo.
- **Si el archivo fuente no existe o está vacío**, documenta el bloqueo en `progress/current.md` y para.

---

## 4. Flujo de trabajo por paso

```
pending → [spec_author] → spec_ready → ⏸ DAVID → in_progress → [implementer → reviewer] → done
```

1. El leader detecta el primer paso `pending`.
2. Si el paso tiene `"sdd": true`, lanza `spec_author`, que crea `specs/<paso>/{requirements,design,tasks}.md` y marca `spec_ready`.
3. **Pausa.** David lee el spec y aprueba o pide cambios.
4. Leader cambia a `in_progress` y lanza `implementer`.
5. Implementer ejecuta `tasks.md` una a una, marcándolas `[x]`.
6. Reviewer verifica según `CHECKPOINTS.md` y `docs/verification.md`.
7. Si aprueba → `done`, resumen a `progress/history.md`.

**Pasos con `"sdd": false`** (los más mecánicos, ej. Paso 0 y 1) no pasan por spec: el leader lanza `implementer` directamente con las instrucciones del paso.

---

## 5. Cierre de sesión

1. Ejecuta `./init.sh` — todo verde.
2. Marca el paso como `done` en `step_list.json` si corresponde.
3. Mueve el resumen de `progress/current.md` a `progress/history.md`.
4. Vacía `progress/current.md` dejando solo la plantilla.

---

## 6. Si te bloqueas

- Relee la sección relevante de `docs/`.
- Si la herramienta falla de forma inesperada, **no inventes workarounds**: documenta el bloqueo en `progress/current.md` con el error exacto y para la sesión.
