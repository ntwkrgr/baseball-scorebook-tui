# Baseball Scorebook TUI — Design Plan

## Overview

A terminal-based baseball scorebook application that supports live game scoring for both home and away teams. The app presents a traditional paper scorebook layout rendered entirely in the terminal, including per-at-bat diamond diagrams with live baserunner tracking, defensive alignments, inning totals (R/H/E/LOB), and full game save/load support.

---

## 1. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Wide adoption, rich ecosystem, fast iteration |
| TUI Framework | [Textual](https://github.com/Textualize/textual) | Reactive widget model, mouse + keyboard, Rich rendering |
| Rendering | [Rich](https://github.com/Textualize/rich) | Tables, grids, styled text, box-drawing characters |
| Storage | JSON (via `json` stdlib) | Human-readable, easily version-controlled, no DB needed |
| Distribution | `pip install` / `pipx` | Simple installation for end users |

### Textual Highlights

- **Widgets** compose into a reactive tree (like React for TUIs)
- Full **mouse support** (click to focus / select cells)
- **CSS-like** layout system
- Built-in **modal dialogs** for input prompts
- **Dark/light theme** support
- Works on macOS, Linux, and Windows Terminal

---

## 2. Application Architecture

```
baseball_scorebook/
├── __init__.py
├── __main__.py          # Entry point: `python -m baseball_scorebook`
├── app.py               # Main Textual App class, screen routing
├── models/
│   ├── __init__.py
│   ├── game.py          # Game, Inning, HalfInning
│   ├── team.py          # Team, Player, LineupSlot
│   ├── at_bat.py        # AtBat, BaseEvent, Pitch
│   └── constants.py     # Enums: Position, PlayCode, BaseCode, Hand
├── widgets/
│   ├── __init__.py
│   ├── scorecard.py     # ScorecardWidget — full team scorecard
│   ├── diamond.py       # DiamondWidget — per-at-bat diamond + lines
│   ├── lineup_row.py    # LineupRowWidget — one row per batter
│   ├── defense.py       # DefenseWidget — 9-position alignment grid
│   ├── inning_totals.py # InningTotalsWidget — R/H/E/LOB row
│   └── scoreline.py     # ScorelineWidget — horizontal R per inning
├── screens/
│   ├── __init__.py
│   ├── home.py          # HomeScreen — start new game / load game
│   ├── game.py          # GameScreen — main scoring view
│   ├── lineup_editor.py # LineupEditorScreen — pre-game lineup entry
│   └── game_over.py     # GameOverScreen — final summary + save
└── storage/
    ├── __init__.py
    └── serializer.py    # save_game() / load_game() JSON serialization
```

---

## 3. Data Model

### 3.1 Core Classes

```python
@dataclass
class Player:
    name: str
    number: int
    bats: Hand          # L, R, S (switch)
    throws: Hand
    position: Position  # enumerated defensive position

@dataclass
class LineupSlot:
    batting_order: int  # 1–9
    player: Player
    position: Position  # may differ from player.position (DH, substitution)
    entered_inning: int # inning when this lineup slot became active

@dataclass
class BaseEvent:
    base: BaseCode       # FIRST, SECOND, THIRD, HOME, OUT
    how: PlayCode        # how baserunner reached / advanced (see §4)
    earned: bool         # for scoring runs
    rbi: bool            # did a hit/sac produce this run?

@dataclass
class Pitch:
    type: PitchType      # BALL, STRIKE, FOUL, HIT_BY_PITCH, etc.
    velocity: int | None # optional

@dataclass
class AtBat:
    batter: LineupSlot
    inning: int
    pitches: list[Pitch]
    result: PlayCode     # final at-bat result
    bases: list[BaseEvent]   # ordered list of bases reached/advanced to
    scored: bool
    rbi_count: int
    notes: str           # free-text annotation

@dataclass
class HalfInning:
    team: Team
    inning: int
    half: HalfCode       # TOP, BOTTOM
    at_bats: list[AtBat]

    @property
    def runs(self) -> int: ...
    @property
    def hits(self) -> int: ...
    @property
    def errors(self) -> int: ...
    @property
    def lob(self) -> int: ...

@dataclass
class Game:
    away: Team
    home: Team
    innings: list[HalfInning]
    stadium: str
    date: str
    umpires: list[str]
    notes: str
    completed: bool
```

### 3.2 Play Codes (PlayCode enum)

Standard baseball scoring abbreviations:

| Code | Meaning |
|------|---------|
| `1B` | Single |
| `2B` | Double |
| `3B` | Triple |
| `HR` | Home Run |
| `BB` | Walk |
| `IBB` | Intentional Walk |
| `HBP` | Hit By Pitch |
| `K` | Strikeout (swinging) |
| `Kl` | Strikeout (looking) |
| `F` | Foul out |
| `GB` | Ground ball out (with fielder numbers, e.g. `6-3`) |
| `FB` | Fly ball out (with fielder number, e.g. `9`) |
| `L` | Line drive out |
| `DP` | Double play |
| `TP` | Triple play |
| `SF` | Sacrifice fly |
| `SAC` | Sacrifice bunt |
| `E` | Error (with fielder number) |
| `FC` | Fielder's choice |
| `SB` | Stolen base |
| `CS` | Caught stealing |
| `PB` | Passed ball |
| `WP` | Wild pitch |
| `BK` | Balk |
| `OBR` | Out on base running |
| `CI` | Catcher's interference |

### 3.3 Defensive Position Numbers

```
1 - Pitcher
2 - Catcher
3 - First Base
4 - Second Base
5 - Third Base
6 - Shortstop
7 - Left Field
8 - Center Field
9 - Right Field
DH - Designated Hitter
```

---

## 4. Screen Flow

```
┌─────────────────────────────┐
│        HomeScreen           │
│  [New Game]  [Load Game]    │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│     LineupEditorScreen      │
│  Away lineup → Home lineup  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│        GameScreen           │◄──── main loop
│  [Away Tab] [Home Tab]      │
│  Scorecard + Defense view   │
└──────┬──────────────────────┘
       │ game over / ESC
       ▼
┌─────────────────────────────┐
│      GameOverScreen         │
│  Final score summary        │
│  [Save]  [Discard]  [Back]  │
└─────────────────────────────┘
```

---

## 5. GameScreen Layout

The GameScreen is the heart of the application. It has two tabs — one per team — and uses a split layout:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  ⚾ Baseball Scorebook   [AWAY: Cardinals] [HOME: Cubs]   Inning: 4th ▲  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  BATTING: Cardinals (Away)           FIELDING: Cubs (Home)               ║
║  ┌───────────────────────────────┐   ┌──────────────────────────────┐    ║
║  │  SCORECARD (away batters)     │   │  DEFENSIVE ALIGNMENT         │    ║
║  │  9 rows × 9+ inning cols      │   │  1  P  John Smith            │    ║
║  │  each cell = diamond widget   │   │  2  C  Mike Jones            │    ║
║  └───────────────────────────────┘   │  3  1B Bob Williams          │    ║
║                                       │  4  2B ...                   │    ║
║  ┌──────────────────────────────────┐ │  5  3B ...                   │    ║
║  │  INNING TOTALS (R/H/E/LOB)      │ │  6  SS ...                   │    ║
║  │  Inn: 1  2  3  4  5  6  7  8  9 │ │  7  LF ...                   │    ║
║  │  R:   0  0  2  ...              │ │  8  CF ...                   │    ║
║  │  H:   1  0  3  ...              │ │  9  RF ...                   │    ║
║  │  E:   0  0  0  ...              │ └──────────────────────────────┘    ║
║  │  LOB: 0  1  1  ...              │                                     ║
║  └──────────────────────────────────┘                                    ║
║                                                                           ║
║  SCORELINE: Away 0 | 0 | 2 | ...        Home 0 | 1 | 0 | ...            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  [N] New AB  [E] Edit Cell  [S] Sub  [P] Pitches  [?] Help  [Q] Quit    ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Tab Behavior

- **Away tab** shows: Away team's scorecard + Home team's defensive alignment
- **Home tab** shows: Home team's scorecard + Away team's defensive alignment
- Tabs auto-switch when the half-inning changes

---

## 6. Diamond Widget (Per At-Bat Cell)

Each at-bat cell contains a miniature baseball diamond rendered with Unicode box-drawing and line characters. The diamond tracks baserunner progress visually.

### 6.1 Diamond Rendering

```
  ┌──────────────────────────┐
  │  AB cell (batter #, pos) │
  │                          │
  │         2B               │
  │        /  \              │
  │      3B    1B            │
  │        \  /              │
  │         ◆  ← home        │
  │                          │
  │  Result: 1B (6-4)        │
  │  Pitch count: ●●○●       │
  └──────────────────────────┘
```

### 6.2 Base Visualization States

Each of the four path segments (Home→1B, 1B→2B, 2B→3B, 3B→Home) is rendered independently:

| State | Rendering | Meaning |
|-------|-----------|---------|
| Not reached | Thin line `─` / `│` (dim) | No runner progress |
| Reached / advanced through | Bold line `━` / `┃` (bright white) | Runner passed this base path |
| Scored | Filled diamond `◆` at home + bold all paths (green) | Run scored |
| Left on base | Filled circle `●` at the base where stranded (yellow) | LOB |
| Out on base | `✕` at the base where put out (red) | Out |

### 6.3 How Lines Are Drawn

The baserunner path is a directed sequence of base events. For example:

- Batter hits a single → Home→1B segment lit
- Advances to second on next batter's single → 1B→2B segment lit
- Scores on a double → 2B→3B→Home segments lit, home diamond filled green

Each `BaseEvent` in `AtBat.bases` carries `how` (PlayCode) and `base` (destination). The DiamondWidget reads this list and renders the appropriate path segments and annotations.

### 6.4 Play Code Annotations in the Diamond

The at-bat result is written below the diamond in standard scoring notation:

```
  K          (strikeout swinging)
  6-3        (ground out, shortstop to first)
  F8         (fly out to center field)
  E6         (error by shortstop)
  1B ↑SB     (single, then stolen base)
```

---

## 7. Scorecard Grid Layout

### 7.1 Column Structure

```
┌────┬──────────────────┬────┬──────────────────────────────────┬───┬───┬───┐
│ #  │ Player           │ Pos│  1   │  2   │  3   │ … │  9   │ AB│ R │ H │
├────┼──────────────────┼────┼──────┼──────┼──────┼───┼──────┼───┼───┼───┤
│ 1  │ J. Smith         │ CF │ ◆-cell│ ◆-cell│      │   │      │ 2 │ 0 │ 1 │
│ 2  │ M. Jones         │ 2B │      │       │      │   │      │   │   │   │
│ …  │ …                │ …  │      │       │      │   │      │   │   │   │
│ 9  │ B. Williams      │ P  │      │       │      │   │      │   │   │   │
├────┴──────────────────┴────┴──────┴──────┴──────┴───┴──────┴───┴───┴───┤
│ R: 0  0  2  0  0  0  1  0  0 = 3   H: 7   E: 1   LOB: 5              │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Cell Navigation

- **Arrow keys** navigate between cells
- **Enter / click** opens the At-Bat Entry modal for the focused cell
- **E** key opens the edit modal for an already-scored cell
- **S** key triggers the substitution workflow
- Cells for future innings are greyed out until that inning is active

### 7.3 Totals Row

At the bottom of the scorecard:
- Running R/H/E per inning
- LOB computed automatically: runners who reached base but did not score or get put out at a later base
- Cumulative totals (AB, R, H, RBI, BB, K) in rightmost columns

---

## 8. Defensive Alignment Widget

Displayed alongside the opposing team's scorecard (right panel):

```
  FIELDING: Cubs (Home)       Inning 4 ▲
  ┌─────────────────────────────────────┐
  │  1  P   Kyle Hendricks              │
  │  2  C   Willson Contreras           │
  │  3  1B  Anthony Rizzo               │
  │  4  2B  Javier Baez                 │
  │  5  3B  Kris Bryant                 │
  │  6  SS  Addison Russell             │
  │  7  LF  Kyle Schwarber              │
  │  8  CF  Albert Almora              │
  │  9  RF  Jason Heyward               │
  │     DH  —                           │
  └─────────────────────────────────────┘
  [E] Edit alignment  [S] Substitution
```

- Defense updates automatically when a substitution is recorded
- A visual indicator (bold / color) highlights the current pitcher

---

## 9. At-Bat Entry Modal

When the user presses **Enter** on a scorecard cell or **N** for a new at-bat, a modal appears:

```
  ╔══════════════════════════════════════╗
  ║    At-Bat Entry — Batter: J. Smith   ║
  ╠══════════════════════════════════════╣
  ║  Result code: [____]  (e.g. 1B, K)  ║
  ║  Fielder(s):  [____]  (e.g. 6-3)    ║
  ║  Pitch count: B[_] S[_] F[_]        ║
  ║                                      ║
  ║  Base events (add as many as needed):║
  ║  ┌─────────────────────────────┐    ║
  ║  │ Reached: [1B▼]  How: [1B▼] │    ║
  ║  │ Advanced: [2B▼] How: [SB▼] │    ║
  ║  │ [+ Add event]               │    ║
  ║  └─────────────────────────────┘    ║
  ║  Scored: [✓]  RBI: [1]  Notes: [  ] ║
  ╠══════════════════════════════════════╣
  ║    [OK]               [Cancel]       ║
  ╚══════════════════════════════════════╝
```

- All inputs validated against legal play codes
- Diamond preview updates in real-time as events are entered
- Tabbing through fields is fully supported

---

## 10. Substitution Workflow

Triggered by **S** in the main view:

```
  ╔══════════════════════════════════════╗
  ║         Substitution                 ║
  ╠══════════════════════════════════════╣
  ║  Team:    [Away ▼]                   ║
  ║  Type:    [Pinch Hitter ▼]           ║
  ║           (Pinch Hitter / Pinch      ║
  ║            Runner / Defense Change   ║
  ║            / Pitcher Change)         ║
  ║  Leaving: [J. Smith (CF) ▼]         ║
  ║  Entering: [New Player Name _____]   ║
  ║  Number:   [___]                     ║
  ║  New Pos:  [CF ▼]                    ║
  ╠══════════════════════════════════════╣
  ║    [OK]               [Cancel]       ║
  ╚══════════════════════════════════════╝
```

- A new `LineupSlot` is created with `entered_inning` set
- The scorecard displays a horizontal divider after the last at-bat of the replaced player
- The defensive alignment updates immediately

---

## 11. Inning & Scoreline Summary

### 11.1 Inning Totals Block

Below the scorecard grid, per inning:

```
          Inn  1  2  3  4  5  6  7  8  9   TOTAL
          R:   0  0  2  0  1  0  0  0  0 =   3
          H:   1  0  3  1  2  0  0  1  0 =   8
          E:   0  0  0  1  0  0  0  0  0 =   1
          LOB: 1  0  2  1  2  0  0  1  0 =   7
```

### 11.2 Top-Level Scoreline

Pinned at the bottom of the screen (like a real scoreboard):

```
  ┌──────────┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
  │ Team     │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ 8 │ 9 │ R │ H │ E │
  ├──────────┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
  │ Cardinals│ 0 │ 0 │ 2 │ 0 │ 1 │ 0 │ 0 │ 0 │ 0 │ 3 │ 8 │ 1 │
  │ Cubs     │ 0 │ 1 │ 0 │ 0 │ 0 │ 0 │ 0 │ 0 │   │ 1 │ 4 │ 0 │
  └──────────┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

Highlighted: current inning column, leading team row

---

## 12. Save / Load System

### 12.1 File Format

Games are saved as pretty-printed JSON files:

```json
{
  "version": "1.0",
  "date": "2026-03-27",
  "stadium": "Wrigley Field",
  "away": {
    "name": "Cardinals",
    "lineup": [...],
    "half_innings": [...]
  },
  "home": {
    "name": "Cubs",
    "lineup": [...],
    "half_innings": [...]
  },
  "completed": true,
  "notes": ""
}
```

### 12.2 File Location

- Default save directory: `~/.baseball-scorebook/games/`
- Filename: `YYYY-MM-DD_Away-vs-Home.json`
- User can override path on save

### 12.3 Load Game Browser

A file-picker widget on the HomeScreen that lists saved games:

```
  ╔══════════════════════════════════════╗
  ║         Load a Saved Game            ║
  ╠══════════════════════════════════════╣
  ║  2026-03-27  Cardinals vs Cubs   ✅  ║
  ║  2026-03-20  Dodgers vs Giants       ║
  ║  2026-03-15  Yankees vs Red Sox  ✅  ║
  ╠══════════════════════════════════════╣
  ║  [Open]  [Delete]  [Cancel]          ║
  ╚══════════════════════════════════════╝
```

- ✅ = completed game
- Completed games open in read-only mode (with an [Edit] toggle)

---

## 13. Keyboard Shortcut Reference

| Key | Context | Action |
|-----|---------|--------|
| `↑ ↓ ← →` | Scorecard | Navigate cells |
| `Enter` | Scorecard cell | Open at-bat entry / edit |
| `N` | GameScreen | New at-bat (next in order) |
| `E` | Scorecard cell | Edit existing at-bat |
| `S` | GameScreen | Substitution dialog |
| `P` | GameScreen | Pitch log for current AB |
| `D` | GameScreen | Toggle defensive alignment panel |
| `T` | GameScreen | Switch between Away / Home tabs |
| `Ctrl+S` | GameScreen | Save game |
| `Ctrl+Z` | GameScreen | Undo last entry |
| `F1` / `?` | Anywhere | Help overlay |
| `Q` / `Ctrl+C` | Anywhere | Quit (with unsaved-changes prompt) |
| `ESC` | Modal | Close / cancel |
| `Tab` | Modal | Next field |
| `Shift+Tab` | Modal | Previous field |

---

## 14. Additional Feature Suggestions

### 14.1 Pitch Tracking
- Optional per-pitch logging (type, velocity, result)
- Pitch count display in diamond cell corner
- Running balls/strikes count shown during active at-bat
- Pitcher-level pitch count totals per inning

### 14.2 Game Log / Play-by-Play
- A scrollable `GameLog` panel (toggled with `L`) showing a text play-by-play:
  ```
  4th ▲  J. Smith singles to center field (1B)
  4th ▲  M. Jones grounds into 4-6-3 double play; Smith out at 2nd
  4th ▲  B. Williams walks
  ```

### 14.3 Running Batting Stats Sidebar
- Expandable right panel showing cumulative individual stats for the active batter's team:
  ```
  Player       AB  R  H  RBI  BB  K  AVG
  J. Smith      3  0  1   0   1   1  .333
  M. Jones      3  0  0   0   0   2  .000
  ```

### 14.4 Extra Innings
- Automatic extension beyond 9 innings
- Column headers extend dynamically
- Tie game / walk-off detection and annotation

### 14.5 Export Options
- **Text export**: ASCII art scorecard to `.txt` file (shareable)
- **HTML export**: Styled HTML version of the scorecard
- **CSV export**: Raw data for downstream analysis

### 14.6 Undo / Redo
- Full undo stack (`Ctrl+Z` / `Ctrl+Y`)
- Undo pops the last atomic action (at-bat entry, substitution, etc.)

### 14.7 Game Templates
- Pre-loaded team rosters from a `teams/` directory (YAML files)
- Quick-start: select team names and lineups are pre-filled

### 14.8 Auto-Save
- Periodic auto-save every 5 minutes to `~/.baseball-scorebook/autosave.json`
- Recovery prompt on next launch if auto-save is detected

### 14.9 Color Themes
- Default dark theme (green on black — classic scoreboard aesthetic)
- Light theme for daytime use
- High-contrast accessibility theme

### 14.10 Scoreboard Display Mode
- `F11` toggles a minimal scoreboard-only view (just the scoreline widget, full width)
- Useful for projecting to a screen or stream overlay

---

## 15. Implementation Phases

### Phase 1 — Foundation
- [ ] Project scaffolding (`pyproject.toml`, package structure)
- [ ] Data models (`game.py`, `team.py`, `at_bat.py`, `constants.py`)
- [ ] JSON serialization / deserialization
- [ ] Unit tests for models and serialization

### Phase 2 — Core TUI Widgets
- [ ] `DiamondWidget` — static diamond rendering
- [ ] `DiamondWidget` — dynamic baserunner line drawing
- [ ] `LineupRowWidget` — single batter row
- [ ] `ScorecardWidget` — full scorecard grid
- [ ] `DefenseWidget` — fielding alignment panel
- [ ] `InningTotalsWidget` — R/H/E/LOB row
- [ ] `ScorelineWidget` — pinned scoreboard

### Phase 3 — Screens & Interaction
- [ ] `HomeScreen` — new/load game
- [ ] `LineupEditorScreen` — pre-game lineup entry
- [ ] `GameScreen` — main layout (tabs, split panels)
- [ ] At-bat entry modal
- [ ] Substitution modal
- [ ] Edit-cell modal
- [ ] Keyboard navigation and focus management

### Phase 4 — Game Logic
- [ ] Automatic LOB calculation
- [ ] Run/hit/error counting
- [ ] Earned run determination
- [ ] Walk-off / extra innings detection
- [ ] Undo / redo stack

### Phase 5 — Quality & Polish
- [ ] Pitch tracking
- [ ] Game log / play-by-play
- [ ] Export (text, HTML, CSV)
- [ ] Auto-save
- [ ] Team roster templates
- [ ] Color themes
- [ ] Help overlay
- [ ] End-to-end integration tests
- [ ] README with screenshots

---

## 16. Visual Design Principles

1. **Authenticity** — mirror a real paper scorebook as closely as possible within terminal constraints
2. **Density without clutter** — show everything at once but make each element clearly legible
3. **Minimal-keypress workflow** — entering an at-bat should require as few keystrokes as possible
4. **Immediate feedback** — diamond lines update the moment a base event is confirmed
5. **Resilience** — no data is ever lost; every change is undoable
