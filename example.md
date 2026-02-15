# 📝 Ejemplo de Markdown con Diagramas

Este archivo demuestra las capacidades de **MD TUI**.

## Diagrama de Secuencia (Mermaid)

```mermaid
sequenceDiagram
    participant Usuario
    participant Termux
    participant MD_TUI
    participant Archivo

    Usuario->>Termux: Abre app
    Termux->>MD_TUI: Ejecuta mdtui
    MD_TUI->>Archivo: Lee directorio
    Archivo-->>MD_TUI: Lista archivos
    MD_TUI-->>Usuario: Muestra UI
    Usuario->>MD_TUI: Selecciona archivo.md
    MD_TUI->>Archivo: Lee contenido
    Archivo-->>MD_TUI: Retorna markdown
    MD_TUI-->>Usuario: Renderiza documento
```

## Flowchart (Mermaid)

```mermaid
flowchart TD
    A[Inicio] --> B{¿Es .md?}
    B -->|Sí| C[Renderizar Markdown]
    B -->|No| D[Mostrar Info]
    C --> E{¿Tiene diagramas?}
    E -->|Sí| F[Detectar tipo]
    E -->|No| G[Mostrar texto]
    F --> H[Mermaid o D2]
    H --> I[Renderizar ASCII]
    D --> J[Fin]
    G --> J
    I --> J
```

## Diagrama D2

```d2
direction: right

App: MD TUI {
  shape: rectangle
  style.fill: "#4a90d9"
}

User: Usuario {
  shape: person
}

Files: Sistema de Archivos {
  shape: cylinder
}

Diagrams: Renderizador {
  Mermaid: 🧜 Mermaid
  D2: 🎨 D2
}

User -> App: Interactúa
App -> Files: Lee archivos
App -> Diagrams: Renderiza diagramas
```

## Diagrama de Clases

```mermaid
classDiagram
    class MDTUI {
        +FileBrowser browser
        +MarkdownViewer viewer
        +run()
    }
    class FileBrowser {
        +Path current_path
        +refresh_files()
        +open_selected()
    }
    class MarkdownViewer {
        +str file_path
        +Diagram[] diagrams
        +load_file()
        +render()
    }
    class DiagramViewer {
        +str code
        +str type
        +float zoom
        +render()
    }

    MDTUI --> FileBrowser
    MDTUI --> MarkdownViewer
    MarkdownViewer --> DiagramViewer
```

## Características de Texto

### Listas
- ✅ Explorador de archivos integrado
- ✅ Soporte Mermaid y D2
- ✅ Zoom en diagramas
- ✅ Optimizado para móvil

### Tablas
| Característica | Mermaid | D2 |
|---------------|---------|-----|
| Secuencias | ✅ | ✅ |
| Flowcharts | ✅ | ✅ |
| Clases | ✅ | ❌ |
| Infraestructura | ❌ | ✅ |

### Código

```python
# Ejemplo de código Python
def hello_termux():
    print("¡Hola desde MD TUI!")
    return "📝"

hello_termux()
```

---

**Presiona `v` para ver cualquier diagrama en modo detalle con zoom!**
