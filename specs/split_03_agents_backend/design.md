# split_03_agents_backend — Diseno

## Estructura de archivos

```
avedra-backend/
├── .claude/
│   ├── agents/
│   │   ├── leader.md
│   │   ├── implementer.md
│   │   ├── reviewer.md
│   │   └── spec_author.md
│   └── settings.json
├── CLAUDE.md
└── scripts/
    └── generar_estructura.py   # adaptado

avedra-shared-contracts/
└── CLAUDE.md
```

## Diferencias clave vs. mono-repo actual

| Aspecto | Mono-repo (actual) | Backend (post-split) |
|---|---|---|
| Scope del implementer | `src/` (todo) | `src/` (sin interface/) + `app/` |
| Reglas de design system | Aplican | Eliminadas |
| init.py | check_design + ruff + tests | ruff + tests + contract validation |
| Reviewer chequea | CSS tokens, imports, tests | API contracts, imports, tests |

## leader.md — Adiciones

Regla de contrato API:
```
Cuando un paso modifique un endpoint, schema o enum:
1. Regenerar OpenAPI: python scripts/generate_openapi.py
2. Copiar a avedra-shared-contracts
3. Anotar en progress/current.md: "CONTRACT_CHANGED: <que cambio>"
```

## implementer.md — Reglas adaptadas

- Scope: `src/domain/`, `src/infrastructure/`, `src/services/`,
  `src/reference/`, `app/`, `tests/`, `scripts/`
- model_dump() obligatorio (sin .dict())
- No import src.db fuera de infrastructure
- No instanciar repos fuera de container.py
- Sin reglas de CSS/tokens/design system

## reviewer.md — Checklist adaptado

1. Correcccion funcional (tipos, logica, tests)
2. Puerta de imports (no src.db fuera de infra, no repos fuera de container)
3. Puerta anti AI-slop (ver repo_split_00_pasos.md seccion 5.4)
4. Validacion de contrato API (si el paso toca endpoints)
5. ruff sin defectos de ejecucion (F821, F811, etc.)

## generar_estructura.py — Cambios

- Eliminar de NOISE_DIRS: `roadmaps/`, `specs/`, `progress/`
  (ya no existen en el backend)
- Agregar `app/` al arbol principal
- Mantener CACHE_DIRS y consola UTF-8
- Simplificar NOISE_DIRS a solo `logs/`

## CLAUDE.md de shared-contracts

Contenido minimo. Explica que es un repo de solo lectura, que los archivos
se generan desde avedra-backend, y el flujo:
backend genera -> shared-contracts recibe -> frontend regenera cliente.

No necesita subagentes. David o CI lo actualiza.
