# Requisitos: CI/CD seguro (seguridad_web_11)

> **Nivel:** N1 — Primer mes en producción
> **Dificultad:** Config (configuración del pipeline; minimal código Python)
> **Depende de:** S06 (pip-audit integrado aquí), S02 (secretos fuera del repo)
> **Bloquea a:** nada, pero habilita automatización de todos los demás checks

## Contexto del problema

El pipeline de CI/CD es la última puerta antes de producción y también es un vector
de ataque: secretos en logs, dependencias comprometidas en la cadena de build, o
código con tests rojos llegando a prod. Este spec define los gates mínimos que
el pipeline DEBE tener para ser considerado seguro.

## Requisitos

### Secretos en el pipeline

R1: EL PIPELINE NUNCA DEBE imprimir el valor de variables de entorno secretas en
    logs de CI. Los runners de CI (GitHub Actions, GitLab CI, etc.) DEBEN tener los
    secretos configurados como "masked" o equivalente.

R2: LOS SECRETOS DE PRODUCCIÓN NO DEBEN estar en el repositorio de CI/CD config
    (`.github/workflows/*.yml`, `.gitlab-ci.yml`, etc.) en texto claro. DEBEN
    referenciarse como variables del entorno del CI (p. ej. `${{ secrets.DB_URL }}`).

R3: LOS LOGS DE CI DEBEN revisarse periódicamente para detectar fugas accidentales
    de secretos. Herramientas como `trufflehog` o `gitleaks` DEBEN ejecutarse en el
    pipeline sobre cada PR.

### Gates de calidad obligatorios

R4: EL PIPELINE DEBE ejecutar los siguientes checks en este orden antes de cualquier
    deploy a staging o producción, y el deploy DEBE abortarse si cualquiera falla:
    1. `pip-audit -r requirements.txt` — sin CVEs Alto/Crítico (S06).
    2. `python init.py` — suite completa de tests verde.
    3. Verificación de headers de seguridad en staging (smoke test de S04).

R5: EL PIPELINE NO DEBE deployar código de una rama que no haya pasado por PR review.
    El branch de producción (`main` o `prod`) DEBE tener protección de rama activada:
    sin push directo, mínimo 1 aprobación.

R6: CADA BUILD DE PRODUCCIÓN DEBE generar un artefacto reproducible. La misma versión
    del código con el mismo `requirements.txt` DEBE producir el mismo entorno instalado.

### Trazabilidad

R7: CADA DEPLOY A PRODUCCIÓN DEBE registrar: commit hash, timestamp, quién lo disparó,
    y resultado de los gates (PASS/FAIL). Este registro DEBE persistir al menos 6 meses.

R8: EL PIPELINE DEBE crear un tag de git automáticamente en cada deploy exitoso a
    producción (requerido por S10 — rollback de código).

### Entorno de staging

R9: DEBE existir un entorno de staging que sea lo más idéntico posible a producción:
    misma versión de Python, misma configuración de proxy, mismo backend de BD (Postgres),
    secretos diferentes pero del mismo tipo. Los deploys a prod siempre pasan por
    staging primero.

R10: LAS VARIABLES DE ENTORNO DE STAGING NUNCA DEBEN ser iguales a las de producción.
     Especialmente `DATABASE_URL` debe apuntar a una BD diferente.

## Criterio de done

- `git push --force` al branch de producción está bloqueado por protección de rama.
- `pip-audit` y `python init.py` son pasos obligatorios del pipeline (el pipeline
  falla si se omiten).
- Logs de CI no contienen valores de secretos (verificable inspeccionando un run reciente).
- El registro de deploys existe y tiene al menos el commit hash y timestamp.
