# Enhanced File Explorer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the basic TUI file browser into a full-featured Windows Explorer-style file manager with multiple view modes, touch/mouse/keyboard support, and rich previews.

**Architecture:** Modular UI system with view adapters (list/icons/details), mouse event handling via crossterm, and touch-friendly interaction patterns. The DirNavigator will support view state and filtering while maintaining the existing navigation logic.

**Tech Stack:** Rust with Ratatui 0.26, crossterm 0.27 for input handling, existing filesystem and preview modules.

---

## Phase 1: Core Infrastructure & View Modes

### Task 1: Create ViewMode Enum and ExplorerState

**Files:**
- Modify: `src/filesystem/mod.rs:1-42`
- Create: `src/ui/views.rs`
- Modify: `src/main.rs:1-50`

**Step 1: Add ViewMode enum to filesystem/mod.rs**

```rust
// Add after SortBy enum
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ViewMode {
    List,      // Traditional list view (current)
    Icons,     // Icon grid like Windows Explorer
    Details,   // Table with columns
}
```

**Step 2: Create ExplorerState in ui/views.rs**

```rust
use crate::filesystem::{DirNavigator, FileEntry, ViewMode, SortBy};

pub struct ExplorerState {
    pub view_mode: ViewMode,
    pub sort_by: SortBy,
    pub show_hidden: bool,
    pub filter_type: Option<FileTypeFilter>,
    pub search_query: String,
    pub selected_index: usize,
    pub icon_size: u8,  // For icon view scaling
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileTypeFilter {
    All,
    Folders,
    Documents,
    Images,
    Videos,
    Audio,
    Code,
    Archives,
    Executables,
}

impl ExplorerState {
    pub fn new() -> Self {
        ExplorerState {
            view_mode: ViewMode::List,
            sort_by: SortBy::Name,
            show_hidden: false,
            filter_type: None,
            search_query: String::new(),
            selected_index: 0,
            icon_size: 1,
        }
    }
}
```

**Step 3: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 4: Commit**

```bash
git add src/filesystem/mod.rs src/ui/views.rs
git commit -m "feat: add ViewMode enum and ExplorerState"
```

---

### Task 2: Create List View Component

**Files:**
- Modify: `src/ui/views.rs`
- Create: `src/ui/components/list_view.rs`

**Step 1: Create ListViewComponent**

```rust
use ratatui::{prelude::*, widgets::*};
use crate::filesystem::FileEntry;

pub struct ListViewComponent;

impl ListViewComponent {
    pub fn render(entries: &[FileEntry], selected: usize, area: Rect, frame: &mut Frame) {
        let items: Vec<ListItem> = entries.iter().enumerate().map(|(i, entry)| {
            let icon = Self::get_icon(entry);
            let size = Self::format_size(entry.size);
            let line = format!("{} {}  {}", icon, entry.name, size);
            let style = if i == selected {
                Style::default().fg(Color::Black).bg(Color::LightGreen)
            } else if entry.is_dir {
                Style::default().fg(Color::Blue)
            } else {
                Style::default().fg(Color::White)
            };
            ListItem::new(line).style(style)
        }).collect();

        let list = List::new(items)
            .block(Block::default().borders(Borders::ALL).title("Files"))
            .style(Style::default().fg(Color::White));

        frame.render_widget(list, area);
    }

    fn get_icon(entry: &FileEntry) -> &'static str {
        if entry.is_dir { "📂" } else {
            match entry.extension.as_deref() {
                Some("md") | Some("txt") => "📄",
                Some("rs") | Some("py") | Some("js") | Some("ts") => "💻",
                Some("png") | Some("jpg") | Some("jpeg") | Some("gif") => "🖼️",
                Some("pdf") => "📕",
                Some("zip") | Some("tar") | Some("gz") => "📦",
                Some("mp3") | Some("wav") => "🎵",
                Some("mp4") | Some("mkv") => "🎬",
                _ => "📄",
            }
        }
    }

    fn format_size(size: u64) -> String {
        if size == 0 && !false { return "".to_string(); } // dirs have no size
        const KB: u64 = 1024;
        const MB: u64 = KB * 1024;
        const GB: u64 = MB * 1024;
        if size >= GB { format!("{:.1}G", size as f64 / GB as f64) }
        else if size >= MB { format!("{:.1}M", size as f64 / MB as f64) }
        else if size >= KB { format!("{:.1}K", size as f64 / KB as f64) }
        else { format!("{}B", size) }
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ui/views.rs src/ui/components/list_view.rs
git commit -m "feat: add ListViewComponent with file icons"
```

