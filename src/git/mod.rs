// src/git/mod.rs
use std::path::PathBuf;
use std::process::Command;

pub mod status;
pub mod diff;

pub struct GitManager {
    path: PathBuf,
    is_repo: bool,
}

#[derive(Debug, Clone)]
pub struct FileStatus {
    pub path: String,
    pub status: StatusType,
    pub staged: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum StatusType {
    Modified,
    Added,
    Deleted,
    Renamed,
    Untracked,
    Ignored,
    Unmodified,
}

impl GitManager {
    pub fn new(path: PathBuf) -> Self {
        let is_repo = Command::new("git")
            .args(["-C", path.to_str().unwrap_or("."), "rev-parse", "--is-inside-work-tree"])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false);

        GitManager { path, is_repo }
    }

    pub fn is_repo(&self) -> bool {
        self.is_repo
    }

    pub fn get_status(&self) -> Result<Vec<FileStatus>, String> {
        if !self.is_repo {
            return Err("Not a git repository".to_string());
        }

        let output = Command::new("git")
            .args(["-C", self.path.to_str().unwrap_or("."), "status", "--porcelain"])
            .output()
            .map_err(|e| e.to_string())?;

        if !output.status.success() {
            return Err("Git command failed".to_string());
        }

        let status_text = String::from_utf8_lossy(&output.stdout);
        let mut result = Vec::new();

        for line in status_text.lines() {
            if line.len() < 3 {
                continue;
            }

            let index_status = line.chars().next().unwrap_or(' ');
            let worktree_status = line.chars().nth(1).unwrap_or(' ');
            let file_path = line[3..].to_string();

            let (status_type, staged) = match (index_status, worktree_status) {
                ('A', _) => (StatusType::Added, true),
                ('M', _) => (StatusType::Modified, true),
                ('D', _) => (StatusType::Deleted, true),
                ('R', _) => (StatusType::Renamed, true),
                ('?', _) => (StatusType::Untracked, false),
                ('!', _) => (StatusType::Ignored, false),
                (_, 'M') => (StatusType::Modified, false),
                (_, 'D') => (StatusType::Deleted, false),
                _ => (StatusType::Unmodified, false),
            };

            if status_type != StatusType::Unmodified {
                result.push(FileStatus { path: file_path, status: status_type, staged });
            }
        }

        Ok(result)
    }

    pub fn get_diff(&self, file_path: Option<&str>) -> Result<String, String> {
        if !self.is_repo {
            return Err("Not a git repository".to_string());
        }

        let mut args = vec!["-C", self.path.to_str().unwrap_or("."), "diff"];

        if let Some(path) = file_path {
            args.push("--");
            args.push(path);
        }

        let output = Command::new("git")
            .args(&args)
            .output()
            .map_err(|e| e.to_string())?;

        if !output.status.success() {
            return Err("Git diff failed".to_string());
        }

        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }

    pub fn get_branches(&self) -> Result<Vec<String>, String> {
        if !self.is_repo {
            return Err("Not a git repository".to_string());
        }

        let output = Command::new("git")
            .args(["-C", self.path.to_str().unwrap_or("."), "branch", "--format=%(refname:short)"])
            .output()
            .map_err(|e| e.to_string())?;

        if !output.status.success() {
            return Err("Git branch command failed".to_string());
        }

        let branches: Vec<String> = String::from_utf8_lossy(&output.stdout)
            .lines()
            .map(|s| s.to_string())
            .filter(|s| !s.is_empty())
            .collect();

        Ok(branches)
    }
}
