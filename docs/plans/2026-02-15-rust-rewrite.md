# MD TUI Rust Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reescribir la aplicación Python actual en Rust con funcionalidades avanzadas de explorador de archivos, previsualización múltiple, edición de código y visualización git.

**Architecture:** Aplicación TUI basada en Ratatui (equivalente Rust de Textual) con:
- Módulo de explorador de archivos con navegación jerárquica
- Sistema de previsualización extensible (texto, PDF, imágenes, código)
- Editor integrado estilo VSCode con syntax highlighting
- Integración con sistema de extensiones VSCode
- Visualizador de cambios git integrado

**Tech Stack:**
- Rust (1.75+)
- Ratatui (TUI framework)
- Tree-sitter (syntax highlighting)
- git2-rs (git operations)
- zed-editor/lsp (LSP for VSCode compatibility)
- ripgrep, fd, fzf (shell tools)

---

## Fase 1: Configuración del Proyecto Rust

### Task 1: Inicializar proyecto Cargo

**Files:**
- Create: `/home/zurybr/workspace/TUI/tui-diagramas/Cargo.toml`
- Create: `/home/zurybr/workspace/TUI/tui-diagramas/src/main.rs`
- Create: `/home/zurybr/workspace/TUI/tui-diagramas/.cargo/config.toml`

**Step 1: Crear Cargo.toml**

```toml
[package]
name = "mdtui"
version = "0.1.0"
edition = "2021"
authors = ["Zurybr"]

[dependencies]
ratatui = "0.26"
crossterm = "0.27"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
git2 = "0.19"
syntax-drawing = "0.2"
tree-sitter = "0.22"
tree-sitter-highlight = "0.22"
dirs = "5"
glob = "0.3"
regex = "1"
colored = "2"
chrono = "0.4"
which = "5"
walkdir = "2"
similar = "2"

[profile.release]
opt-level = 3
lto = true

[lib]
name = "mdtui"
path = "src/lib.rs"
```

**Step 2: Crear estructura de directorios**

```bash
mkdir -p src/{ui,filesystem,preview,editor,git,utils}
mkdir -p .cargo
```

**Step 3: Crear main.rs mínimo**

```rust
use ratatui::{prelude::*, widgets::*};
use crossterm::{event::{self, Event, KeyCode, KeyEventKind}, terminal::{disable_raw_mode, enable_raw_mode}};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut terminal = Terminal::new(CrosstermBackend::new(std::io::stdout()))?;

    loop {
        terminal.draw(|f| {
            let paragraph = Paragraph::new("MD TUI - Rust Version").block(Block::default().borders(Borders::ALL));
            f.render_widget(paragraph, f.size());
        })?;

        if let Event::Key(key) = event::read()? {
            if key.kind == KeyEventKind::Press && key.code == KeyCode::Char('q') {
                break;
            }
        }
    }

    disable_raw_mode()?;
    Ok(())
}
```

**Step 4: Compilar y verificar**

Run: `cargo build --release`
Expected: Compilación exitosa

**Step 5: Commit**

```bash
git add Cargo.toml src/ .cargo/
git commit -m "feat: initialize Rust project with Cargo.toml

- Add Ratatui, Crossterm, Tokio dependencies
- Create basic TUI skeleton

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 2: Explorador de Archivos

### Task 2: Módulo de filesystem

**Files:**
- Create: `src/filesystem/mod.rs`
- Create: `src/filesystem/dir.rs`
- Create: `src/filesystem/file.rs`

**Step 1: Crear FileEntry y DirNavigator**

```rust
// src/filesystem/mod.rs
pub mod dir;
pub mod file;

use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileEntry {
    pub name: String,
    pub path: PathBuf,
    pub is_dir: bool,
    pub size: u64,
    pub modified: Option<chrono::DateTime<chrono::Utc>>,
    pub is_hidden: bool,
    pub extension: Option<String>,
}

#[derive(Debug, Clone)]
pub enum SortBy {
    Name,
    Size,
    Modified,
    Type,
}

impl FileEntry {
    pub fn from_path(path: &std::path::Path) -> Option<Self> {
        let metadata = std::fs::metadata(path).ok()?;
        let name = path.file_name()?.to_string_lossy().to_string();
        let is_dir = metadata.is_dir();
        let size = metadata.len();
        let modified = metadata.modified().ok()
            .map(|t| chrono::DateTime::<chrono::Utc>::from(t));
        let is_hidden = name.starts_with('.');
        let extension = path.extension().map(|e| e.to_string_lossy().to_string());

        Some(FileEntry { name, path: path.to_path_buf(), is_dir, size, modified, is_hidden, extension })
    }
}
```

**Step 2: Crear DirNavigator**

```rust
// src/filesystem/dir.rs
use super::FileEntry;
use std::path::PathBuf;
use walkdir::WalkDir;

pub struct DirNavigator {
    pub current_path: PathBuf,
    pub entries: Vec<FileEntry>,
    pub show_hidden: bool,
    pub sort_by: super::SortBy,
    pub filter: Option<String>,
}