---

### Task 3: Create Details View (Table)

**Files:**
- Create: `src/ui/components/details_view.rs`

**Step 1: Create DetailsViewComponent**

```rust
use ratatui::{prelude::*, widgets::*};
use crate::filesystem::FileEntry;

pub struct DetailsViewComponent;

impl DetailsViewComponent {
    pub fn render(entries: &[FileEntry], selected: usize, area: Rect, frame: &mut Frame) {
        let rows: Vec<Row> = entries.iter().enumerate().map(|(i, entry)| {
            let name = entry.name.clone();
            let size = if entry.is_dir { "-".to_string() } else { Self::format_size(entry.size) };
            let modified = entry.modified
                .map(|dt| dt.format("%Y-%m-%d %H:%M").to_string())
                .unwrap_or_else(|| "-".to_string());
            let ext = entry.extension.clone().unwrap_or_else(|| "-".to_string());

            let style = if i == selected {
                Style::default().fg(Color::Black).bg(Color::LightGreen)
            } else if entry.is_dir {
                Style::default().fg(Color::Blue)
            } else {
                Style::default().fg(Color::White)
            };

            Row::new(vec![name, size, modified, ext]).style(style)
        }).collect();

        let table = Table::new(rows, &[Constraint::Min(20), Constraint::Length(10), Constraint::Length(18), Constraint::Length(10)])
            .block(Block::default().borders(Borders::ALL).title("Details"))
            .header(
                Row::new(vec!["Name", "Size", "Modified", "Type"])
                    .style(Style::default().fg(Color::Cyan).bold())
            )
            .widths(&[
                Constraint::Min(20),
                Constraint::Length(10),
                Constraint::Length(18),
                Constraint::Length(10),
            ]);

        frame.render_widget(table, area);
    }

    fn format_size(size: u64) -> String {
        const KB: u64 = 1024;
        const MB: u64 = KB * 1024;
        const GB: u64 = MB * 1024;
        if size >= GB { format!("{:.1}G", size as f64 / GB as f64) }
        else if size >= MB { format!("{:.1}M", size as f64 / MB as f64) }
        else if size >= KB { format!("{:.1}K", size as f64 / KB as f64) }
        else { format!("{}B", size) }
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ui/components/details_view.rs
git commit -m "feat: add DetailsViewComponent table view"
```

---

### Task 4: Create Icons View (Grid)

**Files:**
- Create: `src/ui/components/icons_view.rs`

**Step 1: Create IconsViewComponent**

```rust
use ratatui::{prelude::*, widgets::*};
use crate::filesystem::FileEntry;

pub struct IconsViewComponent;

impl IconsViewComponent {
    pub fn render(entries: &[FileEntry], selected: usize, area: Rect, frame: &mut Frame) {
        // Calculate grid columns based on area width
        let cols = (area.width / 20).max(1) as usize;
        let item_width = area.width / cols as u16;

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints(vec![Constraint::Min(0); (entries.len() + cols - 1) / cols])
            .split(area);

        for (chunk_idx, chunk) in chunks.iter().enumerate() {
            let row_entries: Vec<(usize, &FileEntry)> = entries
                .iter()
                .enumerate()
                .skip(chunk_idx * cols)
                .take(cols)
                .collect();

            let col_chunks = Layout::default()
                .direction(Direction::Horizontal)
                .constraints(vec![Constraint::Length(item_width); cols.min(row_entries.len())])
                .split(*chunk);

            for ((idx, entry), col_area) in row_entries.into_iter().zip(col_chunks) {
                let icon = Self::get_icon(entry);
                let name = if entry.name.len() > 15 {
                    format!("{}...", &entry.name[..12])
                } else {
                    entry.name.clone()
                };

                let is_selected = idx == selected;
                let style = if is_selected {
                    Style::default().fg(Color::Black).bg(Color::LightGreen)
                } else if entry.is_dir {
                    Style::default().fg(Color::Blue)
                } else {
                    Style::default().fg(Color::White)
                };

                let text = Paragraph::new(format!("{}\n{}", icon, name))
                    .style(style)
                    .alignment(Alignment::Center)
                    .wrap(Wrap { trim: true });

                frame.render_widget(text, col_area);
            }
        }
    }

    fn get_icon(entry: &FileEntry) -> &'static str {
        if entry.is_dir { "📂" } else {
            match entry.extension.as_deref() {
                Some("md") | Some("txt") => "📄",
                Some("rs") | Some("py") | Some("js") | Some("ts") | Some("go") => "💻",
                Some("png") | Some("jpg") | Some("jpeg") | Some("gif") | Some("webp") => "🖼️",
                Some("pdf") => "📕",
                Some("zip") | Some("tar") | Some("gz") | Some("rar") => "📦",
                Some("mp3") | Some("wav") | Some("flac") => "🎵",
                Some("mp4") | Some("mkv") | Some("avi") => "🎬",
                Some("html") | Some("css") => "🌐",
                Some("json") | Some("yaml") | Some("toml") => "⚙️",
                Some("sh") | Some("bash") => "⚡",
                _ => "📄",
            }
        }
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ui/components/icons_view.rs
git commit -m "feat: add IconsViewComponent grid view"
```

