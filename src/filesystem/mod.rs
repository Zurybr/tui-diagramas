// src/filesystem/mod.rs
pub mod dir;
pub mod file;

pub use dir::DirNavigator;

use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SortBy {
    Name,
    Size,
    Modified,
    Type,
}

#[derive(Debug, Clone)]
pub struct FileEntry {
    pub name: String,
    pub path: PathBuf,
    pub is_dir: bool,
    pub size: u64,
    pub modified: Option<chrono::DateTime<chrono::Utc>>,
    pub is_hidden: bool,
    pub extension: Option<String>,
}

impl FileEntry {
    pub fn from_path(path: &std::path::Path) -> Option<Self> {
        let metadata = std::fs::metadata(path).ok()?;
        let name = path.file_name()?.to_string_lossy().to_string();
        let is_dir = metadata.is_dir();
        let size = metadata.len();
        let modified = metadata.modified().ok()
            .map(|t| chrono::DateTime::<chrono::Utc>::from(t));
        let is_hidden = name.starts_with('.');
        let extension = path.extension().map(|e| e.to_string_lossy().to_string());

        Some(FileEntry { name, path: path.to_path_buf(), is_dir, size, modified, is_hidden, extension })
    }
}
