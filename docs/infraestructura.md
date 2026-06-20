# Capa de Infraestructura (Adaptadores Generales)

Este documento describe la arquitectura y los detalles de implementación de los adaptadores de la capa de infraestructura que **no están relacionados con la base de datos**. Mientras que los repositorios (`src/infrastructure/db/repositories/`) manejan la persistencia y se documentan en `repositorio.md`, esta sección cubre los adaptadores responsables de la autenticación, el contexto de la aplicación, y las exportaciones a formatos externos.

La capa de infraestructura implementa los **Puertos (Interfaces)** definidos por el dominio, interactuando con bibliotecas de terceros sin acoplar la lógica de negocio a dichas herramientas.

## 1. Módulo: Autenticación (`src/infrastructure/auth/`)

Proporciona implementaciones para el manejo seguro de credenciales de usuario.

### Adaptador: `BcryptAuthService`
Implementa la interfaz `IAuthenticationService`.

- **Responsabilidad:** Asegurar las contraseñas del sistema utilizando el algoritmo de hashing `bcrypt` adaptativo.
- **Detalles técnicos:** 
  - Utiliza la librería `passlib` con soporte para encriptación de múltiples rondas (`bcrypt`).
  - Provee métodos `hashear_password` y `verificar_password`.
  - Aisla por completo la criptografía del `UsuarioService` de la capa de dominio.
- **Relación con Frameworks:** Es agnóstico a NiceGUI/FastAPI; opera exclusivamente con strings, lo que permite su testeo unitario aislado.

## 2. Módulo: Contexto de Estado (`src/infrastructure/context/`)

Proporciona implementaciones seguras y tipadas para manejar la sesión del usuario actual y el estado de la UI (User Interface) que el framework subyacente maneja por debajo.

### Adaptador: `AppStateContextAdapter`
Una clase especializada en envolver el diccionario de sesión o almacenamiento local.

- **Responsabilidad:** Actuar como puente entre el framework asíncrono (ej. `app.storage.user` en NiceGUI) y los servicios de la aplicación que requieran conocer quién es el actor de una solicitud.
- **Patrón:** Funciona como un _Facade_ para evitar que los controladores/páginas inyecten diccionarios crudos a los servicios. Facilita obtener de manera segura propiedades tipadas del usuario autenticado actual.

### Adaptador: `ContextInitializer`
Responsable del "bootstrap" o inyección del estado inicial necesario para que los componentes interactivos de la aplicación web funcionen. 

## 3. Módulo: Exportadores de Documentos (`src/infrastructure/exporters/`)

Responsable de tomar datos estructurados generados por los servicios (`DTOs`, Listas, Diccionarios) y renderizarlos en documentos binarios para su descarga final.

Implementan la interfaz de dominio `IExporterService`.

### Adaptador: `ExcelExporter`
Genera hojas de cálculo (`.xlsx`).
- **Responsabilidad:** Crear planillas de notas, listas de asistencia y exportaciones de configuraciones complejas hacia Excel.
- **Dependencias Ocultas:** Encapsula totalmente el uso de la librería `openpyxl`. Las directivas de estilo, anchos de columna y colores de celdas viven aquí y no contaminan el `InformeService`.

### Adaptador: `PdfExporter`
Genera documentos formateados en PDF.
- **Responsabilidad:** Construir los boletines de periodo, actas finales y consolidados académicos en formato inalterable y listo para imprimir.
- **Dependencias Ocultas:** Encapsula el uso de herramientas como `reportlab` o equivalentes. 

### Adaptador: `NullExporter` (Mock / Fallback)
Un exportador especial implementado siguiendo el patrón Null Object.
- **Responsabilidad:** Proporcionar una implementación segura que no revienta la aplicación si una librería pesada (como `reportlab`) no se puede instalar en un ambiente restringido. Lanza excepciones amistosas (`RuntimeError` descriptivos) que la UI puede atrapar para mostrar mensajes claros al usuario en lugar de colapsos genéricos del servidor.

## 4. Repositorio SIEE (`src/infrastructure/db/repositories/sqlite_siee_repo.py`)

Adaptador para el **Sistema Institucional de Evaluación** (SIEE). *(Nuevo — Junio 2026)*

- **Responsabilidad:** Persiste y lee la `ConfiguracionSIEE` (modo de evaluación y porcentaje de autonomía docente por año) y las categorías institucionales (`Categoria` con `es_institucional=True`).
- **Implementa:** `ISIEERepository` del dominio.
- **Consumido por:** `EvaluacionService` para determinar si la institución opera en modo SIEE centralizado o en modo libre por docente.

---

## Resumen de Interacciones

Ningún componente del Dominio invoca métodos de estas clases directamente. En tiempo de arranque (`container.py`), las clases de infraestructura son instanciadas e inyectadas a los Servicios como si fuesen sus respectivas interfaces (`IAuthenticationService`, `IExporterService`), adhiriendo estrictamente al Principio de Inversión de Dependencias (DIP).