---

## Phase 2: Filter System & Toolbar

### Task 5: Add FileTypeFilter Implementation

**Files:**
- Modify: `src/ui/views.rs`

**Step 1: Add filter logic**

```rust
impl FileTypeFilter {
    pub fn matches(&self, entry: &FileEntry) -> bool {
        if *self == FileTypeFilter::All { return true; }
        if entry.is_dir { return *self == FileTypeFilter::Folders; }

        match entry.extension.as_deref() {
            Some("md") | Some("txt") | Some("pdf") | Some("doc") | Some("docx") => {
                *self == FileTypeFilter::Documents
            }
            Some("png") | Some("jpg") | Some("jpeg") | Some("gif") | Some("webp") | Some("svg") => {
                *self == FileTypeFilter::Images
            }
            Some("mp4") | Some("mkv") | Some("avi") | Some("mov") => {
                *self == FileTypeFilter::Videos
            }
            Some("mp3") | Some("wav") | Some("flac") | Some("ogg") => {
                *self == FileTypeFilter::Audio
            }
            Some("rs") | Some("py") | Some("js") | Some("ts") | Some("go") | Some("java") | Some("c") | Some("cpp") | Some("h") => {
                *self == FileTypeFilter::Code
            }
            Some("zip") | Some("tar") | Some("gz") | Some("rar") | Some("7z") => {
                *self == FileTypeFilter::Archives
            }
            Some("exe") | Some("dll") | Some("so") | Some("dylib") => {
                *self == FileTypeFilter::Executables
            }
            _ => false,
        }
    }

    pub fn label(&self) -> &str {
        match self {
            FileTypeFilter::All => "All",
            FileTypeFilter::Folders => "Folders",
            FileTypeFilter::Documents => "Docs",
            FileTypeFilter::Images => "Images",
            FileTypeFilter::Videos => "Videos",
            FileTypeFilter::Audio => "Audio",
            FileTypeFilter::Code => "Code",
            FileTypeFilter::Archives => "Archives",
            FileTypeFilter::Executables => "Exec",
        }
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ui/views.rs
git commit -m "feat: add FileTypeFilter matching logic"
```

---

### Task 6: Create Toolbar Component

**Files:**
- Create: `src/ui/components/toolbar.rs`

**Step 1: Create Toolbar**

```rust
use ratatui::{prelude::*, widgets::*};
use crate::ui::views::{ViewMode, FileTypeFilter};

pub struct ToolbarComponent;

impl ToolbarComponent {
    pub fn render(
        frame: &mut Frame,
        area: Rect,
        view_mode: ViewMode,
        sort_by: crate::filesystem::SortBy,
        show_hidden: bool,
        filter: Option<FileTypeFilter>,
    ) {
        let view_icon = match view_mode {
            ViewMode::List => "☰",
            ViewMode::Icons => "▦",
            ViewMode::Details => "▤",
        };

        let sort_label = match sort_by {
            crate::filesystem::SortBy::Name => "Name",
            crate::filesystem::SortBy::Size => "Size",
            crate::filesystem::SortBy::Modified => "Date",
            crate::filesystem::SortBy::Type => "Type",
        };

        let hidden_label = if show_hidden { "Yes" } else { "No" };
        let filter_label = filter.map(|f| f.label().to_string()).unwrap_or_else(|| "All".to_string());

        let toolbar = Paragraph::new(format!(
            " [{}] View: {} | Sort: {} | Hidden: {} | Filter: {} | v=view s=sort h=hidden f=filter",
            view_icon, view_icon, sort_label, hidden_label, filter_label
        ))
        .style(Style::default().fg(Color::Cyan))
        .block(Block::default().borders(Borders::ALL).title("Toolbar"));

        frame.render_widget(toolbar, area);
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ui/components/toolbar.rs
git commit -m "feat: add ToolbarComponent with controls"
```