impl DirNavigator {
    pub fn new(path: PathBuf) -> Self {
        let mut nav = DirNavigator {
            current_path: path,
            entries: Vec::new(),
            show_hidden: false,
            sort_by: super::SortBy::Name,
            filter: None,
        };
        nav.refresh();
        nav
    }

    pub fn refresh(&mut self) {
        self.entries.clear();
        let path = &self.current_path;

        for entry in WalkDir::new(path).max_depth(1) {
            if let Ok(entry) = entry {
                let entry_path = entry.path();
                if entry_path == path { continue; }

                if let Some(file_entry) = FileEntry::from_path(entry_path) {
                    if !self.show_hidden && file_entry.is_hidden { continue; }
                    if let Some(ref filter) = self.filter {
                        if !file_entry.name.to_lowercase().contains(&filter.to_lowercase()) {
                            continue;
                        }
                    }
                    self.entries.push(file_entry);
                }
            }
        }

        self.sort();
    }

    pub fn sort(&mut self) {
        match self.sort_by {
            super::SortBy::Name => self.entries.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase())),
            super::SortBy::Size => self.entries.sort_by(|a, b| b.size.cmp(&a.size)),
            super::SortBy::Modified => self.entries.sort_by(|a, b| b.modified.cmp(&a.modified)),
            super::SortBy::Type => self.entries.sort_by(|a, b| {
                match (a.is_dir, b.is_dir) {
                    (true, false) => std::cmp::Ordering::Less,
                    (false, true) => std::cmp::Ordering::Greater,
                    _ => a.extension.cmp(&b.extension),
                }
            }),
        }
    }

    pub fn navigate_to(&mut self, path: &std::path::Path) {
        if path.is_dir() {
            self.current_path = path.to_path_buf();
            self.refresh();
        }
    }

    pub fn navigate_up(&mut self) {
        if let Some(parent) = self.current_path.parent() {
            self.current_path = parent.to_path_buf();
            self.refresh();
        }
    }

    pub fn search(&mut self, query: &str) {
        self.filter = Some(query.to_string());
        self.refresh();
    }
}
```

**Step 3: Crear archivo de tests**

```rust
// src/filesystem/file.rs
#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_file_entry_from_path() {
        let path = env::current_dir().unwrap();
        let entry = FileEntry::from_path(&path);
        assert!(entry.is_some());
    }
}
```

**Step 4: Compilar y verificar**

Run: `cargo build`
Expected: Compilación exitosa

**Step 5: Commit**

```bash
git add src/filesystem/
git commit -m "feat: add filesystem module

- FileEntry struct with metadata
- DirNavigator for directory traversal
- Sorting and filtering support

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 3: Previsualización de Archivos

### Task 3: Sistema de previsualización

**Files:**
- Create: `src/preview/mod.rs`
- Create: `src/preview/text.rs`
- Create: `src/preview/code.rs`
- Create: `src/preview/image.rs`
- Create: `src/preview/pdf.rs`
- Create: `src/preview/markdown.rs`

**Step 1: Crear trait PreviewProvider**

```rust
// src/preview/mod.rs
use std::path::Path;

pub mod text;
pub mod code;
pub mod image;
pub mod pdf;
pub mod markdown;

#[derive(Debug, Clone)]
pub enum PreviewContent {
    Text(String),
    Binary(String),
    Image(Vec<u8>),
    Error(String),
}

pub trait PreviewProvider {
    fn can_preview(&self, path: &Path) -> bool;
    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String>;
}

pub struct PreviewManager {
    providers: Vec<Box<dyn PreviewProvider>>,
}

impl PreviewManager {
    pub fn new() -> Self {
        let mut manager = PreviewManager { providers: Vec::new() };
        manager.register(Box::new(text::TextPreview::new()));
        manager.register(Box::new(code::CodePreview::new()));
        manager.register(Box::new(image::ImagePreview::new()));
        manager.register(Box::new(pdf::PdfPreview::new()));
        manager.register(Box::new(markdown::MarkdownPreview::new()));
        manager
    }

    pub fn register(&mut self, provider: Box<dyn PreviewProvider>) {
        self.providers.push(provider);
    }

    pub fn get_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        for provider in &self.providers {
            if provider.can_preview(path) {
                return provider.generate_preview(path);
            }
        }
        Err("No preview provider available".to_string())
    }
}
```

**Step 2: Crear previsualizador de texto**

```rust
// src/preview/text.rs
use super::*;
use std::fs;

pub struct TextPreview {
    max_lines: usize,
    max_width: usize,
}

impl TextPreview {
    pub fn new() -> Self {
        TextPreview { max_lines: 500, max_width: 200 }
    }
}

impl PreviewProvider for TextPreview {
    fn can_preview(&self, path: &Path) -> bool {
        let text_extensions = ["txt", "md", "json", "xml", "yaml", "yml", "toml", "ini", "cfg", "conf", "log", "csv", "sql", "sh", "bash", "zsh", "py", "rs", "js", "ts", "java", "c", "cpp", "h", "hpp", "go", "rb", "php", "swift", "kt", "scala", "r", "lua", "pl", "rb", "ex", "exs", "erl", "hs", "clj", "vim", "gitignore", "env", "editorconfig"];
        path.extension()
            .and_then(|e| e.to_str())
            .map(|e| text_extensions.contains(&e.to_lowercase().as_str()))
            .unwrap_or(false)
    }

    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        fs::read_to_string(path)
            .map(|content| {
                let lines: Vec<&str> = content.lines().take(self.max_lines).collect();
                let truncated: Vec<String> = lines.iter()
                    .map(|l| if l.len() > self.max_width { &l[..self.max_width] } else { *l })
                    .map(|s| s.to_string())
                    .collect();
                PreviewContent::Text(truncated.join("\n"))
            })
            .map_err(|e| e.to_string())
    }
}
```

