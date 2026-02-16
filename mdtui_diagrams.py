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
            # Renderizar con D2 en modo texto (extensión .txt indica formato ASCII)
            proc = await asyncio.create_subprocess_exec(
                'd2', str(d2_path), str(output_path),
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
        import re

        lines = mermaid_code.split('\n')
        d2_nodes = {}  # id -> label
        d2_edges = []
        d2_styles = []

        # Detectar tipo
        is_sequence = any('sequenceDiagram' in line for line in lines)
        is_flowchart = any('flowchart' in line or 'graph' in line for line in lines)
        is_class = any('classDiagram' in line for line in lines)

        # Helper to extract node ID and label from Mermaid syntax
        def parse_node(s):
            # A[Label] -> returns (A, Label)
            m = re.match(r'(\w+)\[([^\]]+)\]', s)
            if m:
                return m.group(1), m.group(2)
            # A{Label} -> returns (A, Label)
            m = re.match(r'(\w)\{([^}]+)\}', s)
            if m:
                return m.group(1), m.group(2)
            # A("Label") -> returns (A, Label)
            m = re.match(r'(\w+)\(([^)]+)\)', s)
            if m:
                return m.group(1), m.group(2)
            # Just A -> returns (A, A)
            return s.strip(), s.strip()

        if is_sequence:
            # Conversión de secuencia
            for line in lines:
                line = line.strip()
                if not line or line.startswith('sequence'):
                    continue

                # participant declarations
                if line.startswith('participant '):
                    parts = line.split()
                    if len(parts) >= 2:
                        p = parts[1]
                        d2_nodes[p] = p

                # messages: A->>B: message
                for arrow in ['-->>', '->>', '-->', '->', '--', '-']:
                    if arrow in line:
                        parts = line.split(arrow)
                        if len(parts) == 2:
                            from_p = parts[0].strip()
                            rest = parts[1].strip()
                            to_p = rest
                            msg = ""
                            if ':' in rest:
                                to_p, msg = rest.split(':', 1)
                                msg = msg.strip()
                            to_p = to_p.strip()
                            # Clean node IDs
                            from_id, _ = parse_node(from_p)
                            to_id, _ = parse_node(to_p)
                            # Ensure nodes exist
                            if from_id not in d2_nodes:
                                d2_nodes[from_id] = from_id
                            if to_id not in d2_nodes:
                                d2_nodes[to_id] = to_id
                            if msg:
                                d2_edges.append(f"{from_id} -> {to_id}: {msg}")
                            else:
                                d2_edges.append(f"{from_id} -> {to_id}")
                        break

        elif is_flowchart:
            # First pass: parse nodes
            for line in lines:
                line = line.strip()
                if not line or line.startswith(('flowchart', 'graph')):
                    continue

                # Skip arrows for now
                if '-->' in line or '->' in line:
                    continue

                # Parse node definitions
                node_id, label = parse_node(line)
                if node_id:
                    d2_nodes[node_id] = label
                    # Add shape style for diamonds
                    if '{' in line:
                        d2_styles.append(f"{node_id}.shape: diamond")
                    elif '(' in line:
                        d2_styles.append(f"{node_id}.shape: rectangle")

            # Second pass: parse arrows
            for line in lines:
                line = line.strip()
                if not line or line.startswith(('flowchart', 'graph')):
                    continue

                # Parse arrows: A --> B, A -->|label| B
                for arrow in ['-->', '->']:
                    if arrow in line:
                        parts = line.split(arrow)
                        if len(parts) == 2:
                            from_part = parts[0].strip()
                            to_part = parts[1].strip()

                            # Parse source node
                            from_id, _ = parse_node(from_part)

                            # Parse destination - may have |label|
                            label = ""
                            to_clean = to_part
                            if '|' in to_clean:
                                # Format: |label| dest or dest|label|
                                # Mermaid: A -->|label| B
                                m = re.match(r'\|([^|]+)\|\s*(\w+)', to_clean)
                                if m:
                                    label = m.group(1)
                                    to_clean = m.group(2)
                                else:
                                    # Try another pattern
                                    parts_pipe = to_clean.split('|')
                                    if len(parts_pipe) >= 3:
                                        label = parts_pipe[1]
                                        to_clean = parts_pipe[2]

                            to_id, _ = parse_node(to_clean)

                            if not from_id or not to_id:
                                continue

                            # Ensure nodes exist
                            if from_id not in d2_nodes:
                                d2_nodes[from_id] = from_id
                            if to_id not in d2_nodes:
                                d2_nodes[to_id] = to_id

                            if label:
                                d2_edges.append(f"{from_id} -> {to_id}: {label}")
                            else:
                                d2_edges.append(f"{from_id} -> {to_id}")
                        break

        elif is_class:
            # Conversión de class diagram
            current_class = None
            class_attrs = {}

            for line in lines:
                line = line.strip()
                if not line or line.startswith('classDiagram'):
                    continue

                # Class definition: class ClassName {
                if line.startswith('class ') and '{' in line:
                    class_name = line.split()[1].split('{')[0].strip()
                    current_class = class_name
                    d2_nodes[class_name] = class_name
                    class_attrs[class_name] = []
                # Class definition without brace on same line
                elif line.startswith('class ') and '{' not in line:
                    class_name = line.split()[1].strip()
                    current_class = class_name
                    d2_nodes[class_name] = class_name
                    class_attrs[class_class] = []
                # Attributes and methods inside class
                elif current_class and line.startswith(('+', '-', '#')):
                    member = line[1:].strip()
                    class_attrs.setdefault(current_class, []).append(member)
                # Inheritance: Child <|-- Parent (Mermaid: Dog <|-- Animal means Dog extends Animal)
                elif '<|--' in line:
                    parts = line.split('<|--')
                    if len(parts) == 2:
                        child = parts[0].strip()
                        parent = parts[1].strip()
                        d2_edges.append(f"{child} -> {parent}: extends")
                        d2_nodes[parent] = parent
                        d2_nodes[child] = child

        # Build D2 output
        output = []
        for node_id, label in d2_nodes.items():
            output.append(f"{node_id}: {label}")
        output.append("")
        for style in d2_styles:
            output.append(style)
        if d2_styles:
            output.append("")
        for edge in d2_edges:
            output.append(edge)

        return '\n'.join(output) if output else mermaid_code

    # ============ RENDERIZADO ASCII NATIVO (FALLBACK) ============

    def _render_sequence_ascii(self, code: str, width: int) -> str:
        """Renderiza diagrama de secuencia en ASCII."""
        participants = []
        messages = []
        activations = []

        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('sequenceDiagram'):
                continue

            if line.startswith('participant '):
                participants.append(line.split()[1])
            elif line.startswith('actor '):
                participants.append(line.split()[1])
            elif '-->' in line or '->>' in line or '-->' in line or '->' in line:
                # Parsear mensaje completo
                for arrow in ['-->>', '->>', '-->', '->']:
                    if arrow in line:
                        parts = line.split(arrow)
                        if len(parts) == 2:
                            from_p = parts[0].strip()
                            rest = parts[1].strip()
                            if ':' in rest:
                                to_p, msg = rest.split(':', 1)
                                messages.append((from_p.strip(), to_p.strip(), msg.strip(), arrow))
                            else:
                                messages.append((from_p.strip(), rest.strip(), '', arrow))
                        break

        # Extraer participantes de mensajes si no hay participantes definidos
        if not participants:
            for from_p, to_p, _, _ in messages:
                if from_p not in participants:
                    participants.append(from_p)
                if to_p not in participants:
                    participants.append(to_p)

        if not participants:
            return self._format_code_block(code, "mermaid")

        # Calcular ancho
        max_name_len = max(len(p) for p in participants) if participants else 8
        col_width = max(max_name_len + 2, 12)
        num_cols = min(len(participants), (width - 10) // col_width)

        # Header
        result = []
        result.append("┌" + "─" * (width - 2) + "┐")
        result.append("│" + " SECUENCE DIAGRAM ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        # Línea de participantes
        header = "│"
        for p in participants[:num_cols]:
            header += p[:col_width-2].center(col_width-1)
        result.append(header + "│")
        result.append("│" + "│".join("─" * (col_width-1) for _ in range(num_cols)) + "│")

        # Mensajes
        for from_p, to_p, msg, arrow in messages[:15]:
            from_idx = participants.index(from_p) if from_p in participants else 0
            to_idx = participants.index(to_p) if to_p in participants else 0

            if from_idx == to_idx:
                # Mensaje a sí mismo
                line = "│"
                for i in range(num_cols):
                    if i == from_idx:
                        line += " ┌─ " + msg[:col_width-6] if msg else " │ "
                    else:
                        line += " " * (col_width-1)
                result.append(line + "│")
            elif to_idx > from_idx:
                # Mensaje hacia la derecha
                line = "│"
                for i in range(num_cols):
                    if i == from_idx:
                        line += " " * (col_width-1)
                    elif i == to_idx:
                        arrow_str = "──" + arrow.replace(">", "▶").replace("-", "─") + "▶ " + msg[:col_width-6] if msg else "──>"
                        line += arrow_str.ljust(col_width-1)
                    else:
                        line += " " * (col_width-1)
                result.append(line + "│")
            else:
                # Mensaje hacia la izquierda
                line = "│"
                for i in range(num_cols):
                    if i == to_idx:
                        arrow_str = "◀──" + arrow.replace(">", "▼").replace("-", "─") + " " + msg[:col_width-6] if msg else "<──"
                        line += arrow_str.rjust(col_width-1)
                    elif i == from_idx:
                        line += " " * (col_width-1)
                    else:
                        line += " " * (col_width-1)
                result.append(line + "│")

        result.append("└" + "─" * (width - 2) + "┘")
        return '\n'.join(result)

    def _render_flowchart_ascii(self, code: str, width: int) -> str:
        """Renderiza flowchart en ASCII con nodos y conexiones."""
        nodes = {}  # id -> (label, shape)
        edges = []  # (from, to, label)

        lines = code.split('\n')
        direction = 'TB'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('flowchart') or line.startswith('graph'):
                if 'LR' in line or 'RL' in line:
                    direction = 'LR'
                continue

            # Extraer nodos de la línea primero
            # A[Label] -> node_id: A, label: Label
            import re
            # Match nodos: A[Label], A("Label"), A{Label}
            node_pattern = r'(\w+)\[([^\]]+)\]'
            for match in re.finditer(node_pattern, line):
                nid = match.group(1)
                label = match.group(2)
                nodes[nid] = (label, 'rect')

            node_pattern = r'(\w+)\(([^)]+)\)'
            for match in re.finditer(node_pattern, line):
                nid = match.group(1)
                label = match.group(2)
                nodes[nid] = (label, 'round')

            node_pattern = r'(\w)\{([^}]+)\}'
            for match in re.finditer(node_pattern, line):
                nid = match.group(1)
                label = match.group(2)
                nodes[nid] = (label, 'diamond')

            # Ahora parsear conexiones
            for arrow in ['-->', '->', '-->>', '->>']:
                if arrow in line:
                    parts = line.split(arrow)
                    if len(parts) == 2:
                        from_node = parts[0].strip()
                        # Limpiar el nodo emisor (quitar labels)
                        from_node = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', from_node).strip()

                        to_part = parts[1].strip()
                        label = ''
                        if '|' in to_part:
                            to_part, label = to_part.split('|', 1)
                            label = label.strip()
                        to_node = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', to_part).strip()

                        if from_node and to_node:
                            edges.append((from_node, to_node, label))
                    break

        if not nodes:
            return self._format_code_block(code, "mermaid")

        # Calcular niveles (simplificado)
        node_levels = {}
        level = 0
        for from_n, to_n, _ in edges:
            if from_n not in node_levels:
                node_levels[from_n] = level
            if to_n not in node_levels:
                node_levels[to_n] = level + 1

        for node in nodes:
            if node not in node_levels:
                node_levels[node] = level

        # Renderizar
        result = []
        result.append("┌" + "─" * (width - 2) + "┐")
        result.append("│" + " FLOWCHART ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        # Renderizar nodos
        max_level = max(node_levels.values()) if node_levels else 0

        for lvl in range(max_level + 1):
            level_nodes = [(nid, nodes[nid]) for nid, lvl_ in node_levels.items() if lvl_ == lvl]
            if not level_nodes:
                continue

            # Renderizar nodos en esta línea
            line = "│ "
            for nid, (label, shape) in level_nodes[:4]:
                if shape == 'rect':
                    box = f"┌{label[:10].center(10)}┐"
                elif shape == 'round':
                    box = f"({label[:10].center(10)})"
                elif shape == 'diamond':
                    box = f"◇{label[:8].center(8)}◇"
                else:
                    box = f"○ {label[:8]} ○"
                line += box + "  "
            result.append(line.ljust(width - 1) + "│")

            # Renderizar flechas de conexión
            if lvl < max_level:
                arrow_line = "│ "
                for nid, (label, shape) in level_nodes[:4]:
                    arrow_line += "    │    "
                result.append(arrow_line.ljust(width - 1) + "│")

        # Mostrar relaciones
        if edges:
            result.append("├" + "─" * (width - 2) + "┤")
            result.append("│ Conexiones:")
            for from_n, to_n, label in edges[:8]:
                label_str = f" ({label})" if label else ""
                result.append(f"│   {from_n} ──→ {to_n}{label_str}".ljust(width - 1) + "│")

        result.append("└" + "─" * (width - 2) + "┘")
        return '\n'.join(result)

    def _render_class_ascii(self, code: str, width: int) -> str:
        """Renderiza diagrama de clases en ASCII."""
        classes = {}  # class_name -> {methods: [], attrs: [], relations: []}
        current_class = None

        lines = code.split('\n')
        for line in lines:
            line = line.strip()

            if line.startswith('class '):
                # Nueva clase
                parts = line.split()
                if len(parts) >= 2:
                    class_name = parts[1].split('{')[0].strip()
                    current_class = class_name
                    classes[current_class] = {'methods': [], 'attrs': [], 'relations': []}
            elif current_class and line.startswith('+'):
                # Método o atributo
                if '(' in line:
                    classes[current_class]['methods'].append(line[1:])
                else:
                    classes[current_class]['attrs'].append(line[1:])
            elif '-->' in line or '<--' in line or '-->' in line:
                # Relación
                for rel in ['<--', '-->', '<--', '-->']:
                    if rel in line:
                        parts = line.split(rel)
                        if len(parts) == 2:
                            from_c = parts[0].strip()
                            to_c = parts[1].strip()
                            classes[from_c]['relations'].append((to_c, rel))
                        break

        if not classes:
            return self._format_code_block(code, "mermaid")

        result = []
        result.append("┌" + "─" * (width - 2) + "┐")
        result.append("│" + " CLASS DIAGRAM ".center(width - 2) + "│")
        result.append("├" + "─" * (width - 2) + "┤")

        # Renderizar cada clase
        class_names = list(classes.keys())

        for i, cls_name in enumerate(class_names[:6]):
            cls_data = classes[cls_name]
            box_width = min(len(cls_name) + 4, width - 10)

            # Nombre de clase
            result.append("│  ┌" + "─" * box_width + "┐")
            result.append("│  │" + cls_name.center(box_width) + "│")
            result.append("│  ├" + "─" * box_width + "┤")

            # Atributos
            for attr in cls_data['attrs'][:3]:
                attr_text = f"+ {attr}"[:box_width]
                result.append("│  │" + attr_text.ljust(box_width) + "│")

            if cls_data['attrs'] and cls_data['methods']:
                result.append("│  ├" + "─" * box_width + "┤")

            # Métodos
            for method in cls_data['methods'][:3]:
                method_text = f"+ {method}"[:box_width]
                result.append("│  │" + method_text.ljust(box_width) + "│")

            result.append("│  └" + "─" * box_width + "┘")

            # Mostrar relaciones
            for to_class, rel in cls_data['relations'][:2]:
                rel_arrow = "───▶" if "-->" in rel else "◀───"
                result.append(f"│      {rel_arrow} {to_class}")

            if i < len(class_names) - 1 and class_names[i+1] in [r[0] for cls in classes.values() for r in cls['relations']]:
                result.append("│        │")

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
