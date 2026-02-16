// src/filesystem/file.rs
#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_file_entry_from_path() {
        let path = env::current_dir().unwrap();
        let entry = FileEntry::from_path(&path);
        assert!(entry.is_some());
    }
}