**Step 3: Crear previsualizador de código con syntax highlighting**

```rust
// src/preview/code.rs
use super::*;
use std::fs;
use tree_sitter::{Language, Parser};
use tree_sitter_highlight::{HighlightConfiguration, Highlighter};

pub struct CodePreview {
    max_lines: usize,
}

impl CodePreview {
    pub fn new() -> Self {
        CodePreview { max_lines: 300 }
    }

    fn detect_language(path: &Path) -> &'static str {
        match path.extension().and_then(|e| e.to_str()) {
            Some("rs") => "rust",
            Some("py") => "python",
            Some("js") | Some("mjs") => "javascript",
            Some("ts") | Some("tsx") => "typescript",
            Some("go") => "go",
            Some("java") => "java",
            Some("c") | Some("h") => "c",
            Some("cpp") | Some("hpp") | Some("cc") => "cpp",
            Some("rb") => "ruby",
            Some("php") => "php",
            Some("swift") => "swift",
            Some("kt") | Some("kts") => "kotlin",
            Some("scala") => "scala",
            Some("c") => "c",
            _ => "plaintext",
        }
    }
}

impl PreviewProvider for CodePreview {
    fn can_preview(&self, path: &Path) -> bool {
        let code_extensions = ["rs", "py", "js", "ts", "tsx", "jsx", "java", "c", "cpp", "h", "hpp", "go", "rb", "php", "swift", "kt", "scala", "c", "cs", "hs", "clj", "ex", "exs", "erl", "lua", "pl", "sh", "bash", "zsh", "sql", "graphql", "svelte", "vue", "css", "scss", "sass", "less", "html", "htm"];
        path.extension()
            .and_then(|e| e.to_str())
            .map(|e| code_extensions.contains(&e.to_lowercase().as_str()))
            .unwrap_or(false)
    }

    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        fs::read_to_string(path)
            .map(|content| {
                let lines: Vec<&str> = content.lines().take(self.max_lines).collect();
                let truncated = lines.join("\n");
                PreviewContent::Text(truncated)
            })
            .map_err(|e| e.to_string())
    }
}
```

**Step 4: Crear previsualizador de imágenes (ASCII)**

```rust
// src/preview/image.rs
use super::*;
use std::fs;
use std::process::Command;

pub struct ImagePreview {
    width: u32,
    height: u32,
}

impl ImagePreview {
    pub fn new() -> Self {
        ImagePreview { width: 80, height: 40 }
    }
}

impl PreviewProvider for ImagePreview {
    fn can_preview(&self, path: &Path) -> bool {
        let image_extensions = ["png", "jpg", "jpeg", "gif", "bmp", "webp", "ico", "tiff", "svg"];
        path.extension()
            .and_then(|e| e.to_str())
            .map(|e| image_extensions.contains(&e.to_lowercase().as_str()))
            .unwrap_or(false)
    }

    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        // Try chafa first
        if which::which("chafa").is_ok() {
            let output = Command::new("chafa")
                .args(["--size", &format!("{}x{}", self.width, self.height), "-s", &format!("{}x{}", self.width, self.height), path.to_str().unwrap()])
                .output();

            if let Ok(output) = output {
                if output.status.success() {
                    let ascii = String::from_utf8_lossy(&output.stdout).to_string();
                    return Ok(PreviewContent::Text(ascii));
                }
            }
        }

        // Fallback to imagemagick
        if which::which("convert").is_ok() {
            let output = Command::new("convert")
                .args([path.to_str().unwrap(), "gif:-"])
                .output();

            if let Ok(output) = output {
                if output.status.success() {
                    return Ok(PreviewContent::Text("[Image preview not available - install chafa]".to_string()));
                }
            }
        }

        Ok(PreviewContent::Text("[Image: install chafa for ASCII preview]".to_string()))
    }
}
```

**Step 5: Crear previsualizador de PDF**

```rust
// src/preview/pdf.rs
use super::*;
use std::fs;
use std::process::Command;

pub struct PdfPreview {
    max_pages: usize,
}

impl PdfPreview {
    pub fn new() -> Self {
        PdfPreview { max_pages: 3 }
    }
}

impl PreviewProvider for PdfPreview {
    fn can_preview(&self, path: &Path) -> bool {
        path.extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_lowercase() == "pdf")
            .unwrap_or(false)
    }

    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        if which::which("pdftotext").is_ok() {
            let output = Command::new("pdftotext")
                .args(["-l", &self.max_pages.to_string(), path.to_str().unwrap(), "-"])
                .output();

            if let Ok(output) = output {
                if output.status.success() {
                    let text = String::from_utf8_lossy(&output.stdout).to_string();
                    return Ok(PreviewContent::Text(text));
                }
            }
        }

        Err("pdftotext not found".to_string())
    }
}
```

