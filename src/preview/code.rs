// src/preview/code.rs
use super::*;
use std::fs;

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
            _ => "plaintext",
        }
    }
}

impl PreviewProvider for CodePreview {
    fn can_preview(&self, path: &Path) -> bool {
        let code_extensions = ["rs", "py", "js", "ts", "tsx", "jsx", "java", "c", "cpp", "h", "hpp", "go", "rb", "php", "swift", "kt", "scala", "cs", "hs", "clj", "ex", "exs", "erl", "lua", "pl", "sh", "bash", "zsh", "sql", "graphql", "svelte", "vue", "css", "scss", "sass", "less", "html", "htm"];
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
