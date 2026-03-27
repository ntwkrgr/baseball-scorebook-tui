# baseball-scorebook-tui

A terminal-based baseball scorebook application for live game scoring.

## What Is This?

`baseball-scorebook-tui` is a TUI (terminal user interface) application that lets you keep a full baseball scorebook directly in your terminal — no paper required. It supports live scoring for both the home and away teams, shows a traditional per-at-bat scorecard with animated diamond diagrams tracking each baserunner's path, and stores completed games as JSON files for later review.

## Status

**Planning phase.** See [`PLAN.md`](PLAN.md) for the full design document.

## Planned Highlights

- ⚾ **Full scorecard** — 9 rows × 9+ inning columns, one diamond cell per at-bat
- 💎 **Diamond visualization** — lines drawn in real time to show where each baserunner advanced; filled green when they score, yellow when left on base
- 🛡️ **Defensive alignment** — fielding team's lineup shown alongside the batting team's scorecard
- 📊 **Inning totals** — R / H / E / LOB tracked per inning, updated automatically
- 🔁 **Full editability** — any cell can be corrected; substitutions update both the scorecard and defensive alignment
- 💾 **Save / load** — games persisted as human-readable JSON in `~/.baseball-scorebook/games/`
- ↩️ **Undo / redo** — every action is reversible
- 🎨 **Themes** — dark (classic scoreboard green-on-black), light, and high-contrast

## Technology Stack (Planned)

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| TUI Framework | [Textual](https://github.com/Textualize/textual) |
| Rendering | [Rich](https://github.com/Textualize/rich) |
| Storage | JSON (stdlib) |

## See Also

- [PLAN.md](PLAN.md) — detailed design plan including data model, screen layouts, widget hierarchy, keyboard shortcuts, and implementation phases

