#!/usr/bin/env python3
"""
MD TUI - Visualizador de Markdown para Termux/Móvil
Compatible con diagramas Mermaid y D2, optimizado para touch.
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Header, Footer, DataTable, Static, Button,
    Label, Input, ContentSwitcher
)
from textual.screen import Screen, ModalScreen
from textual.worker import Worker
from rich.markdown import Markdown as RichMarkdown
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from rich.console import Group
from rich.align import Align
from rich.style import Style

from mdtui_diagrams import DiagramRenderer, DiagramInfo


class ConfirmDialog(ModalScreen[bool]):
    """Diálogo de confirmación simple."""

    def __init__(self, message: str, *args, **kwargs) -> None:
        self.message = message
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.message, id="dialog-message")
            with Horizontal(id="dialog-buttons"):
                yield Button("Sí", variant="success", id="btn-yes")
                yield Button("No", variant="error", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")


class DiagramViewerScreen(Screen):
    """Pantalla para visualizar diagramas con zoom."""

    diagram_code = reactive("")
    diagram_type = reactive("")  # 'mermaid' o 'd2'
    zoom_level = reactive(1.0)
    ascii_render = reactive("")
    tool_used = reactive("")  # Herramienta usada para renderizar

    def __init__(self, code: str = "", diagram_type: str = "", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.diagram_code = code
        self.diagram_type = diagram_type
        # zoom_level ya tiene default 1.0 en la clase - no asignar aquí para no disparar watch
        self.tool_used = ""
        self.renderer = DiagramRenderer()

    ZOOM_PRESETS = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]

    BINDINGS = [
        ("plus", "zoom_in", "Zoom +"),
        ("minus", "zoom_out", "Zoom -"),
        ("up", "scroll_up", "Subir"),
        ("down", "scroll_down", "Bajar"),
        ("pageup", "page_up", "Página ↑"),
        ("pagedown", "page_down", "Página ↓"),
        ("c", "show_code", "Código"),
        ("r", "refresh", "Refrescar"),
        ("escape", "back", "Volver"),
        ("q", "back", "Volver"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="diagram-viewer"):
            with ScrollableContainer(id="diagram-scroll"):
                yield Static(id="diagram-content")

            with Horizontal(id="diagram-controls"):
                yield Button("➖", id="zoom-out", classes="zoom-button", tooltip="Reducir zoom")
                yield Label("100%", id="zoom-label", classes="zoom-level")
                yield Button("➕", id="zoom-in", classes="zoom-button", tooltip="Aumentar zoom")
                yield Button("📄 Código", id="btn-code", classes="touch-button", tooltip="Ver código fuente del diagrama")
                yield Button("🔄 Regen", id="btn-refresh", classes="touch-button", tooltip="Regenerar diagrama")
                yield Button("↩️ Volver", id="btn-back", classes="touch-button", tooltip="Volver al visor de markdown")

        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.render_diagram(), exclusive=True)

    def watch_zoom_level(self, level: float) -> None:
        if not self.is_mounted:
            return
        try:
            label = self.query_one("#zoom-label", Label)
            label.update(f"{int(level * 100)}%")
            self.update_display()
        except Exception:
            pass

    def watch_ascii_render(self, render: str) -> None:
        if not self.is_mounted:
            return
        self.update_display()

    def update_display(self) -> None:
        """Actualiza la visualización con el zoom actual."""
        content = self.query_one("#diagram-content", Static)
        scroll = self.query_one("#diagram-scroll", ScrollableContainer)

        if not self.ascii_render:
            content.update("[dim]Cargando diagrama...[/]")
            return

        # Aplicar zoom ajustando el ancho de las líneas
        lines = self.ascii_render.split('\n')
        base_width = 80
        max_width = int(base_width * self.zoom_level)

        zoomed_lines = []
        for line in lines:
            line_len = len(line)
            if line_len > max_width:
                # Truncar si la línea es muy larga para el zoom
                zoomed_lines.append(line[:max_width])
            elif line_len < max_width and self.zoom_level > 1.0:
                # En zoom alto, mantener líneas como están
                zoomed_lines.append(line)
            else:
                zoomed_lines.append(line)

        # Añadir info con herramienta usada
        tool_icon = {
            "d2": "🎨 D2",
            "diagon": "🔷 Diagon",
            "ascii": "📋 ASCII",
            "fallback": "📄 Fallback"
        }.get(self.tool_used, self.tool_used)

        header = f"[bold cyan]{self.diagram_type.upper()} Diagram[/] | [green]{tool_icon}[/] | Zoom: {int(self.zoom_level * 100)}%\n"
        header += "─" * min(max_width, 50) + "\n"

        content.update(header + '\n'.join(zoomed_lines))

    async def render_diagram(self) -> None:
        """Renderiza el diagrama usando el renderer."""
        from mdtui_diagrams import DiagramInfo

        diagram = DiagramInfo(
            diagram_type=self.diagram_type,
            code=self.diagram_code,
            line_start=0,
            line_end=0
        )

        result = await self.renderer.render_to_ascii(diagram, width=80)
        self.ascii_render = result.content if result.success else f"[red]Error: {result.error_message}[/]"
        self.tool_used = result.tool_used

    def show_code(self) -> None:
        """Muestra el código fuente del diagrama."""
        content = self.query_one("#diagram-content", Static)
        scroll = self.query_one("#diagram-scroll", ScrollableContainer)

        syntax = Syntax(
            self.diagram_code,
            self.diagram_type,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        content.update(syntax)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "zoom-in":
            # Buscar el siguiente nivel de zoom
            current = self.zoom_level
            for level in self.ZOOM_PRESETS:
                if level > current:
                    self.zoom_level = level
                    break
            else:
                self.zoom_level = self.ZOOM_PRESETS[-1]
        elif btn_id == "zoom-out":
            # Buscar el nivel anterior de zoom
            current = self.zoom_level
            for level in reversed(self.ZOOM_PRESETS):
                if level < current:
                    self.zoom_level = level
                    break
            else:
                self.zoom_level = self.ZOOM_PRESETS[0]
        elif btn_id == "btn-back":
            self.app.pop_screen()
        elif btn_id == "btn-refresh":
            self.run_worker(self.render_diagram(), exclusive=True)
        elif btn_id == "btn-code":
            self.show_code()

    def action_zoom_in(self) -> None:
        """Acción de zoom in."""
        current = self.zoom_level
        for level in self.ZOOM_PRESETS:
            if level > current:
                self.zoom_level = level
                break
        else:
            self.zoom_level = self.ZOOM_PRESETS[-1]

    def action_zoom_out(self) -> None:
        """Acción de zoom out."""
        current = self.zoom_level
        for level in reversed(self.ZOOM_PRESETS):
            if level < current:
                self.zoom_level = level
                break
        else:
            self.zoom_level = self.ZOOM_PRESETS[0]

    def action_scroll_up(self) -> None:
        """Scroll hacia arriba con smooth scrolling."""
        scroll = self.query_one("#diagram-scroll", ScrollableContainer)
        scroll.scroll_home()

    def action_scroll_down(self) -> None:
        """Scroll hacia abajo con smooth scrolling."""
        scroll = self.query_one("#diagram-scroll", ScrollableContainer)
        scroll.scroll_end()

    def action_page_up(self) -> None:
        """Página arriba."""
        scroll = self.query_one("#diagram-scroll", ScrollableContainer)
        scroll.scroll_page_up()

    def action_page_down(self) -> None:
        """Página abajo."""
        scroll = self.query_one("#diagram-scroll", ScrollableContainer)
        scroll.scroll_page_down()

    def action_show_code(self) -> None:
        """Mostrar código fuente."""
        self.show_code()

    def action_refresh(self) -> None:
        """Refrescar diagrama."""
        self.run_worker(self.render_diagram(), exclusive=True)

    def action_back(self) -> None:
        """Volver atrás."""
        self.app.pop_screen()


class MarkdownViewerScreen(Screen):
    """Pantalla para visualizar contenido Markdown."""

    file_path = reactive("")
    content = reactive("")
    current_diagrams: List[DiagramInfo] = []
    selected_diagram_index = reactive(-1)

    BINDINGS = [
        ("up", "scroll_up", "Subir"),
        ("down", "scroll_down", "Bajar"),
        ("pageup", "page_up", "Página arriba"),
        ("pagedown", "page_down", "Página abajo"),
        ("v", "view_diagram", "Ver diagrama"),
        ("q", "back", "Volver"),
    ]

    def __init__(self, file_path: str = "", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.file_path = file_path
        self.renderer = DiagramRenderer()

    # Niveles de zoom: índice actual
    ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="markdown-viewer"):
            with ScrollableContainer(id="markdown-scroll"):
                yield Static(id="markdown-content")

            with Horizontal(id="viewer-toolbar"):
                yield Button("📁 Archivos", id="btn-files", classes="touch-button", tooltip="Volver al explorador de archivos")
                yield Button("⬆️ Subir", id="btn-up", classes="touch-button", tooltip="Desplazar hacia arriba")
                yield Button("⬇️ Bajar", id="btn-down", classes="touch-button", tooltip="Desplazar hacia abajo")
                yield Button("🔍+", id="btn-zoom-in", classes="touch-button", tooltip="Aumentar zoom del contenido")
                yield Button("🔍-", id="btn-zoom-out", classes="touch-button", tooltip="Reducir zoom del contenido")

        yield Footer()

    def on_mount(self) -> None:
        self.load_file()

    def load_file(self) -> None:
        """Carga y renderiza el archivo Markdown."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()

            content_widget = self.query_one("#markdown-content", Static)

            # Detectar diagramas
            self.current_diagrams = self.renderer.detect_diagrams(self.content)

            # Procesar contenido - reemplazar diagramas con placeholders
            processed_content = self.content
            for i, diagram in enumerate(self.current_diagrams):
                placeholder = self.create_diagram_placeholder(diagram, i)
                lines = processed_content.split('\n')
                # Reemplazar el bloque de código
                new_lines = []
                skip_until = -1
                for j, line in enumerate(lines):
                    if j == skip_until:
                        continue
                    if line.strip() == f'```{diagram.diagram_type}':
                        new_lines.append(placeholder)
                        # Buscar cierre
                        for k in range(j+1, len(lines)):
                            if lines[k].strip() == '```':
                                skip_until = k
                                break
                    elif skip_until == -1 or j > skip_until:
                        new_lines.append(line)
                        skip_until = -1

                processed_content = '\n'.join(new_lines)

            # Renderizar Markdown
            markdown = RichMarkdown(processed_content, code_theme="monokai")
            content_widget.update(markdown)

            # Mostrar notificación si hay diagramas
            if self.current_diagrams:
                self.notify(
                    f"📊 {len(self.current_diagrams)} diagrama(s) detectado(s). "
                    "Toca el placeholder y luego 'v' para ver.",
                    timeout=4
                )

        except Exception as e:
            content_widget = self.query_one("#markdown-content", Static)
            content_widget.update(Panel(
                f"[red]Error al cargar archivo:[/]\n{str(e)}",
                title="Error",
                border_style="red"
            ))

    def create_diagram_placeholder(self, diagram: DiagramInfo, index: int) -> str:
        """Crea un placeholder visual para un diagrama."""
        icons = {
            "mermaid": "🧜",
            "d2": "🎨"
        }
        icon = icons.get(diagram.diagram_type, "📊")
        lines_count = len(diagram.code.split('\n'))

        return (
            f"\n> **{icon} Diagrama {diagram.diagram_type.upper()} #{index+1}**\n"
            f"> _{lines_count} líneas - Presiona la tecla **v** para visualizar_\n"
            f"> ```{diagram.diagram_type}\n"
            f"> {diagram.code.split(chr(10))[0] if diagram.code else ''}...\n"
            f"> ```\n"
        )

    def action_view_diagram(self) -> None:
        """Abre el visualizador de diagramas para el diagrama seleccionado."""
        if not self.current_diagrams:
            self.notify("No hay diagramas en este archivo", severity="warning")
            return

        # Si hay múltiples diagramas, abrir el primero o implementar selección
        diagram = self.current_diagrams[0]
        self.app.push_screen(DiagramViewerScreen(diagram.code, diagram.diagram_type))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        scroll_container = self.query_one("#markdown-scroll", ScrollableContainer)

        if btn_id == "btn-files":
            self.app.pop_screen()
        elif btn_id == "btn-up":
            scroll_container.scroll_up()
        elif btn_id == "btn-down":
            scroll_container.scroll_down()
        elif btn_id == "btn-zoom-in":
            self.action_zoom_in()
        elif btn_id == "btn-zoom-out":
            self.action_zoom_out()

    def action_zoom_in(self) -> None:
        """Aumenta el zoom del contenido."""
        content = self.query_one("#markdown-content", Static)
        current = content.styles.width or "100%"
        # Aumentar ancho para simular zoom
        scroll = self.query_one("#markdown-scroll", ScrollableContainer)
        # Scroll horizontal/vertical ajustado
        scroll.styles.width = "auto"

    def action_zoom_out(self) -> None:
        """Reduce el zoom del contenido."""
        scroll = self.query_one("#markdown-scroll", ScrollableContainer)
        scroll.styles.width = "100%"

    def key_v(self) -> None:
        """Tecla 'v' para ver diagrama."""
        self.action_view_diagram()

    def action_scroll_up(self) -> None:
        """Scroll hacia arriba con smooth scrolling."""
        scroll = self.query_one("#markdown-scroll", ScrollableContainer)
        scroll.scroll_home()

    def action_scroll_down(self) -> None:
        """Scroll hacia abajo con smooth scrolling."""
        scroll = self.query_one("#markdown-scroll", ScrollableContainer)
        scroll.scroll_end()

    def action_page_up(self) -> None:
        """Página arriba."""
        scroll = self.query_one("#markdown-scroll", ScrollableContainer)
        scroll.scroll_page_up()

    def action_page_down(self) -> None:
        """Página abajo."""
        scroll = self.query_one("#markdown-scroll", ScrollableContainer)
        scroll.scroll_page_down()

    def action_back(self) -> None:
        """Volver al explorador."""
        self.app.pop_screen()


