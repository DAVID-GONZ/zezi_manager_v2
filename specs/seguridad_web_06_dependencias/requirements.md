# Requisitos: Auditoría de dependencias (seguridad_web_06)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Proceso (sin código Python nuevo; integración en CI es Config)
> **Depende de:** ningún otro spec
> **Bloquea a:** S11 (CI/CD seguro integra este check)

## Contexto del problema

Cada paquete en `requirements.txt` es superficie de ataque. CVEs conocidos en
dependencias directas o transitivas pueden ser explotados sin ningún cambio en el
código propio. Este check toma menos de 30 minutos la primera vez y debe ejecutarse
antes de cada deploy.

## Requisitos

R1: EL PROYECTO DEBE tener un `requirements.txt` con versiones exactas pinneadas
    para todas las dependencias directas. No se aceptan rangos abiertos (`>=`, `~=`,
    `*`) en producción. Las versiones exactas garantizan builds reproducibles.

R2: EL PROYECTO DEBE ejecutar `pip-audit` (o `safety check`) contra el
    `requirements.txt` antes de cada deploy y antes de añadir cualquier dependencia
    nueva. Cualquier CVE con severidad ALTA o CRÍTICA bloquea el deploy.

R3: LOS CVEs con severidad MEDIA o BAJA DEBEN estar documentados en un archivo
    `docs/seguridad_dependencias.md` con: nombre del paquete, versión afectada, CVE ID,
    severidad, motivo de aceptación o plan de mitigación, y fecha de revisión.

R4: EL PROYECTO DEBE eliminar dependencias no utilizadas. Antes del primer deploy,
    se DEBE ejecutar `pip-check` o equivalente para verificar consistencia del entorno,
    y revisar manualmente que todos los paquetes instalados son usados en `src/`.

R5: LAS DEPENDENCIAS DE DESARROLLO (pytest, black, etc.) DEBEN estar separadas en
    `requirements-dev.txt`. El entorno de producción NO instala dependencias de
    desarrollo.

R6: EL CHECK DE AUDITORÍA DEBE integrarse en el pipeline de CI (S11) como paso
    previo al deploy. Un pipeline que no corra `pip-audit` no puede hacer deploy.

R7: CADA VEZ QUE SE AÑADA O ACTUALICE UNA DEPENDENCIA, el `requirements.txt` DEBE
    actualizarse en el mismo commit. No se aceptan dependencias instaladas en el
    entorno de producción que no estén en el lockfile.

## Criterio de done

- `pip-audit -r requirements.txt` no reporta CVEs de severidad Alta o Crítica.
- CVEs aceptados están documentados en `docs/seguridad_dependencias.md`.
- `requirements.txt` y `requirements-dev.txt` son archivos distintos.
- El check está integrado en el pipeline de CI (puede verificarse después de S11).
