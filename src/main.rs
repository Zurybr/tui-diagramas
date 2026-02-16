// src/main.rs - Complete TUI Application
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
                Ok(PreviewContent::Binary(s)) => {
                    let bin = Paragraph::new(s)
                        .style(Style::default().fg(Color::Yellow));
                    frame.render_widget(bin, chunks[1]);
                }
                Ok(PreviewContent::Image(_)) => {
                    let img = Paragraph::new("[Image preview]")
                        .style(Style::default().fg(Color::Blue));
                    frame.render_widget(img, chunks[1]);
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
                            KeyCode::Char('q') => {
                                // Cambiar al directorio actual antes de salir
                                let _ = std::env::set_current_dir(&state.navigator.current_path);
                                break;
                            }
                            KeyCode::Char('j') | KeyCode::Down => {
                                state.selected_index = (state.selected_index + 1)
                                    .min(state.navigator.entries.len().saturating_sub(1));
                            }
                            KeyCode::Char('k') | KeyCode::Up => {
                                state.selected_index = state.selected_index.saturating_sub(1);
                            }
                            KeyCode::Enter => {
                                if state.selected_index < state.navigator.entries.len() {
                                    let is_dir = state.navigator.entries[state.selected_index].is_dir;
                                    let path = state.navigator.entries[state.selected_index].path.clone();
                                    if is_dir {
                                        state.navigator.navigate_to(&path);
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
                                    let _ = std::env::set_current_dir(&state.navigator.current_path);
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
                            // Refresh git status handled automatically
                        }
                    }
                }
            }
        }
    }

    disable_raw_mode()?;
    Ok(())
}