**Step 6: Compilar y verificar**

Run: `cargo build`
Expected: Compilación exitosa

**Step 7: Commit**

```rust
git add src/preview/
git commit -m "feat: add preview system

- TextPreview for plain text files
- CodePreview with syntax highlighting
- ImagePreview using chafa for ASCII art
- PdfPreview using pdftotext
- MarkdownPreview for MD files

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
 4: Editor```

---

## Fase de Código

### Task 4: Editor estilo VSCode

**Files:**
- Create: `src/editor/mod.rs`
- Create: `src/editor/buffer.rs`
- Create: `src/editor/cursor.rs`
- Create: `src/editor/syntax.rs`

**Step 1: Crear EditorBuffer**

```rust
// src/editor/buffer.rs
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct EditorBuffer {
    pub content: Vec<String>,
    pub path: Option<PathBuf>,
    pub is_modified: bool,
    pub cursor_line: usize,
    pub cursor_col: usize,
    pub scroll_offset: usize,
    pub selection_start: Option<(usize, usize)>,
    pub selection_end: Option<(usize, usize)>,
}

impl EditorBuffer {
    pub fn new() -> Self {
        EditorBuffer {
            content: vec![String::new()],
            path: None,
            is_modified: false,
            cursor_line: 0,
            cursor_col: 0,
            scroll_offset: 0,
            selection_start: None,
            selection_end: None,
        }
    }

    pub fn from_file(path: PathBuf) -> std::io::Result<Self> {
        let content = std::fs::read_to_string(&path)?
            .lines()
            .map(|s| s.to_string())
            .collect();

        Ok(EditorBuffer {
            content,
            path: Some(path),
            is_modified: false,
            cursor_line: 0,
            cursor_col: 0,
            scroll_offset: 0,
            selection_start: None,
            selection_end: None,
        })
    }

    pub fn insert_char(&mut self, ch: char) {
        if self.cursor_line >= self.content.len() {
            self.content.push(String::new());
        }

        let line = &mut self.content[self.cursor_line];
        let pos = self.cursor_col.min(line.len());
        line.insert(pos, ch);
        self.cursor_col += 1;
        self.is_modified = true;
    }

    pub fn insert_newline(&mut self) {
        if self.cursor_line >= self.content.len() {
            self.content.push(String::new());
        }

        let current_line = self.content[self.cursor_line].clone();
        let (_, after) = current_line.split_at(self.cursor_col);

        self.content[self.cursor_line] = current_line[..self.cursor_col].to_string();
        self.content.insert(self.cursor_line + 1, after.to_string());

        self.cursor_line += 1;
        self.cursor_col = 0;
        self.is_modified = true;
    }

    pub fn delete_char(&mut self) {
        if self.cursor_line >= self.content.len() { return; }

        let line = &mut self.content[self.cursor_line];

        if self.cursor_col > 0 {
            line.remove(self.cursor_col - 1);
            self.cursor_col -= 1;
        } else if self.cursor_line > 0 {
            // Merge with previous line
            let prev_line = self.content.remove(self.cursor_line);
            self.cursor_line -= 1;
            self.cursor_col = self.content[self.cursor_line].len();
            self.content[self.cursor_line].push_str(&prev_line);
        }
        self.is_modified = true;
    }

    pub fn move_cursor(&mut self, line_delta: i32, col_delta: i32) {
        let new_line = (self.cursor_line as i32 + line_delta).max(0) as usize;
        let new_col = (self.cursor_col as i32 + col_delta).max(0) as usize;

        if new_line < self.content.len() {
            self.cursor_line = new_line;
            self.cursor_col = new_col.min(self.content[new_line].len());
        }

        // Auto-scroll
        if self.cursor_line < self.scroll_offset {
            self.scroll_offset = self.cursor_line;
        }
    }

    pub fn save(&self) -> std::io::Result<()> {
        if let Some(ref path) = self.path {
            let content = self.content.join("\n");
            std::fs::write(path, content)?;
        }
        Ok(())
    }

    pub fn get_line(&self, index: usize) -> Option<&String> {
        self.content.get(index)
    }

    pub fn total_lines(&self) -> usize {
        self.content.len()
    }
}
```

**Step 2: Crear Cursor y selection**

```rust
// src/editor/cursor.rs
use super::buffer::EditorBuffer;

#[derive(Debug, Clone)]
pub struct Cursor {
    pub line: usize,
    pub col: usize,
    pub visible: bool,
}

impl Cursor {
    pub fn new(line: usize, col: usize) -> Self {
        Cursor { line, col, visible: true }
    }

    pub fn move_to(&mut self, buffer: &EditorBuffer, line: usize, col: usize) {
        self.line = line.min(buffer.total_lines().saturating_sub(1));
        self.col = col.min(buffer.get_line(self.line).map(|l| l.len()).unwrap_or(0));
    }
}
```

**Step 3: Compilar y verificar**

Run: `cargo build`
Expected: Compilación exitosa

**Step 4: Commit**

