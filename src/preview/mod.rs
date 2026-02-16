// src/preview/mod.rs
use std::path::Path;
use std::fs;
use std::process::Command;

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

/// Proveedor genérico para cualquier archivo - siempre puede hacer preview
pub struct GenericPreview;

impl PreviewProvider for GenericPreview {
    fn can_preview(&self, _path: &Path) -> bool {
        true // Siempre disponible como fallback
    }

    fn generate_preview(&self, path: &Path) -> Result<PreviewContent, String> {
        let metadata = fs::metadata(path).map_err(|e| e.to_string())?;
        let size = metadata.len();
        let file_name = path.file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| "Unknown".to_string());

        // Intentar leer como texto primero
        if let Ok(content) = fs::read_to_string(path) {
            let preview_content = if content.len() > 5000 {
                content.chars().take(5000).collect::<String>() + "\n\n... (truncated)"
            } else {
                content
            };
            return Ok(PreviewContent::Text(preview_content));
        }

        // Si no es texto, mostrar información del archivo
        let extension = path.extension()
            .map(|e| e.to_string_lossy().to_string())
            .unwrap_or_else(|| "unknown".to_string());

        let mut info = format!(
            "📄 File: {}\n📁 Size: {} bytes\n🔧 Type: {}\n\n",
            file_name, size, extension
        );

        // Intentar con herramientas externas
        if extension == "doc" || extension == "docx" {
            if let Ok(output) = Command::new("pandoc").args(["-t", "plain", path.to_str().unwrap()]).output() {
                if output.status.success() {
                    let text: String = String::from_utf8_lossy(&output.stdout).chars().take(5000).collect();
                    return Ok(PreviewContent::Text(info + &text));
                }
            }
            info += "⚠️ Install 'pandoc' to preview Word documents";
        } else if extension == "xlsx" || extension == "xls" {
            if which::which("xlsx2csv").is_ok() {
                if let Ok(output) = Command::new("xlsx2csv").arg(path.to_str().unwrap()).output() {
                    if output.status.success() {
                        let text: String = String::from_utf8_lossy(&output.stdout).chars().take(5000).collect();
                        return Ok(PreviewContent::Text(info + &text));
                    }
                }
            }
            info += "⚠️ Install 'xlsx2csv' to preview Excel files";
        } else if extension == "pptx" || extension == "ppt" {
            if which::which("pdftotext").is_ok() {
                // No hay forma directa de convertir PPT a texto
            }
            info += "⚠️ Install 'libreoffice' to convert PowerPoint";
        } else if extension == "zip" || extension == "tar" || extension == "gz" || extension == "rar" || extension == "7z" {
            // Listar contenido del archivo
            let listing = if extension == "zip" {
                Command::new("unzip").args(["-l", path.to_str().unwrap()]).output()
            } else if extension == "tar" || extension == "gz" {
                Command::new("tar").args(["-tvf", path.to_str().unwrap()]).output()
            } else {
                Command::new("7z").args(["l", path.to_str().unwrap()]).output()
            };

            if let Ok(output) = listing {
                if output.status.success() {
                    let list = String::from_utf8_lossy(&output.stdout);
                    info += &format!("\n📦 Archive contents:\n{}", list.chars().take(3000).collect::<String>());
                }
            }
        } else if extension == "mp3" || extension == "wav" || extension == "flac" || extension == "ogg" || extension == "m4a" {
            if which::which("mediainfo").is_ok() {
                if let Ok(output) = Command::new("mediainfo").arg(path.to_str().unwrap()).output() {
                    if output.status.success() {
                        let info_audio = String::from_utf8_lossy(&output.stdout);
                        return Ok(PreviewContent::Text(info + &info_audio));
                    }
                }
            }
            info += &format!("\n🎵 Audio file: {} bytes", size);
        } else if extension == "mp4" || extension == "avi" || extension == "mkv" || extension == "mov" || extension == "webm" {
            if which::which("mediainfo").is_ok() {
                if let Ok(output) = Command::new("mediainfo").arg(path.to_str().unwrap()).output() {
                    if output.status.success() {
                        let info_video = String::from_utf8_lossy(&output.stdout);
                        return Ok(PreviewContent::Text(info + &info_video));
                    }
                }
            }
            info += &format!("\n🎬 Video file: {} bytes", size);
        } else if extension == "exe" || extension == "dll" || extension == "so" || extension == "dylib" {
            if which::which("file").is_ok() {
                if let Ok(output) = Command::new("file").arg(path.to_str().unwrap()).output() {
                    if output.status.success() {
                        let file_info = String::from_utf8_lossy(&output.stdout);
                        info += &format!("\n🔧 {}", file_info);
                    }
                }
            }
        } else if extension == "iso" {
            if which::which("isoinfo").is_ok() {
                if let Ok(output) = Command::new("isoinfo").args(["-l", "-i", path.to_str().unwrap()]).output() {
                    if output.status.success() {
                        let list = String::from_utf8_lossy(&output.stdout);
                        info += &format!("\n💿 ISO contents:\n{}", list.chars().take(3000).collect::<String>());
                    }
                }
            }
        } else {
            // Para cualquier otro archivo binario
            if which::which("file").is_ok() {
                if let Ok(output) = Command::new("file").arg(path.to_str().unwrap()).output() {
                    if output.status.success() {
                        let file_info = String::from_utf8_lossy(&output.stdout);
                        info += &format!("\n🔍 Detected: {}", file_info);
                    }
                }
            }
        }

        Ok(PreviewContent::Binary(info))
    }
}

pub struct PreviewManager {
    providers: Vec<Box<dyn PreviewProvider>>,
}

impl PreviewManager {
    pub fn new() -> Self {
        let mut manager = PreviewManager { providers: Vec::new() };
        // Proveedores específicos primero
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
        // Primero intentar con todos los proveedores específicos
        for provider in &self.providers {
            if provider.can_preview(path) {
                match provider.generate_preview(path) {
                    Ok(PreviewContent::Text(text)) if !text.is_empty() => return Ok(PreviewContent::Text(text)),
                    Ok(PreviewContent::Text(_)) => {}, // Vacío, continuar
                    Ok(other) => return Ok(other), // Binary, Image, Error
                    Err(_) => {}, // Error, continuar
                }
            }
        }
        // Si ninguno funcionó, usar el genérico como último recurso
        // Intentar leer el archivo directamente
        match fs::read_to_string(path) {
            Ok(content) => Ok(PreviewContent::Text(content)),
            Err(e) => Ok(PreviewContent::Binary(format!("Cannot read file: {}", e)))
        }
    }
}