class FileBrowserScreen(Screen):
    """Pantalla principal del explorador de archivos."""

    current_path = reactive(Path.cwd())
    selected_file = reactive("")

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("r", "refresh", "Refrescar"),
        ("enter", "open", "Abrir"),
        ("backspace", "parent", "Subir"),
        ("?", "help", "Ayuda"),
        ("h", "help", "Ayuda"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="main-container"):
            yield Label(str(self.current_path), id="browser-header")

            with Horizontal(id="browser-toolbar"):
                yield Button("⬆️ Subir", id="btn-parent", classes="touch-button", tooltip="Ir al directorio padre")
                yield Button("🏠 Home", id="btn-home", classes="touch-button", tooltip="Ir al directorio home")
                yield Button("🔄 Refrescar", id="btn-refresh", classes="touch-button", tooltip="Actualizar lista de archivos")
                yield Button("❓ Ayuda", id="btn-help", classes="touch-button", tooltip="Mostrar ayuda y atajos")

            table = DataTable(id="file-list", cursor_type="row")
            table.add_columns("", "Nombre", "Tamaño")
            table.cursor_type = "row"
            table.zebra_stripes = True
            yield table

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_files()

    def watch_current_path(self, path: Path) -> None:
        if self.is_mounted:
            try:
                header = self.query_one("#browser-header", Label)
                header.update(str(path))
                self.refresh_files()
            except:
                pass

    def refresh_files(self) -> None:
        """Actualiza la lista de archivos."""
        table = self.query_one("#file-list", DataTable)
        table.clear()

        try:
            entries = list(self.current_path.iterdir())

            # Separar carpetas y archivos
            dirs = [e for e in entries if e.is_dir()]
            files = [e for e in entries if e.is_file()]

            # Ordenar
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())

            # Agregar carpeta padre
            parent = self.current_path.parent
            if parent != self.current_path:
                table.add_row("⬆️", Text(".. (subir)", style="dim"), "")

            # Agregar carpetas primero
            for d in dirs:
                name = Text(f"{d.name}/", style="bold cyan")
                table.add_row("📁", name, "<dir>")

            # Agregar archivos
            for f in files:
                icon = "📄"
                style = "white"

                if f.suffix.lower() == '.md':
                    icon = "📝"
                    style = "bold green"
                elif f.suffix.lower() in ['.py', '.js', '.ts', '.go', '.rs', '.java']:
                    icon = "💻"
                    style = "yellow"
                elif f.suffix.lower() in ['.txt', '.json', '.yaml', '.yml', '.toml']:
                    icon = "📋"
                    style = "dim"
                elif f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                    icon = "🖼️"
                    style = "magenta"
                elif f.suffix.lower() in ['.zip', '.tar', '.gz', '.rar']:
                    icon = "📦"
                    style = "red"

                try:
                    size = f.stat().st_size
                    size_str = self.format_size(size)
                except:
                    size_str = "?"

                name = Text(f.name, style=style)
                table.add_row(icon, name, size_str)

        except PermissionError:
            table.add_row("⚠️", "[red]Sin permisos para leer este directorio[/]", "")
        except Exception as e:
            table.add_row("❌", f"[red]Error: {str(e)[:50]}[/]", "")

    def format_size(self, size: int) -> str:
        """Formatea tamaño de archivo."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                if unit == 'B':
                    return f"{size} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Maneja selección de fila (click o enter)."""
        self.open_selected()

    def open_selected(self) -> None:
        """Abre el elemento seleccionado."""
        table = self.query_one("#file-list", DataTable)
        cursor_row = table.cursor_row

        if cursor_row is None:
            return

        rows = list(table.rows)
        if cursor_row >= len(rows):
            return

        row_key = rows[cursor_row]
        row_data = table.get_row(row_key)

        if not row_data:
            return

        # row_data[1] es un objeto Text o string
        name_cell = row_data[1]
        if isinstance(name_cell, Text):
            name = str(name_cell.plain)
        else:
            name = str(name_cell)

        # Verificar si es "subir"
        if "subir" in name or name == "..":
            parent = self.current_path.parent
            if parent != self.current_path:
                self.current_path = parent
            return

        is_dir = name.endswith("/")
        name = name.rstrip("/")

        selected = self.current_path / name

        if is_dir:
            self.current_path = selected
        elif selected.suffix.lower() == '.md':
            self.app.push_screen(MarkdownViewerScreen(str(selected)))
        else:
            self.show_file_info(selected)

    def show_file_info(self, path: Path) -> None:
        """Muestra información de archivo no-Markdown."""
        try:
            stat = path.stat()
            mtime = path.stat().st_mtime
            from datetime import datetime
            mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

            info = (
                f"📄 {path.name}\n\n"
                f"📏 Tamaño: {self.format_size(stat.st_size)}\n"
                f"📅 Modificado: {mod_time}\n"
                f"\n[dim]ℹ️ Solo archivos .md pueden visualizarse[/]"
            )
            self.app.push_screen(ConfirmDialog(info))
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-parent":
            parent = self.current_path.parent
            if parent != self.current_path:
                self.current_path = parent
        elif btn_id == "btn-home":
            self.current_path = Path.home()
        elif btn_id == "btn-refresh":
            self.refresh_files()
        elif btn_id == "btn-help":
            self.app.push_screen(HelpScreen())

    def action_parent(self) -> None:
        """Subir al directorio padre."""
        parent = self.current_path.parent
        if parent != self.current_path:
            self.current_path = parent

    def action_refresh(self) -> None:
        """Refrescar lista."""
        self.refresh_files()

    def action_open(self) -> None:
        """Abrir archivo seleccionado."""
        self.open_selected()

    def action_quit(self) -> None:
        """Salir de la aplicación."""
        self.app.exit()

    def action_help(self) -> None:
        """Mostrar ayuda."""
        self.app.push_screen(HelpScreen())


