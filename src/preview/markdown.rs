// src/preview/markdown.rs
use super::*;
use std::fs;

pub struct MarkdownPreview {
    max_lines: usize,
}

impl MarkdownPreview {
    pub fn new() -> Self {
        MarkdownPreview { max_lines: 500 }
    }
}

impl PreviewProvider for MarkdownPreview {
    fn can_preview(&self, path: &Path) -> bool {
        path.extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_lowercase() == "md")
            .unwrap_or(false)
    }

    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        fs::read_to_string(path)
            .map(|content| {
                let lines: Vec<&str> = content.lines().take(self.max_lines).collect();
                PreviewContent::Text(lines.join("\n"))
            })
            .map_err(|e| e.to_string())
    }
}