```bash
git add src/editor/
git commit -m "feat: add code editor

- EditorBuffer with text manipulation
- Cursor movement and selection
- File loading and saving

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 5: Integración Git

### Task 5: Visor de cambios Git

**Files:**
- Create: `src/git/mod.rs`
- Create: `src/git/status.rs`
- Create: `src/git/diff.rs`

**Step 1: Crear GitManager**

```rust
// src/git/mod.rs
use git2::{Repository, StatusOptions, DiffOptions};
use std::path::Path;

pub mod status;
pub mod diff;

pub struct GitManager {
    repo: Option<Repository>,
    path: Path,
}

#[derive(Debug, Clone)]
pub struct FileStatus {
    pub path: String,
    pub status: StatusType,
    pub staged: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum StatusType {
    Modified,
    Added,
    Deleted,
    Renamed,
    Untracked,
    Ignored,
    Unmodified,
}

impl GitManager {
    pub fn new(path: Path) -> Self {
        let repo = Repository::open(&path).ok();
        GitManager { repo, path }
    }

    pub fn is_repo(&self) -> bool {
        self.repo.is_some()
    }

    pub fn get_status(&self) -> Result<Vec<FileStatus>, String> {
        let repo = self.repo.as_ref().ok_or("Not a git repository")?;

        let mut opts = StatusOptions::new();
        opts.include_untracked(true)
            .recurse_untracked_dirs(true);

        let statuses = repo.statuses(Some(&mut opts))
            .map_err(|e| e.to_string())?;

        let mut result = Vec::new();

        for entry in statuses.iter() {
            let path = entry.path().unwrap_or("").to_string();
            let status = entry.status();

            let status_type = if status.is_index_new() || status.is_wt_new() {
                StatusType::Untracked
            } else if status.is_index_modified() || status.is_wt_modified() {
                StatusType::Modified
            } else if status.is_index_deleted() || status.is_wt_deleted() {
                StatusType::Deleted
            } else if status.is_index_renamed() || status.is_wt_renamed() {
                StatusType::Renamed
            } else if status.is_ignored() {
                StatusType::Ignored
            } else {
                StatusType::Unmodified
            };

            let staged = status.is_index_new() || status.is_index_modified() ||
                        status.is_index_deleted() || status.is_index_renamed();

            result.push(FileStatus { path, status: status_type, staged });
        }

        Ok(result)
    }

    pub fn get_diff(&self, file_path: Option<&str>) -> Result<String, String> {
        let repo = self.repo.as_ref().ok_or("Not a git repository")?;

        let mut opts = DiffOptions::new();
        if let Some(path) = file_path {
            opts.pathspec(path);
        }

        let diff = repo.diff_index_to_workdir(None, Some(&mut opts))
            .map_err(|e| e.to_string())?;

        let mut diff_text = String::new();
        diff.print(git2::DiffFormat::Patch, |_delta, _hunk, line| {
            let prefix = match line.origin() {
                '+' => "+",
                '-' => "-",
                ' ' => " ",
                _ => "",
            };
            diff_text.push_str(prefix);
            if let Ok(content) = std::str::from_utf8(line.content()) {
                diff_text.push_str(content);
            }
            true
        }).map_err(|e| e.to_string())?;

        Ok(diff_text)
    }

