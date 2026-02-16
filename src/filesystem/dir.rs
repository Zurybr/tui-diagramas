// src/filesystem/dir.rs
use super::FileEntry;
use std::path::PathBuf;
use walkdir::WalkDir;

pub struct DirNavigator {
    pub current_path: PathBuf,
    pub entries: Vec<FileEntry>,
    pub show_hidden: bool,
    pub sort_by: super::SortBy,
    pub filter: Option<String>,
}

impl DirNavigator {
    pub fn new(path: PathBuf) -> Self {
        let mut nav = DirNavigator {
            current_path: path,
            entries: Vec::new(),
            show_hidden: false,
            sort_by: super::SortBy::Name,
            filter: None,
        };
        nav.refresh();
        nav
    }

    pub fn refresh(&mut self) {
        self.entries.clear();
        let path = &self.current_path;

        for entry in WalkDir::new(path).max_depth(1) {
            if let Ok(entry) = entry {
                let entry_path = entry.path();
                if entry_path == path { continue; }

                if let Some(file_entry) = FileEntry::from_path(entry_path) {
                    if !self.show_hidden && file_entry.is_hidden { continue; }
                    if let Some(ref filter) = self.filter {
                        if !file_entry.name.to_lowercase().contains(&filter.to_lowercase()) {
                            continue;
                        }
                    }
                    self.entries.push(file_entry);
                }
            }
        }

        self.sort();
    }

    pub fn sort(&mut self) {
        match self.sort_by {
            super::SortBy::Name => self.entries.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase())),
            super::SortBy::Size => self.entries.sort_by(|a, b| b.size.cmp(&a.size)),
            super::SortBy::Modified => self.entries.sort_by(|a, b| b.modified.cmp(&a.modified)),
            super::SortBy::Type => self.entries.sort_by(|a, b| {
                match (a.is_dir, b.is_dir) {
                    (true, false) => std::cmp::Ordering::Less,
                    (false, true) => std::cmp::Ordering::Greater,
                    _ => a.extension.cmp(&b.extension),
                }
            }),
        }
    }

    pub fn navigate_to(&mut self, path: &std::path::Path) {
        if path.is_dir() {
            self.current_path = path.to_path_buf();
            self.refresh();
        }
    }

    pub fn navigate_up(&mut self) {
        if let Some(parent) = self.current_path.parent() {
            self.current_path = parent.to_path_buf();
            self.refresh();
        }
    }

    pub fn search(&mut self, query: &str) {
        self.filter = Some(query.to_string());
        self.refresh();
    }
}
