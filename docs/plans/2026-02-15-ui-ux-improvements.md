# UI/UX Improvement Plan para MD TUI

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mejorar la UI/UX de la aplicación TUI para que sea más amigable para usuarios novatos de terminal, arreglar problemas de scroll, y hacer la interfaz más intuitiva.

**Architecture:** Mejoras incrementales en 4 áreas principales: Scroll smoothness, Botones táctiles mejorados, Ayuda contextual mejorada, y Feedback visual mejorado. Cada agente trabaja en un área independiente.

**Tech Stack:** Python, Textual TUI framework, Rich

**Agentes asignados:**
- Agente 1: Scroll improvements
- Agente 2: Touch-friendly buttons & accessibility
- Agente 3: Help system & onboarding
- Agente 4: Visual feedback & notifications

---

## Task 1: Fix Scroll Issues & Add Smooth Scrolling

**Files:**
- Modify: `mdtui.py:82-97` (DiagramViewerScreen compose)
- Modify: `mdtui.py:281-295` (MarkdownViewerScreen compose)
- Modify: `mdtui.py:233-241` (scroll actions)
- Modify: `mdtui.css:126-131` (scroll container styles)
- Test: Manual test after changes

### Step 1: Añadir smooth scrolling y mejor handling de scroll

**Step 1.1: Agregar auto-scroll y scroll por página**

```python
# En DiagramViewerScreen y MarkdownViewerScreen, modificar action_scroll_up/down:

def action_scroll_up(self) -> None:
    """Scroll hacia arriba con smooth scrolling."""
    scroll = self.query_one("#diagram-scroll", ScrollableContainer)
    # Scroll más suave y consistente
    scroll.scroll_home()

def action_scroll_down(self) -> None:
    """Scroll hacia abajo con smooth scrolling."""
    scroll = self.query_one("#diagram-scroll", ScrollableContainer)
    scroll.scroll_end()
```

**Step 1.2: Agregar atajos de keyboard para page up/down**

```python
# Agregar en BINDINGS de cada screen
("pageup", "page_up", "Página ↑"),
("pagedown", "page_down", "Página ↓"),
```

**Step 1.3: Mejorar CSS para scrollbars más visibles**

```css
/* En mdtui.css agregar */
Scrollbar {
    background: $surface-darken-2;
    width: 2;
}

Scrollbar > .scrollbar--thumb {
    background: $primary;
    border-radius: 1;
}

Scrollbar > .scrollbar--thumb:hover {
    background: $primary-lighten-1;
}
```

### Step 2: Commit scroll improvements

```bash
git add mdtui.py mdtui.css
git commit -m "fix: improve scroll behavior and add page navigation

- Add pageup/pagedown keyboard shortcuts
- Improve scroll container styling
- Add scroll position indicators

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Touch-Friendly Buttons & Accessibility

**Files:**
- Modify: `mdtui.py:89-95` (button layouts)
- Modify: `mdtui.py:288-293` (markdown toolbar)
- Modify: `mdtui.css:98-115` (button styles)
- Test: Verify button sizes and spacing

### Step 1: Aumentar tamaño de botones y mejorar spacing

**Step 1.1: Modificar estilos CSS para botones más grandes**

```css
/* En mdtui.css - mejorar .touch-button */
.touch-button {
    min-width: 12;
    height: 4;
    background: $primary;
    color: $text;
    text-style: bold;
    content-align: center middle;
    margin: 0 2;
    border-radius: 4;
}

.touch-button:hover {
    background: $primary-lighten-1;
}

.touch-button:focus {
    background: $primary-lighten-2;
    outline: thick $accent;
}
```

**Step 1.2: Agregar labels más descriptivos a los botones**

```python
# En DiagramViewerScreen compose()
yield Button("➖", id="zoom-out", classes="zoom-button", tooltip="Reducir zoom")
yield Button("➕", id="zoom-in", classes="zoom-button", tooltip="Aumentar zoom")
```

### Step 2: Commit button improvements

```bash
git add mdtui.py mdtui.css
git commit -m "feat: improve touch buttons and accessibility

- Larger touch targets (12x4 minimum)
- Better visual feedback on focus
- Add tooltips for better discoverability

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Enhanced Help System & Onboarding

**Files:**
- Modify: `mdtui.py:661-743` (HelpScreen)
- Modify: `mdtui.py:758-762` (on_mount startup)
- Create: `docs/welcome.md` (welcome screen content)
- Test: Test help accessibility

### Step 1: Improve Help Screen con mejores ejemplos visuales

**Step 1.1: Agregar pantalla de bienvenida al inicio**

```python
# En MDTUI class, agregar método
def show_welcome(self) -> None:
    """Muestra pantalla de bienvenida para nuevos usuarios."""
    self.push_screen(WelcomeScreen())
```

**Step 1.2: Mejorar HelpScreen con atajos visuales**

```python
# En HelpScreen compose(), mejorar la presentación
# Usar DataTable para mostrar atajos de forma más clara
```

### Step 2: Commit help improvements

```bash
git add mdtui.py
git commit -m "feat: improve help system with visual shortcuts

- Add welcome screen for new users
- Better keyboard shortcuts presentation
- More intuitive help navigation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Visual Feedback & Better Notifications

**Files:**
- Modify: `mdtui.py:34-49` (ConfirmDialog)
- Modify: `mdtui.py:339-345` (notification calls)
- Modify: `mdtui.css:351-370` (status styles)
- Test: Test all notifications

### Step 1: Improve feedback visual para usuarios novatos

**Step 1.1: Agregar animations de carga**

```python
# En DiagramViewerScreen, mejorar loading state
def watch_ascii_render(self, render: str) -> None:
    if not self.is_mounted:
        return

    if not render:
        # Mostrar spinner de carga
        content = self.query_one("#diagram-content", Static)
        content.update("[dim]⏳ Cargando diagrama...[/]")
    else:
        self.update_display()
```

**Step 1.2: Mejorar ConfirmDialog con iconos más claros**

```python
# En ConfirmDialog, usar iconos más descriptivos
def compose(self) -> ComposeResult:
    with Container(id="confirm-dialog"):
        yield Label("⚠️ " + self.message, id="dialog-message")
```

### Step 2: Commit feedback improvements

```bash
git add mdtui.py mdtui.css
git commit -m "feat: improve visual feedback and loading states

- Add loading spinner for diagram rendering
- Better error messages with icons
- Improved confirmation dialogs

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Final Integration

### Commit de integración

```bash
git add .
git commit -m "feat: complete UI/UX improvements for novice users

- Fixed scroll issues with page navigation
- Enhanced touch-friendly buttons
- Improved help system and onboarding
- Better visual feedback throughout

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Testing Checklist

- [ ] Scroll with arrow keys works smoothly
- [ ] Page up/down navigation works
- [ ] Touch buttons are easily tappable (min 44px equivalent)
- [ ] Help screen is accessible from all screens
- [ ] Loading states show feedback
- [ ] Error messages are clear and helpful
- [ ] Application starts without errors
- [ ] All screens navigate correctly
