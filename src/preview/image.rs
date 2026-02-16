// src/preview/image.rs
use super::*;
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