class HelpScreen(Screen):
    """Pantalla de ayuda."""

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("q", "back", "Volver"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with ScrollableContainer(id="help-screen"):
            yield Label("\n[bold underline]📘 MD TUI - Guía de Uso[/]\n", classes="help-title")

            with Vertical(classes="help-section"):
                yield Label("[bold]🎯 Navegación Táctil:[/]")
                yield Label("  • Toca un archivo/carpeta para seleccionar")
                yield Label("  • Toca dos veces (o Enter) para abrir")
                yield Label("  • Usa los botones grandes en la parte inferior")
                yield Label("  • Desliza con dos dedos para scroll")

            yield Label("")

            with Vertical(classes="help-section"):
                yield Label("[bold]⌨️ Atajos de Teclado - Explorador:[/]")
                yield Label("  [cyan]↑/↓[/]      - Navegar arriba/abajo")
                yield Label("  [cyan]Enter[/]    - Abrir selección")
                yield Label("  [cyan]Backspace[/] - Subir directorio")
                yield Label("  [cyan]q[/]        - Salir")
                yield Label("  [cyan]h/?[/]      - Esta ayuda")
                yield Label("  [cyan]r[/]        - Refrescar")

            yield Label("")

            with Vertical(classes="help-section"):
                yield Label("[bold]📖 Controles - Visor Markdown:[/]")
                yield Label("  [cyan]↑/↓[/] o [cyan]PgUp/PgDn[/] - Scroll arriba/abajo")
                yield Label("  [cyan]v[/]          - Ver diagrama (cuando hay placeholder)")
                yield Label("  [cyan]q[/]          - Volver al explorador")
                yield Label("  Botones: [⬆️ Subir] [⬇️ Bajar] para scroll táctil")

            yield Label("")

            with Vertical(classes="help-section"):
                yield Label("[bold]📊 Controles - Visor de Diagramas:[/]")
                yield Label("  [cyan]+/-[/]        - Zoom in/out")
                yield Label("  [cyan]↑/↓[/]          - Scroll del diagrama")
                yield Label("  [cyan]c[/]            - Ver código fuente")
                yield Label("  [cyan]r[/]            - Refrescar/renderizar de nuevo")
                yield Label("  [cyan]q/Esc[/]        - Volver")
                yield Label("  Botones: [➕ Zoom] [➖ Zoom] para zoom táctil")

            yield Label("")

            with Vertical(classes="help-section"):
                yield Label("[bold]🔧 Instalación de Renderizadores:[/]")
                yield Label("  Los diagramas funcionan mejor con herramientas externas:")
                yield Label("  [dim]Mermaid: npm install -g @mermaid-js/mermaid-cli[/]")
                yield Label("  [dim]D2: go install oss.terrastruct.com/d2@latest[/]")
                yield Label("  [dim]Diagon: pip install diagon (o descargar binario)[/]")

            yield Label("")

            with Vertical(classes="help-section"):
                yield Label("[bold]💡 Tips para Termux/Móvil:[/]")
                yield Label("  • Usa los botones grandes en la parte inferior")
                yield Label("  • Scroll: toca los botones ⬆️⬇️ o desliza con el dedo")
                yield Label("  • Zoom en diagramas: usa los botones ➕➖")
                yield Label("  • Los volúmenes pueden funcionar como atajos (Vol+ = Esc)")
                yield Label("  • La interfaz se adapta a pantallas pequeñas")

            yield Label("")
            yield Button("↩️ Volver", id="btn-back", classes="touch-button", tooltip="Volver a la pantalla anterior")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()


class MDTUI(App):
    """Aplicación principal."""

    TITLE = "📝 MD TUI"
    SUB_TITLE = "Markdown Viewer para Termux"

    def __init__(self, initial_file: str = "", *args, **kwargs):
        # Obtener directorio del script real (resolviendo symlinks)
        script_dir = Path(__file__).resolve().parent
        self.CSS_PATH = str(script_dir / "mdtui.css")
        self.initial_file = initial_file
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        if self.initial_file:
            self.push_screen(MarkdownViewerScreen(self.initial_file))
        else:
            self.push_screen(FileBrowserScreen())


def main():
    """Punto de entrada."""
    import argparse

    parser = argparse.ArgumentParser(description="MD TUI - Visualizador Markdown")
    parser.add_argument("path", nargs="?", help="Archivo o directorio inicial")
    args = parser.parse_args()

    initial_file = ""
    if args.path:
        path = Path(args.path)
        if path.is_file() and path.suffix.lower() == '.md':
            # Si es un archivo md, abrir directamente
            initial_file = str(path)
        elif path.is_dir():
            # Si es directorio, cambiar a ese directorio
            os.chdir(path)

    app = MDTUI(initial_file=initial_file)
    app.run()


if __name__ == "__main__":
    main()
