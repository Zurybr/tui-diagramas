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