---

## Phase 3: Mouse & Touch Support

### Task 7: Enable Mouse Support in Terminal

**Files:**
- Modify: `src/main.rs:240-250`

**Step 1: Enable mouse events**

```rust
// In main.rs, after enable_raw_mode():
use crossterm::event::{EnableMouseCapture, DisableMouseCapture};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    // Enable mouse capture
    execute!(std::io::stdout(), EnableMouseCapture)?;

    let mut terminal = Terminal::new(CrosstermBackend::new(std::io::stdout()))?;
    // ... rest of code

    // Before disable_raw_mode:
    execute!(std::io::stdout(), DisableMouseCapture)?;
    disable_raw_mode()?;
    Ok(())
}
```

**Step 2: Add mouse event handling in main loop**

```rust
// In the event loop, after key handling:
if let Event::Mouse(mouse_event) = event::read()? {
    match mouse_event.kind {
        MouseEventKind::Down(MouseButton::Left) => {
            // Calculate clicked item from mouse position
            let clicked_index = calculate_index_from_position(
                mouse_event.column,
                mouse_event.row,
                area,
                state.explorer_state.view_mode,
            );
            if let Some(idx) = clicked_index {
                state.explorer_state.selected_index = idx;
            }
        }
        MouseEventKind::Down(MouseButton::Left) if mouse_event.modifiers.contains(KeyModifiers::SHIFT) => {
            // Double-click to open
            if state.selected_index < state.navigator.entries.len() {
                let entry = &state.navigator.entries[state.selected_index];
                if entry.is_dir {
                    state.navigator.navigate_to(&entry.path);
                    state.explorer_state.selected_index = 0;
                }
            }
        }
        _ => {}
    }
}
```

**Step 3: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 4: Commit**

```bash
git add src/main.rs
git commit -m "feat: enable mouse capture and click handling"
```

---

### Task 8: Add Mouse Click Position Calculator

**Files:**
- Create: `src/ui/components/mouse_handler.rs`

**Step 1: Create position calculator**

```rust
use ratatui::layout::Rect;
use crate::ui::views::ViewMode;

pub fn calculate_index_from_position(
    col: u16,
    row: u16,
    area: Rect,
    view_mode: ViewMode,
) -> Option<usize> {
    // Adjust for borders
    let inner = Rect {
        x: area.x + 1,
        y: area.y + 1,
        width: area.width.saturating_sub(2),
        height: area.height.saturating_sub(2),
    };

    if !inner.contains((col, row)) {
        return None;
    }

    let relative_row = row - inner.y;
    let relative_col = col - inner.x;

    match view_mode {
        ViewMode::List | ViewMode::Details => {
            Some(relative_row as usize)
        }
        ViewMode::Icons => {
            let cols = (inner.width / 20).max(1) as usize;
            let item_row = relative_row as usize; // Assuming 1 row per item
            let item_col = (relative_col / 20) as usize;
            let index = item_row * cols + item_col;
            Some(index)
        }
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ui/components/mouse_handler.rs
git commit -m "feat: add mouse position calculator"
```

---

## Phase 4: Integrate All Views into Main App

### Task 9: Refactor main.rs to Use New UI System

**Files:**
- Modify: `src/main.rs:50-150`

**Step 1: Add ExplorerState to AppState**

```rust
// Add to imports
use ui::views::ExplorerState;
use ui::components::{ListViewComponent, DetailsViewComponent, IconsViewComponent, ToolbarComponent};

struct AppState {
    mode: Mode,
    navigator: DirNavigator,
    explorer_state: ExplorerState,  // NEW
    selected_index: usize,
    preview_manager: PreviewManager,
    editor: Option<EditorBuffer>,
    git_manager: Option<GitManager>,
    search_query: String,
    message: String,
}
```

**Step 2: Update AppState::new()**

```rust
impl AppState {
    fn new() -> Self {
        let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
        let navigator = DirNavigator::new(cwd.clone());
        let git_manager = GitManager::new(cwd);

        AppState {
            mode: Mode::FileBrowser,
            navigator,
            explorer_state: ExplorerState::new(),
            selected_index: 0,
            preview_manager: PreviewManager::new(),
            editor: None,
            git_manager: Some(git_manager),
            search_query: String::new(),
            message: String::new(),
        }
    }
}
```

