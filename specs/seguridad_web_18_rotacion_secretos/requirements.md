# Requisitos: Rotación periódica de secretos (seguridad_web_18)

> **Nivel:** N4 — Continuo / Operacional
> **Dificultad:** Proceso (sin código nuevo; procedimiento operacional)
> **Depende de:** S02 (secretos bien configurados desde el inicio)
> **Sin fecha de "done":** práctica permanente

## Contexto del problema

Los secretos tienen una vida útil. Un `JWT_SECRET` o password de base de datos que
no se rota nunca acumula riesgo: puede haber sido comprometido sin saberlo, puede
aparecer en un leak de otro servicio si el mismo secreto se reutilizó, o puede estar
almacenado en un lugar que ya no está bajo control (laptop antigua, backup sin cifrar,
log de hace 2 años). La rotación periódica limita la ventana de exposición.

## Requisitos

R1: EL PROCEDIMIENTO DE ROTACIÓN DEBE estar documentado paso a paso en
    `docs/operaciones.md` para cada secreto: `JWT_SECRET`, `STORAGE_SECRET`,
    password de usuario de Postgres, y cualquier API key de servicios externos.

R2: `JWT_SECRET` DEBE rotarse como mínimo anualmente o inmediatamente si se
    sospecha compromiso. La rotación invalida todos los tokens JWT activos; los
    usuarios de la API deberán re-autenticarse. Documentar el impacto y comunicarlo.

R3: `STORAGE_SECRET` (clave de firma de cookies NiceGUI) DEBE rotarse como mínimo
    anualmente. La rotación invalida todas las sesiones activas; los usuarios de la
    web deberán hacer login de nuevo.

R4: EL PASSWORD DEL USUARIO DE POSTGRES DEBE rotarse como mínimo anualmente.
    El procedimiento DEBE permitir la rotación sin downtime: actualizar el secreto
    en el gestor de secretos → reiniciar la app → verificar conexión.

R5: CUANDO SE ROTA UN SECRETO POR SOSPECHA DE COMPROMISO, la rotación DEBE
    ocurrir en menos de 1 hora desde la detección. El procedimiento de emergencia
    DEBE estar documentado separado del procedimiento de rotación periódica.

R6: NUNCA REUTILIZAR UN SECRETO ROTADO. Los secretos anteriores DEBEN eliminarse
    del gestor de secretos o marcarse como revocados.

R7: EL CALENDARIO DE ROTACIÓN DEBE revisarse y ejecutarse aunque no haya incidentes.
    Se recomienda agendar la rotación en el mismo mes cada año, documentando la fecha
    de la última rotación en `docs/operaciones.md`.

## Criterio de done (continuo)

- `docs/operaciones.md` tiene el procedimiento de rotación para cada secreto.
- Existe registro de la última rotación de cada secreto.
- El procedimiento de emergencia está documentado y es conocido por al menos
  dos personas con acceso al servidor.
