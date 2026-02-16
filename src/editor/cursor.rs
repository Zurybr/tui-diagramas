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
