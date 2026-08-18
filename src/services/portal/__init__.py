"""
src/services/portal/
=====================
Implementaciones concretas de `src.domain.portal_provider.PortalProvider`.

Regla de este paquete: los providers NO importan `Container`. Reciben sus
dependencias como callables inyectados desde `container.py`, de modo que se
puedan testear sin arrancar el contenedor. No añadir imports eager aquí:
`container.py` importa cada módulo perezosamente.
"""