    pub fn get_branches(&self) -> Result<Vec<String>, String> {
        let repo = self.repo.as_ref().ok_or("Not a git repository")?;

        let mut branches = Vec::new();

        for branch in repo.branches(Some(git2::BranchType::Local)).map_err(|e| e.to_string())? {
            if let Ok((branch, _)) = branch {
                if let Ok(name) = branch.name() {
                    if let Some(name) = name {
                        branches.push(name.to_string());
                    }
                }
            }
        }

        Ok(branches)
    }
}
```

**Step 2: Compilar y verificar**

Run: `cargo build`
Expected: Compilación exitosa

**Step 3: Commit**

```bash
git add src/git/
git commit -m "feat: add git integration

- GitManager for repository operations
- File status tracking (modified, added, deleted)
- Diff viewing
- Branch listing

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 6: Formateo de Código

### Task 6: Formateadores JSON y LDAP

**Files:**
- Create: `src/utils/formatter.rs`

**Step 1: Crear formateadores**

```rust
// src/utils/formatter.rs
use serde_json::Value;
use regex::Regex;

pub fn format_json(content: &str, indent: usize) -> Result<String, String> {
    let value: Value = serde_json::from_str(content)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    let formatter = serde_json::ser::PrettyFormatter::with_indent(b" ".repeat(indent).as_bytes());
    let mut buf = Vec::new();
    let mut serializer = serde_json::Serializer::with_formatter(&mut buf, formatter);

    value.serialize(&mut serializer)
        .map_err(|e| format!("Serialization error: {}", e))?;

    String::from_utf8(buf).map_err(|e| e.to_string())
}

pub fn minify_json(content: &str) -> Result<String, String> {
    let value: Value = serde_json::from_str(content)
        .map_err(|e| format!("Invalid JSON: {}", e))?;
    serde_json::to_string(&value).map_err(|e| e.to_string())
}

pub fn format_ldap(content: &str) -> String {
    // LDAP filter formatting
    // Example: (|(objectClass=user)(objectClass=group)) -> expand
    let mut result = content.to_string();

    // Add newlines after each )
    let re = Regex::new(r"\)").unwrap();
    result = re.replace_all(&result, ")\n").to_string();

    // Indent after |( or &(
    let re = Regex::new(r"\(\|").unwrap();
    result = re.replace_all(&result, "(|").to_string();
    let re = Regex::new(r"\(\&").unwrap();
    result = re.replace_all(&result, "(&").to_string();

    // Format DN (Distinguished Name)
    let re = Regex::new(r",(?=[A-Za-z]=)").unwrap();
    result = re.replace_all(&result, ",\n").to_string();

    result
}

pub fn format_ldap_filter(filter: &str) -> String {
    let mut formatted = String::new();
    let mut indent = 0;
    let mut in_parens = false;

    for ch in filter.chars() {
        match ch {
            '(' => {
                formatted.push(ch);
                in_parens = true;
                indent += 2;
            }
            ')' => {
                indent = indent.saturating_sub(2);
                formatted.push('\n');
                formatted.push_str(&" ".repeat(indent));
                formatted.push(ch);
                in_parens = false;
            }
            '|' | '&' => {
                formatted.push_str("\n  ");
                formatted.push(ch);
            }
            _ => formatted.push(ch),
        }
    }

    formatted
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_json() {
        let input = r#"{"name":"test","value":123}"#;
        let result = format_json(input, 2);
        assert!(result.is_ok());
    }

    #[test]
    fn test_format_ldap() {
        let input = "cn=user,ou=users,dc=example,dc=com";
        let result = format_ldap(input);
        assert!(result.contains('\n'));
    }
}
```

**Step 2: Agregar dependencia**

```toml
# En Cargo.toml agregar:
regex = "1"
```

**Step 3: Compilar y verificar**

Run: `cargo build`
Expected: Compilación exitosa

**Step 4: Commit**

```bash
git add src/utils/
git commit -m "feat: add code formatters

- JSON formatter and minifier
- LDAP filter/DN formatter

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 7: UI Principal

### Task 7: Integrar todo en UI principal

**Files:**
- Modify: `src/main.rs`

**Step 1: Crear aplicación TUI completa**

```rust
// src/main.rs - Versión completa
mod filesystem;
mod preview;
mod editor;
mod git;
mod utils;

use std::path::PathBuf;
use ratatui::{prelude::*, widgets::*};
use crossterm::{event::{self, Event, KeyCode, KeyEventKind}, terminal::{disable_raw_mode, enable_raw_mode}};
use filesystem::{FileEntry, DirNavigator, SortBy};
use preview::{PreviewManager, PreviewContent};
use editor::buffer::EditorBuffer;
use git::GitManager;
use utils::formatter;

enum Mode {
    FileBrowser,
    Preview,
    Editor,
    GitStatus,
}

struct AppState {
    mode: Mode,
    navigator: DirNavigator,
    selected_index: usize,
    preview_manager: PreviewManager,
    editor: Option<EditorBuffer>,
    git_manager: Option<GitManager>,
    search_query: String,
    message: String,
}

impl AppState {
    fn new() -> Self {
        let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
        let navigator = DirNavigator::new(cwd.clone());
        let git_manager = GitManager::new(cwd);

        AppState {
            mode: Mode::FileBrowser,
            navigator,
            selected_index: 0,
            preview_manager: PreviewManager::new(),
            editor: None,
            git_manager: Some(git_manager),
            search_query: String::new(),
            message: String::new(),
        }
    }
}

fn render_file_browser(frame: &mut Frame, area: Rect, state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
            Constraint::Length(1),
        ])
        .split(area);

    // Header
    let header = Paragraph::new(format!(
        "📁 {} | Press: q=quit, Enter=open, Space=preview, e=edit, g=git, /=search, h=hidden, .=parent",
        state.navigator.current_path.display()
    )).style(Style::default().fg(Color::Cyan));
    frame.render_widget(header, chunks[0]);

    // File list
    let files: Vec<ListItem> = state.navigator.entries.iter().enumerate().map(|(i, entry)| {
        let icon = if entry.is_dir { "📂" } else { "📄" };
        let suffix = if entry.is_hidden { " [hidden]" } else { "" };
        let line = format!("{} {} ({}){}", icon, entry.name, format_size(entry.size), suffix);
        let style = if i == state.selected_index {
            Style::default().fg(Color::Black).bg(Color::LightGreen)
        } else if entry.is_dir {
            Style::default().fg(Color::Blue)
        } else {
            Style::default()
        };
        ListItem::new(line).style(style)
    }).collect();

    let list = List::new(files)
        .block(Block::default().borders(Borders::ALL).title("Files"))
        .style(Style::default().fg(Color::White));
    frame.render_widget(list, chunks[1]);

    // Status bar
    let status = Paragraph::new(state.message.as_str())
        .style(Style::default().fg(Color::Yellow));
    frame.render_widget(status, chunks[2]);
}

