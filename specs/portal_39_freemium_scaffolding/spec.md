# portal_39_freemium_scaffolding — Spec (ROADMAP — sin detalle aun)

## Contexto

El diseno de render dual (portal_35..38) deja preparado el terreno para un modelo
**freemium**. Este paso lo materializa: tarjetas de modulos premium visibles pero
bloqueadas, interceptacion de clic hacia una pagina de pricing, y metricas de intencion.

**Estado: roadmap.** No se detalla en esta ronda por decision de David: requiere un
concepto de **plan/tier** que hoy NO existe en el modelo de datos. Ese modelo llega con la
Etapa A de backend (`roadmaps/backend_00_roadmap_sqlalchemy_api` + el trabajo multitenant).
Especificar los requisitos EARS y tareas concretas se hara cuando ese modelo exista, para
no construir sobre un stub que habria que rehacer.

Scope previsto (se concretara al detallar): modelo de plan/tier por institucion (o usuario)
y flag `premium` por modulo/feature; capa visual de bloqueo; interceptor de clic; pagina de
pricing; registro de metricas de intencion.

## Alcance previsto (borrador, no ejecutable aun)

- **Modelo de plan/tier**: por institucion (o usuario) + flag `premium` por modulo/feature,
  derivado del registro `src/domain/modulos.py`.
- **Tarjetas bloqueadas (upselling)**: los modulos premium se muestran con candado /
  opacidad reducida (clase nueva `.portal-card--locked`), no se ocultan.
- **Interceptacion de clic**: al hacer clic en un modulo o sub-tarjeta premium, el enrutador
  NO bloquea con error; despliega un modal o redirige a la pagina interna de "Actualizar
  plan" (Pricing), detallando que se desbloquea.
- **Metricas de intencion**: registrar en BD cada intento de clic premium de un usuario
  gratuito (evento de auditoria/analytics), para priorizar monetizacion.
- **Encapsulado por permisos**: la carga de `ui.card`/`ui.button` premium se envuelve en
  helpers que verifican autenticacion **y** plan/rol al cargar la pagina.

## Requisitos (EARS)

Pendientes de redactar cuando exista el modelo de planes. Este archivo se actualizara de
`roadmap` a spec ejecutable en ese momento.

## Dependencias

- Modelo de planes / tiers (Etapa A backend — `backend_00`). **Bloqueante**.
- `portal_38_mini_dashboards` — la capa de bloqueo se aplica sobre las tarjetas/sub-tarjetas.
