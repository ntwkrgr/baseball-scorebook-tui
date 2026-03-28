# baseball-scorebook-tui

A browser-based baseball scorebook application for live game scoring.

## What Is This?

`baseball-scorebook-tui` is now a local web app that keeps the original scorekeeping engine and JSON save format while moving the interface into the browser. It supports live scoring for both the home and away teams, shows a traditional per-at-bat scorecard with diamond diagrams tracking each baserunner's path, and stores completed games as JSON files for later review.

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

This starts a local FastAPI server, opens the browser automatically, and serves the built React UI.

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
- **Mouse + keyboard parity** — every primary action works with shortcuts and clickable controls
- **Auto-generate lineup** — fills away/home lineup screens with deterministic test data for fast manual testing

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
| `Q` | Game | Return home |

## Architecture

The app uses an **event sourcing** architecture. The game is stored as an append-only sequence of immutable events. Current game state (inning, outs, runners, scores) is derived by replaying the event log — nothing is mutated in place.

```
baseball_scorebook/
├── models/        # Frozen dataclasses, enums, event types
├── engine/        # Event store (undo/redo) + state derivation
├── services/      # Shared command helpers + browser snapshot builders
└── storage/       # JSON serialization/deserialization
frontend/          # React app, unit tests, Playwright coverage
```

## Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) |
| Frontend | [React](https://react.dev/) + [Vite](https://vite.dev/) |
| Storage | JSON (stdlib) |

## Development

```bash
pip install -e ".[dev]"
pytest
```

Frontend development:

```bash
cd frontend
npm install
npm run dev
```

Current verification:

- `uv run pytest -q`
- `cd frontend && npm run test:run`
- `cd frontend && npm run e2e`

## See Also

- [PLAN.md](PLAN.md) — detailed design plan including data model, screen layouts, widget hierarchy, keyboard shortcuts, and implementation phases
