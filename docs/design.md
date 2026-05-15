# Sistema de Diseño: Andes Minimal v2

El directorio `src/interface/design/` contiene la implementación del sistema de diseño **Andes Minimal v2** para la interfaz de **ZECI Manager v2.0**. Este sistema está construido sobre NiceGUI (versión 3.x) y proporciona una experiencia de usuario consistente, tipada, minimalista y responsiva.

## Arquitectura del Sistema de Diseño

El sistema de diseño se compone de los siguientes elementos principales:

### 1. Tokens de Diseño (`tokens.py`)
Centraliza las constantes de diseño para su uso en Python (utilizado cuando no es posible o conveniente usar CSS puro, como en configuraciones de AG Grid o cálculos en tiempo de ejecución). Asegura la consistencia entre Python y CSS.
- **Colors**: Paleta base (Primarios, Secundarios, Semánticos, Neutros, Navegación).
- **AsistenciaColors**: Colores semánticos asociados a estados de asistencia (Presente, Falta Justificada, Falta Injustificada, Retraso, Excusa).
- **DesempenoColors**: Colores semánticos para los niveles del sistema institucional de evaluación (Bajo, Básico, Alto, Superior).
- **Icons**: Nombres de **Material Symbols Rounded** centralizados (ej. `Icons.DASHBOARD`, `Icons.EDIT`) para evitar *magic strings* en el código.
- **Spacing & Layout**: Variables numéricas de espaciado y dimensiones de la estructura (ej. ancho del sidebar).

### 2. Gestor de Tema (`theme.py`)
El `ThemeManager` es el punto central que inyecta la configuración visual en el framework de NiceGUI y maneja el renderizado complejo de iconos.
- **Inyección de CSS**: A través del método `ThemeManager.aplicar()`, inyecta el contenido de `styles.css` y el *meta viewport* en el `<head>` de la aplicación usando `ui.add_head_html(..., shared=True)`. Este paso es mandatorio y se realiza una sola vez en el ciclo de vida de la aplicación, preferiblemente en el *entrypoint* (`main.py`) antes de invocar `ui.run()`.
- **Renderizado de Iconos Material Symbols**: NiceGUI 3.x no maneja de forma nativa la variabilidad completa (peso, relleno, grado) de las fuentes Material Symbols Rounded. Para solucionarlo, el método `ThemeManager.icono(...)` encapsula esta lógica. Renderiza el icono utilizando un componente `ui.html()` inyectando los atributos *font-variation-settings* (ej. `'FILL' 1, 'wght' 300, 'opsz' 24`). Soporta configuración de tamaño, color por variable CSS y clases adicionales.
- **Soporte Nativo**: Implementa la lógica para ajustar el color de fondo (`background_color`) de la ventana base en caso de que la aplicación se ejecute en modo escritorio nativo mediante `pywebview`.

### 3. Estilos Globales (`styles.css`)
Actúa como la base canónica del sistema visual. A diferencia de un diseño acoplado por utilidades, Andes Minimal v2 centraliza los estilos fundamentales:
- **Variables CSS (`:root`)**: Más de 60 variables CSS nativas que mapean 1 a 1 con `tokens.py`. Incluye variables de colores de la marca, dominios específicos de la app (asistencia, desempeño escolar), escalas tipográficas predefinidas, espaciados sistemáticos y sombras.
- **Reset y Overrides**: Inicializa el diseño base (`box-sizing`) y elimina *paddings* intrusivos que NiceGUI inyecta por defecto a través de `.nicegui-content`. Configura también la tipografía principal (`Inter`) con un *fallback* a tipografías del sistema de forma global.
- **Clases Estructurales y de UI**:
  - **Botones (`.btn-primary`, `.btn-secondary`, etc.)**: Define transiciones de color fluidas en `:hover` y alturas estandarizadas.
  - **Cards y Tablas (`.andes-card`, `.andes-table`)**: Define bordes, sombras de componentes y estilos de filas que reaccionan de manera táctil a los *hovers*.
  - **Componentes Complejos (`.andes-sidebar`, `.andes-topbar`)**: Controla las reglas de anclaje flotante (*fixed*), *scrolls* internos, y transiciones suaves para interacciones (como la expansión del sidebar).
  - **Badges y Alertas (`.badge-*`, `.andes-alert-*`)**: Clases semánticas de un solo propósito para colorear distintivos y mensajes de validación o dominios de negocio (ej. `.badge-P` inyecta estilos para Asistencia Presente).
  - **Feedback Visual**: Implementa los bordes delineados en *:focus-visible* para potenciar la accesibilidad, estilos para *scrollbars* e inyecta animaciones *skeleton* asincrónicas (`.andes-skeleton`).

### 4. Layout Principal (`layout.py`)
Provee la envoltura base para todas las páginas autenticadas mediante la función `app_layout`:
- **Sidebar**: Menú lateral de navegación. Su contenido se genera dinámicamente según la constante `NAV_ITEMS`, filtrando las opciones disponibles según el rol del usuario en la sesión.
- **Topbar**: Barra de control superior. Muestra el título de la vista actual y un bloque de perfil que contiene el nombre del usuario, su rol y el botón de cierre de sesión.
- **Contenido Dinámico**: El cuerpo principal recibe y ejecuta un *callable* (el contenido de la página) asegurando que esté envuelto dentro del contenedor del layout principal.

### 5. Componentes Reutilizables (`components/`)
La carpeta `components` aloja elementos modulares de UI construidos puramente con componentes de NiceGUI y clases de CSS de Andes Minimal v2. Estos componentes evitan la duplicación de código en las vistas y garantizan consistencia visual:
- **`base_form.py`**: Estructuras de formulario uniformes.
- **`confirm_dialog.py` / `confirmation_card.py`**: Diálogos modales y tarjetas para acciones críticas (ej. confirmar borrado).
- **`context_bar.py`**: Barras de herramientas que agrupan filtros, búsqueda y acciones globales por pantalla.
- **`data_table.py`**: Implementaciones encapsuladas de tablas de datos, a menudo *wrappers* sobre `ui.aggrid` estilizados con el tema.
- **`page_header.py`**: Componente de encabezado estandarizado para iniciar cada vista.
- **`performance_indicator.py` / `stat_card.py`**: Elementos analíticos para tableros de control (KPIs).
- **`status_badge.py`**: Etiquetas (badges) visuales que implementan lógicas de colores de los tokens (ej. `badge_asistencia`, `badge_desempeno`).

## Ejemplo de Uso en Vistas

El diseño está pensado para que los desarrolladores front-end puedan componer interfaces rápidamente sin preocuparse por los detalles de estilos.

```python
from nicegui import ui
from src.interface.design.theme import ThemeManager
from src.interface.design.layout import app_layout
from src.interface.design.components import page_header

@ui.page("/mi-pagina")
def mi_pagina_view():
    def contenido():
        # 1. Utilizar un componente prefabricado
        page_header.render(titulo="Panel de Control", subtitulo="Gestión general")
        
        # 2. Renderizar un icono según las reglas de diseño
        ThemeManager.icono("space_dashboard", color="var(--color-primary)")

    # 3. Envolver todo en el Layout del Sistema
    app_layout(
        titulo_pagina="Mi Página",
        usuario_nombre="Juan Pérez",
        usuario_rol="admin",
        ruta_activa="/mi-pagina",
        contenido=contenido
    )
```
