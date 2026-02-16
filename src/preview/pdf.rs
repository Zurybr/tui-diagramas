// src/preview/pdf.rs
use super::*;
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