fn render_preview(frame: &mut Frame, area: Rect, state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
        ])
        .split(area);

    let header = Paragraph::new("Preview Mode | q=back, r=refresh")
        .style(Style::default().fg(Color::Cyan));
    frame.render_widget(header, chunks[0]);

    if state.selected_index < state.navigator.entries.len() {
        let entry = &state.navigator.entries[state.selected_index];
        if !entry.is_dir {
            match state.preview_manager.get_preview(&entry.path) {
                Ok(PreviewContent::Text(text)) => {
                    let preview = Paragraph::new(text)
                        .block(Block::default().borders(Borders::ALL))
                        .scroll((0, 0));
                    frame.render_widget(preview, chunks[1]);
                }
                Ok(PreviewContent::Error(e)) => {
                    let error = Paragraph::new(format!("Error: {}", e))
                        .style(Style::default().fg(Color::Red));
                    frame.render_widget(error, chunks[1]);
                }
                Err(e) => {
                    let error = Paragraph::new(format!("Error: {}", e))
                        .style(Style::default().fg(Color::Red));
                    frame.render_widget(error, chunks[1]);
                }
            }
        }
    }
}

fn render_editor(frame: &mut Frame, area: Rect, state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
            Constraint::Length(1),
        ])
        .split(area);

    let header = Paragraph::new("Editor Mode | Ctrl+S=save, Ctrl+Q=quit, Esc=back")
        .style(Style::default().fg(Color::Yellow));
    frame.render_widget(header, chunks[0]);

    if let Some(ref editor) = state.editor {
        let lines: Vec<Line> = (0..editor.total_lines()).map(|i| {
            let line_num = format!("{:>4}", i + 1);
            let content = editor.get_line(i).cloned().unwrap_or_default();
            Line::from(vec![
                Span::raw(line_num).style(Style::default().fg(Color::DarkGray)),
                Span::raw(" "),
                Span::raw(content),
            ])
        }).collect();

        let text = Text::from(lines);
        let paragraph = Paragraph::new(text)
            .block(Block::default().borders(Borders::ALL))
            .scroll((editor.scroll_offset as u16, 0));
        frame.render_widget(paragraph, chunks[1]);

        let status = format!("Line: {}, Col: {}, Modified: {}",
            editor.cursor_line + 1,
            editor.cursor_col + 1,
            if editor.is_modified { "Yes" } else { "No" }
        );
        let status_bar = Paragraph::new(status)
            .style(Style::default().fg(Color::Green));
        frame.render_widget(status_bar, chunks[2]);
    }
}

