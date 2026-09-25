# Requisitos: Historial de cambios en la ficha de negocio (obs_10)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgo
> B11.
> **Depende de:** `obs_09`, que aporta el diff, el catálogo de etiquetas y la
> resolución de actores.
> **Alcance:** un componente reutilizable del design system, su presenter, una
> política RBAC y cuatro puntos de enganche. No cambia el esquema ni el
> repositorio.

## El defecto que este paso cierra

La pregunta que un colegio hace primero —*«¿quién cambió esto y cuándo?»*— solo
se puede responder hoy navegando a `/admin/auditoria`, con rol de admin, y
filtrando a ciegas por nombre de tabla y número de registro. Desde la ficha de
la observación, de la nota, del estudiante o del usuario no hay ningún camino.

`listar_cambios_por_registro(tabla, registro_id)` existe en el puerto
(`auditoria_repo.py:121`), en la implementación SQLite (`:316`) y en los dobles
de test, **sin ningún consumidor**. Devuelve además los cambios en orden
cronológico ascendente, que es justo el orden en que se lee un historial.

## Decisión de alcance: quién ve el historial

El historial de un registro expone quién tocó qué y cuándo. No es información
de administración de plataforma: es información institucional, y su lector
natural es el equipo directivo del colegio. Este paso introduce la política
RBAC que `obs_11` reutilizará.

---

R1: EL SISTEMA DEBE exponer una política pura
    `src/domain/policies/rbac_auditoria.py` con
    `puede_ver_historial(actor_rol) -> bool`, siguiendo el patrón de
    `rbac_usuarios.py` y `rbac_convivencia.py`.

R2: `puede_ver_historial` DEBE conceder acceso a `admin`, `director` y
    `coordinador`, y denegarlo al resto. La política se consulta **tanto** en
    el servicio (enforcement real) **como** en la vista (gating del control),
    para que no diverjan.

R3: EL SISTEMA DEBE exponer `AuditoriaService.historial_de(tabla, registro_id,
    scope)` que devuelva los cambios del registro en orden cronológico, cada
    uno ya resuelto a un `DetalleCambioDTO`.

R4: `historial_de` DEBE aplicar el `TenantScope` recibido: un director no puede
    obtener el historial de un registro de otra institución.

R5: EL SISTEMA DEBE ofrecer un componente reutilizable del design system,
    `historial_cambios(items)`, que renderice una línea temporal de cambios con
    fecha, actor, acción y el diff campo a campo de cada entrada.

R6: EL COMPONENTE DEBE ser de presentación pura: recibe una lista de DTOs, no
    llama a `Container` ni a ningún servicio.

R7: EL COMPONENTE DEBE usar exclusivamente clases del contrato
    `styles/CLASS_CONTRACT.md`. Cualquier clase nueva se incorpora al contrato
    y su CSS vive en `styles/components/`, nunca en `styles/adapter/`, para
    que el componente sea portable al fork Vue.

R8: CUANDO un registro no tenga cambios auditados, el componente DEBE mostrar
    un estado vacío explicativo, no una lista en blanco.

R9: EL SISTEMA DEBE enganchar el historial en cuatro fichas: observación de
    convivencia, planilla de notas, estudiante y usuario. El control solo se
    renderiza cuando `puede_ver_historial(rol)` es cierto.

R10: EL HISTORIAL DEBE ser de solo lectura. No se ofrece deshacer, restaurar ni
     editar desde él.

R11: LA CONSULTA del historial NO DEBE ejecutarse al renderizar la ficha: se
     lanza al abrir el historial, para no añadir coste a pantallas que hoy no
     lo pagan.

R12: EL PRESENTER del historial NO DEBE contener reglas de negocio. El diff, la
     etiqueta de tabla y la resolución de actores vienen del servicio.

## Criterio de done

- Un coordinador abre una observación, pulsa «Historial» y ve la secuencia de
  ediciones con quién y cuándo, y qué campos cambiaron en cada una.
- Un profesor no ve el control de historial en ninguna de las cuatro fichas.
- Un registro recién creado muestra una sola entrada (su creación).
- Un registro sin huella muestra el estado vacío explicativo.
- Abrir la ficha sin pulsar «Historial» no dispara ninguna consulta a
  `audit_log`.
- `python scripts/init.py` completamente verde, incluidos `check_design.py
  --all` y `audit_design.py`.
