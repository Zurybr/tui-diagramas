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
