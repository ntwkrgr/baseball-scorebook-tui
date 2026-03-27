# baseball-scorebook-tui

A terminal-based baseball scorebook application for live game scoring.

## What Is This?

`baseball-scorebook-tui` is a TUI (terminal user interface) application that lets you keep a full baseball scorebook directly in your terminal. It supports live scoring for both the home and away teams, shows a traditional per-at-bat scorecard with diamond diagrams tracking each baserunner's path, and stores completed games as JSON files for later review.

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/ntwkrgr/baseball-scorebook-tui.git
cd baseball-scorebook-tui
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
python -m baseball_scorebook
```

Or if installed via pip:

```bash
baseball-scorebook
```

## Features

- **Full scorecard** — 9 lineup rows with diamond cells for each at-bat
- **Diamond visualization** — base path segments light up as runners advance; green for scored, yellow for left on base, red for out
- **Defensive alignment** — fielding team's lineup shown alongside the batting scorecard
- **Inning totals** — R/H/E/LOB tracked per inning, updated automatically
- **Scoreline** — pinned scoreboard at the bottom showing runs per inning for both teams
- **Play-by-play log** — auto-generated from the event log, toggled with `L`
- **Event sourcing** — all game state derived from an append-only event log
- **Undo/redo** — every action is reversible with Ctrl+Z / Ctrl+Y
- **Save/load** — games persisted as JSON in `~/.baseball-scorebook/games/`
- **Auto-populated runner advances** — smart defaults based on play type (single, double, walk, etc.)
- **Substitutions** — pinch hit, pinch run, defensive changes, and pitcher changes
- **Baserunner events** — stolen bases, caught stealing, wild pitches, passed balls, balks
- **Half-inning transitions** — summary overlay showing R/H/E/LOB with auto tab-switching
- **Game-over detection** — regulation end, walk-off, extra innings, and manual end

## Keyboard Shortcuts

| Key | Context | Action |
|-----|---------|--------|
| `N` | Game | New at-bat |
| `R` | Game | Baserunner event (SB, CS, WP, etc.) |
| `S` | Game | Substitution |
| `G` | Game | End game |
| `L` | Game | Toggle play-by-play log |
| `T` | Game | Switch Away/Home tab |
| `Ctrl+S` | Game | Save game |
| `Ctrl+Z` | Game | Undo |
| `Ctrl+Y` | Game | Redo |
| `Q` | Anywhere | Quit |

## Architecture

The app uses an **event sourcing** architecture. The game is stored as an append-only sequence of immutable events. Current game state (inning, outs, runners, scores) is derived by replaying the event log — nothing is mutated in place.

```
baseball_scorebook/
├── models/        # Frozen dataclasses, enums, event types
├── engine/        # Event store (undo/redo) + state derivation
├── widgets/       # Diamond, scorecard, defense, scoreline, totals, game log
├── screens/       # Home, lineup editor, game, modals, game over
└── storage/       # JSON serialization/deserialization
```

## Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| TUI Framework | [Textual](https://github.com/Textualize/textual) |
| Rendering | [Rich](https://github.com/Textualize/rich) |
| Storage | JSON (stdlib) |

## Development

```bash
pip install -e ".[dev]"
pytest
```

268 tests covering the engine, models, serialization, and app smoke tests.

## See Also

- [PLAN.md](PLAN.md) — detailed design plan including data model, screen layouts, widget hierarchy, keyboard shortcuts, and implementation phases