**Step 3: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 4: Commit**

```bash
git add src/main.rs
git commit -m "refactor: integrate ExplorerState into AppState"
```

---

### Task 10: Update render_file_browser to Use View Components

**Files:**
- Modify: `src/main.rs:54-95`

**Step 1: Replace render function**

```rust
fn render_file_browser(frame: &mut Frame, area: Rect, state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Header
            Constraint::Length(1),  // Toolbar
            Constraint::Min(0),     // Content
            Constraint::Length(1), // Status
        ])
        .split(area);

    // Header
    let header = Paragraph::new(format!(
        "📁 {} | q=quit, Enter=open, Space=preview, e=edit, g=git, /=search, h=hidden, .=parent",
        state.navigator.current_path.display()
    )).style(Style::default().fg(Color::Cyan));
    frame.render_widget(header, chunks[0]);

    // Toolbar
    ToolbarComponent::render(
        frame,
        chunks[1],
        state.explorer_state.view_mode,
        state.navigator.sort_by,
        state.navigator.show_hidden,
        state.explorer_state.filter_type,
    );

    // Filter entries
    let filtered_entries: Vec<_> = state.navigator.entries.iter()
        .filter(|e| {
            state.explorer_state.filter_type
                .map(|f| f.matches(e))
                .unwrap_or(true)
        })
        .collect();

    // Render based on view mode
    let list_area = chunks[2];
    match state.explorer_state.view_mode {
        ViewMode::List => {
            ListViewComponent::render(&filtered_entries, state.selected_index, list_area, frame);
        }
        ViewMode::Details => {
            DetailsViewComponent::render(&filtered_entries, state.selected_index, list_area, frame);
        }
        ViewMode::Icons => {
            IconsViewComponent::render(&filtered_entries, state.selected_index, list_area, frame);
        }
    }

    // Status bar
    let status = Paragraph::new(state.message.as_str())
        .style(Style::default().fg(Color::Yellow));
    frame.render_widget(status, chunks[3]);
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/main.rs
git commit -m "feat: integrate view components into main render"
```

---

### Task 11: Add Keyboard Shortcuts for View Switching

**Files:**
- Modify: `src/main.rs:260-320`

**Step 1: Add view mode keybindings**

```rust
// In FileBrowser mode match:
KeyCode::Char('v') => {
    // Cycle view mode: List -> Icons -> Details -> List
    state.explorer_state.view_mode = match state.explorer_state.view_mode {
        ViewMode::List => ViewMode::Icons,
        ViewMode::Icons => ViewMode::Details,
        ViewMode::Details => ViewMode::List,
    };
}
KeyCode::Char('f') => {
    // Cycle filter
    state.explorer_state.filter_type = match state.explorer_state.filter_type {
        None => Some(FileTypeFilter::Folders),
        Some(FileTypeFilter::Folders) => Some(FileTypeFilter::Documents),
        Some(FileTypeFilter::Documents) => Some(FileTypeFilter::Images),
        Some(FileTypeFilter::Images) => Some(FileTypeFilter::Code),
        Some(FileTypeFilter::Code) => Some(FileTypeFilter::Archives),
        Some(FileTypeFilter::Archives) => None, // Back to all
        _ => None,
    };
}
KeyCode::Char('s') => {
    // Sort cycle (existing)
    state.navigator.sort_by = match state.navigator.sort_by {
        SortBy::Name => SortBy::Size,
        SortBy::Size => SortBy::Modified,
        SortBy::Modified => SortBy::Type,
        SortBy::Type => SortBy::Name,
    };
    state.navigator.sort();
}
KeyCode::Char('h') => {
    // Toggle hidden (existing)
    state.navigator.show_hidden = !state.navigator.show_hidden;
    state.navigator.refresh();
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/main.rs
git commit -me "feat: add view mode and filter keyboard shortcuts"
```

---

## Phase 5: Touch Optimization for Termux

### Task 12: Add Touch-Friendly Interactions

**Files:**
- Modify: `src/main.rs` and `src/ui/components/mouse_handler.rs`

**Step 1: Add touch area navigation**