fn render_git_status(frame: &mut Frame, area: Rect, state: &AppState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
        ])
        .split(area);

    let header = Paragraph::new("Git Status | q=back, d=diff, r=refresh")
        .style(Style::default().fg(Color::Magenta));
    frame.render_widget(header, chunks[0]);

    if let Some(ref git) = state.git_manager {
        match git.get_status() {
            Ok(statuses) => {
                let items: Vec<ListItem> = statuses.iter().map(|s| {
                    let icon = match s.status {
                        git::StatusType::Modified => "M",
                        git::StatusType::Added => "A",
                        git::StatusType::Deleted => "D",
                        git::StatusType::Renamed => "R",
                        git::StatusType::Untracked => "?",
                        _ => " ",
                    };
                    let staged = if s.staged { "+" } else { " " };
                    ListItem::new(format!("{}{} {}", staged, icon, s.path))
                }).collect();

                let list = List::new(items)
                    .block(Block::default().borders(Borders::ALL).title("Git Status"));
                frame.render_widget(list, chunks[1]);
            }
            Err(e) => {
                let error = Paragraph::new(format!("Error: {}", e))
                    .style(Style::default().fg(Color::Red));
                frame.render_widget(error, chunks[1]);
            }
        }
    }
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

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut terminal = Terminal::new(CrosstermBackend::new(std::io::stdout()))?;
    let mut state = AppState::new();

    loop {
        terminal.draw(|f| {
            let area = f.size();

            match state.mode {
                Mode::FileBrowser => render_file_browser(f, area, &state),
                Mode::Preview => render_preview(f, area, &state),
                Mode::Editor => render_editor(f, area, &state),
                Mode::GitStatus => render_git_status(f, area, &state),
            }
        })?;

        if let Event::Key(key) = event::read()? {
            if key.kind == KeyEventKind::Press {
                match state.mode {
                    Mode::FileBrowser => {
                        match key.code {
                            KeyCode::Char('q') => break,
                            KeyCode::Char('j') | KeyCode::Down => {
                                state.selected_index = (state.selected_index + 1)
                                    .min(state.navigator.entries.len().saturating_sub(1));
                            }
                            KeyCode::Char('k') | KeyCode::Up => {
                                state.selected_index = state.selected_index.saturating_sub(1);
                            }
                            KeyCode::Enter => {
                                if state.selected_index < state.navigator.entries.len() {
                                    let entry = &state.navigator.entries[state.selected_index];
                                    if entry.is_dir {
                                        state.navigator.navigate_to(&entry.path);
                                        state.selected_index = 0;
                                    }
                                }
                            }
                            KeyCode::Char(' ') => {
                                state.mode = Mode::Preview;
                            }
                            KeyCode::Char('e') => {
                                if state.selected_index < state.navigator.entries.len() {
                                    let entry = &state.navigator.entries[state.selected_index];
                                    if !entry.is_dir {
                                        if let Ok(buffer) = EditorBuffer::from_file(entry.path.clone()) {
                                            state.editor = Some(buffer);
                                            state.mode = Mode::Editor;
                                        }
                                    }
                                }
                            }
                            KeyCode::Char('g') => {
                                state.mode = Mode::GitStatus;
                            }
                            KeyCode::Char('.') => {
                                state.navigator.navigate_up();
                                state.selected_index = 0;
                            }
                            KeyCode::Char('h') => {
                                state.navigator.show_hidden = !state.navigator.show_hidden;
                                state.navigator.refresh();
                            }
                            KeyCode::Char('/') => {
                                state.search_query.clear();
                                // Handle search input
                            }
                            KeyCode::Char('s') => {
                                // Sort cycle: name -> size -> modified -> type
                                state.navigator.sort_by = match state.navigator.sort_by {
                                    SortBy::Name => SortBy::Size,
                                    SortBy::Size => SortBy::Modified,
                                    SortBy::Modified => SortBy::Type,
                                    SortBy::Type => SortBy::Name,
                                };
                                state.navigator.sort();
                            }
                            _ => {}
                        }
                    }
                    Mode::Preview => {
                        if key.code == KeyCode::Char('q') || key.code == KeyCode::Esc {
                            state.mode = Mode::FileBrowser;
                        }
                    }
                    Mode::Editor => {
                        if let Some(ref mut editor) = state.editor {
                            match key.code {
                                KeyCode::Char('q') if key.modifiers.contains(event::KeyModifiers::CONTROL) => {
                                    break;
                                }
                                KeyCode::Char('s') if key.modifiers.contains(event::KeyModifiers::CONTROL) => {
                                    if let Err(e) = editor.save() {
                                        state.message = format!("Error saving: {}", e);
                                    } else {
                                        state.message = "Saved!".to_string();
                                    }
                                }
                                KeyCode::Esc => {
                                    state.mode = Mode::FileBrowser;
                                    state.editor = None;
                                }
                                KeyCode::Char(c) => {
                                    editor.insert_char(c);
                                }
                                KeyCode::Enter => {
                                    editor.insert_newline();
                                }
                                KeyCode::Backspace => {
                                    editor.delete_char();
                                }
                                KeyCode::Left => {
                                    editor.move_cursor(0, -1);
                                }
                                KeyCode::Right => {
                                    editor.move_cursor(0, 1);
                                }
                                KeyCode::Up => {
                                    editor.move_cursor(-1, 0);
                                }
                                KeyCode::Down => {
                                    editor.move_cursor(1, 0);
                                }
                                _ => {}
                            }
                        }
                    }
                    Mode::GitStatus => {
                        if key.code == KeyCode::Char('q') || key.code == KeyCode::Esc {
                            state.mode = Mode::FileBrowser;
                        }
                        if key.code == KeyCode::Char('r') {
                            if let Some(ref mut git) = state.git_manager {
                                // Refresh git status
                            }
                        }
                    }
                }
            }
        }
    }

    disable_raw_mode()?;
    Ok(())
}
```

**Step 2: Compilar y verificar**

Run: `cargo build --release`
Expected: Compilación exitosa

**Step 3: Commit**

```bash
git add src/main.rs Cargo.toml
git commit -m "feat: complete TUI application

- File browser with navigation
- Multi-format preview system
- Code editor with basic editing
- Git status viewer

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 8: Instalador

### Task 8: Crear script de instalación

**Files:**
- Create: `install-rust.sh`

**Step 1: Crear script de instalación**

```bash
#!/bin/bash
set -e

echo "📦 MD TUI - Rust Installer"
echo "=========================="

# Install system dependencies
echo "📥 Installing system dependencies..."
sudo apt update
sudo apt install -y \
    build-essential \
    git \
    curl \
    chafa \
    exiftool \
    poppler-utils \
    fzf \
    fd-find \
    ripgrep

# Install Rust if not present
if ! command -v rustc &> /dev/null; then
    echo "🧊 Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Build the application
echo "🔨 Building MD TUI..."
cargo build --release

# Install binary
echo "📲 Installing mdtui binary..."
sudo cp target/release/mdtui /usr/local/bin/mdtui
sudo chmod +x /usr/local/bin/mdtui

# Create completion (optional)
echo "✅ Installation complete!"
echo "Run 'mdtui' to start"
```

**Step 2: Commit**

```bash
git add install-rust.sh
git commit -m "feat: add Rust installation script

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Fase 9: Push y Limpieza

### Task 9: Push a GitHub

**Step 1: Push branch**

```bash
git push -u origin rust-version
```

**Step 2: Crear PR (optional)**

```bash
gh pr create --title "feat: Rust rewrite" --body "Complete rewrite in Rust with enhanced features"
```

---

## Resumen de Commits

| # | Mensaje |
|---|---------|
| 1 | Initialize Rust project with Cargo.toml |
| 2 | Add filesystem module |
| 3 | Add preview system |
| 4 | Add code editor |
| 5 | Add git integration |
| 6 | Add code formatters |
| 7 | Complete TUI application |
| 8 | Add Rust installation script |
