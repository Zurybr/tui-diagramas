"""
Módulo de renderizado de diagramas para MD TUI.
Integra herramientas externas: D2, Diagon, y fallback ASCII nativo.
"""

import os
import sys
import asyncio
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.console import Console


@dataclass
class DiagramInfo:
    """Información de un diagrama detectado."""
    diagram_type: str  # 'mermaid', 'd2', 'math', 'sequence', 'tree', 'flowchart'
    code: str
    line_start: int
    line_end: int
    detected_subtype: str = ""  # 'sequence', 'flowchart', 'class', etc.


@dataclass
class RenderResult:
    """Resultado del renderizado de un diagrama."""
    content: str
    tool_used: str  # 'd2', 'diagon', 'mmdc', 'ascii', 'fallback'
    success: bool
    error_message: Optional[str] = None


class DiagramRenderer:
    """Renderizador de diagramas con soporte para herramientas externas."""

    def __init__(self):
        self.cache_dir = Path(tempfile.gettempdir()) / "mdtui_diagrams"
        self.cache_dir.mkdir(exist_ok=True)
        self._tools_checked = False
        self._tools = {
            'd2': False,
            'diagon': False,
            'mmdc': False,
        }

    async def _check_tools(self):
        """Verifica qué herramientas externas están disponibles."""
        if self._tools_checked:
            return

        for tool in self._tools:
            self._tools[tool] = await self._check_command(tool)

        self._tools_checked = True

    async def _check_command(self, cmd: str) -> bool:
        """Verifica si un comando está disponible en el sistema."""
        try:
            proc = await asyncio.create_subprocess_exec(
                'which', cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            return proc.returncode == 0
        except:
            return False

    def detect_diagrams(self, content: str) -> list[DiagramInfo]:
        """Detecta todos los diagramas en el contenido Markdown."""
        diagrams = []
        lines = content.split('\n')

        in_diagram = False
        diagram_type = ""
        diagram_code = []
        line_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detectar inicio de diagrama
            if stripped.startswith('```'):
                lang = stripped[3:].strip().lower()

                if lang in ('mermaid', 'mmd'):
                    in_diagram = True
                    diagram_type = "mermaid"
                    diagram_code = []
                    line_start = i
                    continue
                elif lang == 'd2':
                    in_diagram = True
                    diagram_type = "d2"
                    diagram_code = []
                    line_start = i
                    continue
                elif lang in ('math', 'latex'):
                    in_diagram = True
                    diagram_type = "math"
                    diagram_code = []
                    line_start = i
                    continue
                elif lang in ('sequence', 'seq'):
                    in_diagram = True
                    diagram_type = "sequence"
                    diagram_code = []
                    line_start = i
                    continue
                elif stripped == '```' and in_diagram:
                    # Fin de diagrama - detectar subtipo para mermaid
                    detected_subtype = ""
                    if diagram_type == "mermaid":
                        code_text = '\n'.join(diagram_code)
                        detected_subtype = self._detect_mermaid_subtype(code_text)

                    diagrams.append(DiagramInfo(
                        diagram_type=diagram_type,
                        code='\n'.join(diagram_code),
                        line_start=line_start,
                        line_end=i,
                        detected_subtype=detected_subtype
                    ))
                    in_diagram = False
                    continue

            if in_diagram:
                diagram_code.append(line)

        return diagrams

    def _detect_mermaid_subtype(self, code: str) -> str:
        """Detecta el subtipo de diagrama Mermaid."""
        code_lower = code.lower()

        if 'sequencediagram' in code_lower:
            return 'sequence'
        elif 'flowchart' in code_lower or 'graph td' in code_lower or 'graph lr' in code_lower:
            return 'flowchart'
        elif 'classdiagram' in code_lower:
            return 'class'
        elif 'erdiagram' in code_lower:
            return 'er'
        elif 'statediagram' in code_lower:
            return 'state'
        elif 'gantt' in code_lower:
            return 'gantt'
        elif 'pie' in code_lower:
            return 'pie'
        elif 'gitgraph' in code_lower:
            return 'git'
        elif 'mindmap' in code_lower:
            return 'mindmap'
        elif 'timeline' in code_lower:
            return 'timeline'
        elif 'journey' in code_lower:
            return 'journey'
        elif 'requirementdiagram' in code_lower:
            return 'requirement'
        elif 'c4context' in code_lower or 'c4container' in code_lower:
            return 'c4'
        else:
            return 'generic'

    async def render_to_ascii(self, diagram: DiagramInfo, width: int = 80) -> RenderResult:
        """Renderiza un diagrama a ASCII usando la mejor herramienta disponible."""
        await self._check_tools()

        # Estrategia de renderizado por tipo de diagrama
        if diagram.diagram_type == "mermaid":
            return await self._render_mermaid(diagram, width)
        elif diagram.diagram_type == "d2":
            return await self._render_d2(diagram, width)
        elif diagram.diagram_type == "math":
            return await self._render_math(diagram, width)
        elif diagram.diagram_type == "sequence":
            return await self._render_sequence(diagram, width)

        # Fallback genérico
        return RenderResult(
            content=self._format_code_block(diagram.code, diagram.diagram_type),
            tool_used="fallback",
            success=False,
            error_message=f"Tipo de diagrama '{diagram.diagram_type}' no soportado"
        )

    async def _render_mermaid(self, diagram: DiagramInfo, width: int) -> RenderResult:
        """Renderiza diagrama Mermaid con la mejor herramienta disponible."""
        subtype = diagram.detected_subtype
        code = diagram.code

        # Estrategia por subtipo
        strategies = []

        if subtype == 'sequence':
            # Para secuencias: Diagon es el mejor
            if self._tools['diagon']:
                strategies.append(self._render_with_diagon)
            # D2 también soporta secuencias
            if self._tools['d2']:
                strategies.append(self._render_mermaid_with_d2)
        elif subtype in ('flowchart', 'graph'):
            # Para flowcharts: D2 es excelente
            if self._tools['d2']:
                strategies.append(self._render_mermaid_with_d2)
            if self._tools['diagon']:
                strategies.append(self._render_with_diagon)
        elif subtype in ('class', 'er', 'state'):
            # Para diagramas estructurados: D2
            if self._tools['d2']:
                strategies.append(self._render_mermaid_with_d2)

        # Intentar cada estrategia
        for strategy in strategies:
            try:
                result = await strategy(diagram, width)
                if result.success:
                    return result
            except Exception as e:
                continue

        # Fallback ASCII nativo
        if subtype == 'sequence':
            content = self._render_sequence_ascii(code, width)
        elif subtype == 'flowchart':
            content = self._render_flowchart_ascii(code, width)
        elif subtype == 'class':
            content = self._render_class_ascii(code, width)
        else:
            content = self._format_code_block(code, "mermaid")

        return RenderResult(
            content=content,
            tool_used="ascii",
            success=True
        )

    async def _render_d2(self, diagram: DiagramInfo, width: int) -> RenderResult:
        """Renderiza diagrama D2."""
        if self._tools['d2']:
            return await self._render_with_d2_cli(diagram, width)

        # Fallback
        content = self._render_d2_structure(diagram.code, width)
        return RenderResult(
            content=content,
            tool_used="ascii",
            success=True
        )

    async def _render_math(self, diagram: DiagramInfo, width: int) -> RenderResult:
        """Renderiza expresiones matemáticas."""
        if self._tools['diagon']:
            return await self._render_with_diagon(diagram, width, generator='math')

        # Fallback: mostrar LaTeX formateado
        content = self._format_code_block(diagram.code, "tex")
        return RenderResult(
            content=content,
            tool_used="fallback",
            success=True
        )

    async def _render_sequence(self, diagram: DiagramInfo, width: int) -> RenderResult:
        """Renderiza diagrama de secuencia."""
        if self._tools['diagon']:
            return await self._render_with_diagon(diagram, width, generator='sequence')

        content = self._render_sequence_ascii(diagram.code, width)
        return RenderResult(
            content=content,
            tool_used="ascii",
            success=True
        )

    async def _render_with_diagon(self, diagram: DiagramInfo, width: int, generator: str = None) -> RenderResult:
        """Usa Diagon para renderizar diagramas."""
        if not self._tools['diagon']:
            return RenderResult(
                content="",
                tool_used="diagon",
                success=False,
                error_message="Diagon no está instalado"
            )

        # Crear archivo temporal
        code_hash = hashlib.md5(diagram.code.encode()).hexdigest()[:8]
        input_path = self.cache_dir / f"diagon_{generator or diagram.diagram_type}_{code_hash}.txt"
        output_path = self.cache_dir / f"diagon_{generator or diagram.diagram_type}_{code_hash}.out"

        input_path.write_text(diagram.code)

        try:
            # Determinar generador
            if generator is None:
                if diagram.diagram_type == 'sequence':
                    generator = 'sequence'
                elif diagram.diagram_type == 'math':
                    generator = 'math'
                elif diagram.detected_subtype == 'flowchart':
                    generator = 'flowchart'
                elif diagram.detected_subtype == 'tree':
                    generator = 'tree'
                else:
                    generator = 'sequence'  # Default

            # Ejecutar diagon
            proc = await asyncio.create_subprocess_exec(
                'diagon', generator,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate(input=diagram.code.encode())

            if proc.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                # Truncar si es muy ancho
                lines = output.split('\n')
                if width > 0:
                    lines = [line[:width] for line in lines]

                return RenderResult(
                    content='\n'.join(lines),
                    tool_used="diagon",
                    success=True
                )
            else:
                error = stderr.decode('utf-8', errors='replace')[:100]
                return RenderResult(
                    content="",
                    tool_used="diagon",
                    success=False,
                    error_message=f"Diagon error: {error}"
                )

        except Exception as e:
            return RenderResult(
                content="",
                tool_used="diagon",
                success=False,
                error_message=str(e)
            )
        finally:
            if input_path.exists():
                input_path.unlink()

    async def _render_mermaid_with_d2(self, diagram: DiagramInfo, width: int) -> RenderResult:
        """Convierte Mermaid a D2 y renderiza con D2 CLI en modo ASCII."""
        if not self._tools['d2']:
            return RenderResult(
                content="",
                tool_used="d2",
                success=False,
                error_message="D2 no está instalado"
            )

        # Convertir Mermaid a D2 (conversión básica)
        d2_code = self._convert_mermaid_to_d2(diagram.code)

        # Crear diagrama temporal tipo D2
        temp_diagram = DiagramInfo(
            diagram_type="d2",
            code=d2_code,
            line_start=0,
            line_end=0
        )

        return await self._render_with_d2_cli(temp_diagram, width)

    async def _render_with_d2_cli(self, diagram: DiagramInfo, width: int) -> RenderResult:
        """Usa D2 CLI para renderizar a ASCII."""
        if not self._tools['d2']:
            return RenderResult(
                content="",
                tool_used="d2",
                success=False,
                error_message="D2 no está instalado"
            )

        code_hash = hashlib.md5(diagram.code.encode()).hexdigest()[:8]
        d2_path = self.cache_dir / f"d2_render_{code_hash}.d2"
        output_path = self.cache_dir / f"d2_render_{code_hash}.txt"

        d2_path.write_text(diagram.code)

        try:
            # Renderizar con D2 en modo ASCII
            proc = await asyncio.create_subprocess_exec(
                'd2', str(d2_path), str(output_path),
                '--format', 'txt',  # ASCII output
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if output_path.exists():
                output = output_path.read_text()
                return RenderResult(
                    content=output,
                    tool_used="d2",
                    success=True
                )
            else:
                error = stderr.decode('utf-8', errors='replace')[:100]
                return RenderResult(
                    content="",
                    tool_used="d2",
                    success=False,
                    error_message=f"D2 error: {error}"
                )

        except Exception as e:
            return RenderResult(
                content="",
                tool_used="d2",
                success=False,
                error_message=str(e)
            )
        finally:
            if d2_path.exists():
                d2_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def _convert_mermaid_to_d2(self, mermaid_code: str) -> str:
        """Convierte código Mermaid básico a D2."""
        lines = mermaid_code.split('\n')
        d2_lines = []

        # Detectar tipo
        is_sequence = any('sequenceDiagram' in line for line in lines)
        is_flowchart = any('flowchart' in line or 'graph' in line for line in lines)

        if is_sequence:
            # Conversión de secuencia
            participants = []
            messages = []

            for line in lines:
                line = line.strip()
                if not line or line.startswith('sequence'):
                    continue

                if '->>' in line:
                    # Mensaje
                    parts = line.split('->>')
                    if len(parts) == 2:
                        from_p = parts[0].strip()
                        rest = parts[1].strip()
                        if ':' in rest:
                            to_p, msg = rest.split(':', 1)
                            messages.append((from_p.strip(), to_p.strip(), msg.strip()))

            # Crear estructura D2
            for from_p, to_p, msg in messages:
                d2_lines.append(f"{from_p} -> {to_p}: {msg}")

        elif is_flowchart:
            # Conversión de flowchart
            for line in lines:
                line = line.strip()
                if not line or line.startswith(('flowchart', 'graph')):
                    continue

                if '-->' in line:
                    # Conexión
                    parts = line.split('-->')
                    if len(parts) == 2:
                        from_n = parts[0].strip()
                        to_n = parts[1].strip().split('[', 1)[0].strip()
                        d2_lines.append(f"{from_n} -> {to_n}")
                elif '[' in line and ']' in line:
                    # Nodo con label
                    node_id = line.split('[')[0].strip()
                    label = line.split('[')[1].split(']')[0]
                    d2_lines.append(f"{node_id}: {label}")

        if not d2_lines:
            # Fallback: tratar cada línea como una conexión simple
            for line in lines:
                line = line.strip()
                if line and not line.startswith(('```', 'flowchart', 'graph', 'sequence')):
                    d2_lines.append(line)

        return '\n'.join(d2_lines) if d2_lines else mermaid_code

    # ============ RENDERIZADO ASCII NATIVO (FALLBACK) ============

    def _render_sequence_ascii(self, code: str, width: int) -> str:
        """Renderiza diagrama de secuencia en ASCII."""
        lines = []
        participants = []
        messages = []

        for line in code.split('\n'):
            line = line.strip()
            if not line or line.startswith('sequenceDiagram'):
                continue

            if line.startswith('participant'):
                parts = line.split()
                if len(parts) >= 2:
                    participants.append(parts[1])
            elif line.startswith('actor'):
                parts = line.split()
                if len(parts) >= 2:
                    participants.append(parts[1])
            elif '-->>' in line or '->>' in line or '-->' in line or '->' in line:
                messages.append(line)

        if not participants:
            for msg in messages:
                parts = msg.split('-')[0].strip()
                if parts and parts not in participants:
                    participants.append(parts)

        if not participants:
            return self._format_code_block(code, "mermaid")

        # Generar ASCII
        result = ["┌" + "─" * (width - 2) + "┐"]
        result.append("│" + " Diagrama de Secuencia ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        header = "│"
        spacing = (width - 2) // max(len(participants), 1)
        for p in participants[:4]:
            header += p[:spacing-2].center(spacing)
        result.append(header + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        for msg in messages[:10]:
            arrow = "->>" if '->>' in msg else "->"
            parts = msg.split(arrow)
            if len(parts) == 2:
                from_p = parts[0].strip()[:10]
                to_part = parts[1].strip()
                to_p = to_part.split(':')[0].strip()[:10]
                result.append(f"│ {from_p} {arrow} {to_p}".ljust(width - 1) + "│")

        result.append("└" + "─" * (width - 2) + "┘")
        return '\n'.join(result)

    def _render_flowchart_ascii(self, code: str, width: int) -> str:
        """Renderiza flowchart en ASCII simplificado."""
        nodes = []
        edges = []

        for line in code.split('\n'):
            line = line.strip()
            if not line or line.startswith(('flowchart', 'graph')):
                continue

            if '-->' in line:
                edges.append(line)
            elif '[' in line and ']' in line:
                node_id = line.split('[')[0].strip()
                node_text = line.split('[')[1].split(']')[0]
                nodes.append((node_id, node_text))

        if not nodes:
            return self._format_code_block(code, "mermaid")

        result = ["┌" + "─" * (width - 2) + "┐"]
        result.append("│" + " Flowchart ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        for node_id, node_text in nodes[:15]:
            display = f"┌─────┐ {node_text[:30]}"
            result.append("│ " + display.ljust(width - 3) + "│")

        result.append("└" + "─" * (width - 2) + "┘")
        return '\n'.join(result)

    def _render_class_ascii(self, code: str, width: int) -> str:
        """Renderiza diagrama de clases en ASCII."""
        classes = []

        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('class '):
                class_name = line.split()[1].split('{')[0].strip()
                classes.append(class_name)

        if not classes:
            return self._format_code_block(code, "mermaid")

        result = ["┌" + "─" * (width - 2) + "┐"]
        result.append("│" + " Diagrama de Clases ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        for cls in classes[:8]:
            box_width = min(len(cls) + 6, width - 6)
            result.append("│ " + "┌" + "─" * box_width + "┐")
            result.append("│ " + "│" + cls.center(box_width) + "│")
            result.append("│ " + "└" + "─" * box_width + "┘")

        result.append("└" + "─" * (width - 2) + "┘")
        return '\n'.join(result)

    def _render_d2_structure(self, code: str, width: int) -> str:
        """Renderiza estructura D2 simplificada."""
        shapes = []
        connections = []

        for line in code.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '->' in line:
                connections.append(line)
            elif ':' in line and not line.startswith('style'):
                shape_id = line.split(':')[0].strip()
                shape_label = line.split(':', 1)[1].strip()
                shapes.append((shape_id, shape_label))

        if not shapes:
            return self._format_code_block(code, "d2")

        result = ["┌" + "─" * (width - 2) + "┐"]
        result.append("│" + " Diagrama D2 ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        for shape_id, shape_label in shapes[:10]:
            display = f"{shape_id}: {shape_label}"[:width-6]
            result.append("│ 📦 " + display.ljust(width - 6) + "│")

        if connections:
            result.append("├" + "─" * (width - 2) + "┤")
            result.append("│ Conexiones:")
            for conn in connections[:5]:
                result.append("│   " + conn[:width-5].ljust(width - 5))

        result.append("└" + "─" * (width - 2) + "┘")
        return '\n'.join(result)

    def _format_code_block(self, code: str, lang: str) -> str:
        """Formatea código con sintaxis highlight."""
        console = Console(width=80, force_terminal=True)
        syntax = Syntax(code, lang, theme="monokai", line_numbers=False)
        with console.capture() as capture:
            console.print(syntax)
        return capture.get()

    def create_placeholder(self, diagram: DiagramInfo, index: int) -> str:
        """Crea un placeholder para el diagrama."""
        icons = {
            "mermaid": "🧜",
            "d2": "🎨",
            "math": "📐",
            "sequence": "🔄",
            "flowchart": "🌊",
            "class": "📦",
            "tree": "🌳",
            "generic": "📊"
        }

        icon = icons.get(diagram.diagram_type, icons.get(diagram.detected_subtype, "📊"))
        lines_count = len(diagram.code.split('\n'))
        subtype_info = f" ({diagram.detected_subtype})" if diagram.detected_subtype else ""

        return (
            f"\n> **{icon} Diagrama {diagram.diagram_type.upper()}{subtype_info} #{index+1}**\n"
            f"> _{lines_count} líneas - Presiona la tecla **v** para visualizar_\n"
            f"> ```{diagram.diagram_type}\n"
            f"> {diagram.code.split(chr(10))[0] if diagram.code else ''}...\n"
            f"> ```\n"
        )

    def get_tools_status(self) -> dict:
        """Retorna el estado de las herramientas externas."""
        return self._tools.copy()
