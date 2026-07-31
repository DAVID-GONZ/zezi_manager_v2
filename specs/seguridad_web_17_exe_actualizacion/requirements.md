# Requisitos: Actualización segura del .exe (seguridad_web_17)

> **Nivel:** N3 — Con PWA / WebView2 (Fase 2 del backend_00)
> **Dificultad:** Código-Alto (firma de binarios, verificación de integridad)
> **Depende de:** backend_11_build_exe (.exe construido y distribuido)
> **Relacionado con:** S16 (WebView2 en producción)

## Contexto del problema

Si el mecanismo de auto-update del .exe descarga y ejecuta un binario sin verificar
su integridad y autenticidad, un atacante que comprometa el servidor de distribución
(o intercepte la descarga) puede ejecutar código arbitrario en la máquina del usuario.
Este es un ataque de supply chain. El .exe tiene acceso al filesystem local del usuario,
por lo que el impacto es total.

## Requisitos

R1: CADA BINARIO DISTRIBUIDO DEBE estar firmado digitalmente con un certificado de
    firma de código (Code Signing Certificate) válido. En Windows, esto activa la
    verificación de SmartScreen y previene el aviso "Publisher unknown".

R2: EL MECANISMO DE AUTO-UPDATE DEBE descargar el nuevo binario y verificar su
    firma digital ANTES de ejecutarlo. Si la verificación falla, la actualización
    DEBE abortarse y notificar al usuario. Nunca ejecutar un binario no verificado.

R3: EL CANAL DE DISTRIBUCIÓN (servidor o CDN) DEBE servir los binarios solo por
    HTTPS. La app DEBE verificar el certificado TLS del servidor de distribución
    (no desactivar la verificación SSL).

R4: EL SERVIDOR DE DISTRIBUCIÓN DEBE publicar un manifiesto de versiones (JSON)
    firmado con la misma clave que los binarios. El manifiesto incluye: versión,
    URL de descarga, hash SHA-256 del binario. La app verifica el hash tras la
    descarga antes de la verificación de firma.

R5: EL PROCESO DE BUILD QUE GENERA EL .EXE DEBE ejecutarse en un entorno controlado
    (CI/CD con runners efímeros), no en la máquina de desarrollo local de David.
    El binario en producción nunca proviene de un build manual.

R6: LOS RELEASES DEBEN ser trazables: cada binario tiene un commit hash de git
    asociado. Un usuario puede verificar qué código Python está en su .exe instalado.

R7: LA APP DEBE notificar al usuario cuando hay una actualización disponible y
    pedir confirmación antes de descargar e instalar. No actualizar silenciosamente
    sin consentimiento del usuario.

## Criterio de done

- El .exe está firmado (verificable con `sigcheck` en Windows o el Administrador de certificados).
- El proceso de update verifica el hash SHA-256 antes de ejecutar el nuevo binario.
- El build del .exe ocurre en el CI, no localmente (el pipeline incluye el paso de firma).