```rust
// Add scroll detection for touch
fn handle_touch_scroll(
    state: &mut AppState,
    last_y: &mut Option<u16>,
    current_y: u16,
) {
    if let Some(prev_y) = *last_y {
        let delta = (current_y as i32 - prev_y as i32) as isize;
        if delta > 2 {
            // Scroll down - move selection down
            state.selected_index = (state.selected_index + 1)
                .min(state.navigator.entries.len().saturating_sub(1));
        } else if delta < -2 {
            // Scroll up - move selection up
            state.selected_index = state.selected_index.saturating_sub(1);
        }
    }
    *last_y = Some(current_y);
}
```

**Step 2: Add visual feedback for touch selection**

In icons view, make touch targets larger:

```rust
// In IconsViewComponent, increase spacing
let item_height = 4; // Larger touch target
let cols = (area.width / 18).max(1) as usize; // More spacing
```

**Step 3: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 4: Commit**

```bash
git add src/main.rs src/ui/components/mouse_handler.rs
git commit -m "feat: add touch scroll and larger touch targets"
```

---

### Task 13: Add Bottom Action Bar for Touch

**Files:**
- Create: `src/ui/components/action_bar.rs`

**Step 1: Create action bar**

```rust
use ratatui::{prelude::*, widgets::*};

pub struct ActionBarComponent;

impl ActionBarComponent {
    pub fn render(frame: &mut Frame, area: Rect) {
        let bar = Row::new([
            "◀ Back ",
            "Open ▶ ",
            "Preview ☐ ",
            "Edit 📝 ",
            "Menu ☰ ",
        ])
        .style(Style::default().fg(Color::White))
        .alignment(Alignment::Center);

        let block = Block::default()
            .borders(Borders::ALL)
            .border_set(symbols::border::DOUBLE)
            .style(Style::default().bg(Color::DarkGray));

        frame.render_widget(bar, area);
    }
}
```

**Step 2: Add to main layout**

Modify render_file_browser to include action bar at bottom for touch devices.

**Step 3: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 4: Commit**

```bash
git add src/ui/components/action_bar.rs
git commit -m "feat: add touch-friendly action bar"
```

---

## Phase 6: Preview Panel Integration

### Task 14: Add Side Preview Panel

**Files:**
- Modify: `src/main.rs` render functions

**Step 1: Create side-by-side layout**

```rust
fn render_file_browser(frame: &mut Frame, area: Rect, state: &AppState) {
    // Check if preview should be shown (hold Shift or toggle)
    let show_preview = state.explorer_state.view_mode != ViewMode::Details;

    let chunks = if show_preview {
        Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(60), // File list
                Constraint::Percentage(40), // Preview panel
            ])
            .split(area)
    } else {
        vec![area]
    };

    // Render file browser in first chunk
    Self::render_file_list(frame, chunks[0], state);

    // Render preview in second chunk if enabled
    if show_preview && chunks.len() > 1 {
        Self::render_preview_panel(frame, chunks[1], state);
    }
}
```

**Step 2: Run to verify compilation**

Run: `cargo check`
Expected: PASS

**Step 3: Commit**

```bash
git add src/main.rs
git commit -m "feat: add side preview panel option"
```

---

## Phase 7: Final Integration & Testing

### Task 15: Complete Integration and Test

**Step 1: Build and test**

Run: `cargo build --release`
Expected: Compiles without errors

**Step 2: Run the application**

Run: `cargo run --release`
Expected: Application launches with new UI

**Step 3: Test all view modes**

- Press `v` to cycle through List/Icons/Details
- Press `f` to filter by type
- Press `s` to change sort
- Press `h` to toggle hidden files

**Step 4: Test mouse support**

- Click on items to select
- Double-click to open

**Step 5: Commit**

```bash
git add .
git commit -m "feat: complete enhanced file explorer with all views"
```

---

## Summary

This plan adds:

1. **View Modes**: List, Icons (grid), Details (table)
2. **Filtering**: By file type (Documents, Images, Code, etc.)
3. **Sorting**: Name, Size, Modified, Type
4. **Mouse Support**: Click to select, double-click to open
5. **Touch Optimization**: Larger targets, scroll support, action bar
6. **Toolbar**: Visual feedback of current settings
7. **Preview Panel**: Optional side panel for quick previews
8. **Icons**: File type icons in all views

Key keyboard shortcuts:
- `v` - Cycle view mode
- `f` - Cycle filter type
- `s` - Cycle sort
- `h` - Toggle hidden files
- Mouse click - Select item
- Touch - Scroll and select
