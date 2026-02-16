use ratatui::{prelude::*, widgets::*};
use crossterm::{event::{self, Event, KeyCode, KeyEventKind}, terminal::{disable_raw_mode, enable_raw_mode}};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut terminal = Terminal::new(CrosstermBackend::new(std::io::stdout()))?;

    loop {
        terminal.draw(|f| {
            let paragraph = Paragraph::new("MD TUI - Rust Version").block(Block::default().borders(Borders::ALL));
            f.render_widget(paragraph, f.size());
        })?;

        if let Event::Key(key) = event::read()? {
            if key.kind == KeyEventKind::Press && key.code == KeyCode::Char('q') {
                break;
            }
        }
    }

    disable_raw_mode()?;
    Ok(())
}
