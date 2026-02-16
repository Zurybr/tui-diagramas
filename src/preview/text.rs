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
        let text_extensions = ["txt", "md", "json", "xml", "yaml", "yml", "toml", "ini", "cfg", "conf", "log", "csv", "sql", "sh", "bash", "zsh", "py", "rs", "js", "ts", "java", "c", "cpp", "h", "hpp", "go", "rb", "php", "swift", "kt", "scala", "r", "lua", "pl", "ex", "exs", "erl", "hs", "clj", "vim", "gitignore", "env", "editorconfig"];
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
