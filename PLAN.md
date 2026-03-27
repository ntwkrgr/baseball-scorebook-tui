# Baseball Scorebook TUI — Design Plan

## Overview

A terminal-based baseball scorebook application that supports live game scoring for both home and away teams. The app presents a traditional paper scorebook layout rendered entirely in the terminal, including per-at-bat diamond diagrams with live baserunner tracking, defensive alignments, inning totals (R/H/E/LOB), and full game save/load support.

**Design philosophy:** This is a **digital paper scorebook**, not a rules engine. The user is the scorekeeper — the app provides the layout, visualization, and persistence. It does not enforce baseball rules, validate lineup legality, or require a full roster. You write in what happened, just like a physical scorebook.

**Rules scope:** DH is always used (no pitcher batting). No pitch count or balls/strikes tracking.

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
│   ├── game.py          # Game, GameState, HalfInning
│   ├── team.py          # Team, Player, LineupSlot
│   ├── at_bat.py        # AtBat, BaseEvent
│   ├── events.py        # Event (event-sourced game log)
│   └── constants.py     # Enums: Position, PlayCode, BaseCode, Hand
├── engine/
│   ├── __init__.py
│   ├── event_store.py   # Append-only event log, undo support
│   └── state.py         # Derives GameState by replaying events
├── widgets/
│   ├── __init__.py
│   ├── scorecard.py     # ScorecardWidget — full team scorecard
│   ├── diamond.py       # DiamondWidget — per-at-bat diamond + lines
│   ├── lineup_row.py    # LineupRowWidget — one row per batter
│   ├── defense.py       # DefenseWidget — 9-position alignment grid
│   ├── inning_totals.py # InningTotalsWidget — R/H/E/LOB row
│   ├── scoreline.py     # ScorelineWidget — horizontal R per inning
│   └── game_log.py      # GameLogWidget — scrollable play-by-play
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

### 3.1 Design Approach: Event Sourcing

The game is stored as an **append-only sequence of immutable events**. The current game state (who's batting, what inning, runners on base) is **derived** by replaying the event log. This gives us:

- **Free undo/redo** — pop or re-append the last event
- **Play-by-play log** — the event list *is* the play-by-play
- **Safe serialization** — save the event list, derive state on load
- **Immutability** — no mutation; each event produces a new state snapshot

### 3.2 Event Types

```python
@dataclass(frozen=True)
class GameEvent:
    """Base event. All events are immutable and timestamped."""
    event_id: str        # UUID — used to target corrections via EditEvent
    timestamp: str       # ISO 8601

@dataclass(frozen=True)
class AtBatEvent(GameEvent):
    """A completed plate appearance."""
    inning: int
    half: HalfCode           # TOP / BOTTOM
    batting_order: int       # 1-9 (which lineup slot)
    result_type: ResultType  # structured enum (see §3.6) — drives stat counting
    fielders: str            # fielder notation (e.g. "6-3", "9", "") — display only
    batter_reached: bool     # True even on K+WP/PB (dropped 3rd strike)
    outs_on_play: int        # 0, 1, 2, or 3 (for DP/TP)
    bases_reached: list[BaseEvent]  # this batter's journey around the bases
    rbi_count: int
    notes: str

@dataclass(frozen=True)
class RunnerAdvanceEvent(GameEvent):
    """A runner from a previous at-bat advances (or is put out)
    as a direct consequence of a plate appearance."""
    inning: int
    half: HalfCode
    runner_batting_order: int  # which batter's diamond to update
    runner_at_bat_inning: int  # which inning's cell for that batter
    from_base: BaseCode
    to_base: BaseCode          # HOME for scored, OUT for put out
    how: AdvanceType           # enum: ON_HIT, ON_FC, ON_ERROR, ON_SAC, ON_WP, ON_PB, ON_THROW
    earned: bool
    rbi_batter_order: int | None  # who gets the RBI (if any)

@dataclass(frozen=True)
class BaserunnerEvent(GameEvent):
    """A baserunner event that occurs outside a plate appearance.
    Covers: stolen bases, caught stealing, pickoffs, wild pitches,
    passed balls, balks — anything that moves (or removes) a runner
    without a batter completing an at-bat."""
    inning: int
    half: HalfCode
    runner_batting_order: int  # which batter's diamond to update
    runner_at_bat_inning: int  # which inning's cell for that batter
    from_base: BaseCode
    to_base: BaseCode          # HOME for scored, OUT for put out
    how: BaserunnerType        # enum: SB, CS, PO (pickoff), WP, PB, BK, OBR
    fielders: str              # optional fielder notation (e.g. "2-6" for CS)
    earned: bool
    outs_on_play: int          # 0 or 1 (CS, pickoff)

@dataclass(frozen=True)
class SubstitutionEvent(GameEvent):
    """A player substitution."""
    inning: int
    half: HalfCode
    team: HalfCode             # which team (AWAY=TOP, HOME=BOTTOM)
    batting_order: int         # lineup slot being filled
    leaving_name: str
    entering_name: str
    entering_number: int
    new_position: Position
    sub_type: SubType          # enum: PINCH_HIT, PINCH_RUN, DEFENSIVE, PITCHER_CHANGE

@dataclass(frozen=True)
class ErrorEvent(GameEvent):
    """An error committed by a fielder on the defensive team."""
    inning: int
    half: HalfCode
    fielder_position: Position  # which defensive position committed the error
    fielder_name: str           # name of the fielder
    notes: str

@dataclass(frozen=True)
class EditEvent(GameEvent):
    """Corrects a previous event. Append-only — the original event is
    retained in the log but superseded by this correction.
    The engine replays the log using the corrected version wherever
    it encounters the target_event_id."""
    target_event_id: str       # UUID of the event being corrected
    corrected_event: GameEvent # the replacement event (same type, new data)
    reason: str                # optional note explaining the correction
```

### 3.3 Derived State (computed from events, never stored)

```python
@dataclass
class GameState:
    """Computed by replaying the event log. Never persisted directly."""
    current_inning: int
    current_half: HalfCode       # TOP / BOTTOM
    current_batter_index: int    # 0-8 in lineup order
    outs: int                    # 0-2 (3 triggers half-inning change)
    runners: dict[BaseCode, RunnerInfo]  # who's on which base
    away_score: int
    home_score: int

@dataclass
class RunnerInfo:
    """Identifies a runner currently on base."""
    batting_order: int     # which lineup slot
    at_bat_inning: int     # which inning's cell shows their diamond
```

### 3.4 Core Data Classes

```python
@dataclass(frozen=True)
class Player:
    name: str
    number: int
    position: Position  # defensive position

@dataclass(frozen=True)
class LineupSlot:
    batting_order: int  # 1-9
    player: Player
    position: Position  # may differ from player.position (DH, substitution)
    entered_inning: int # inning when this lineup slot became active

@dataclass(frozen=True)
class BaseEvent:
    """One leg of a batter's journey around the bases."""
    from_base: BaseCode  # HOME (batter's box), FIRST, SECOND, THIRD
    to_base: BaseCode    # FIRST, SECOND, THIRD, HOME, OUT
    how: AdvanceType     # enum: ON_HIT, ON_FC, ON_ERROR, ON_BB, ON_HBP, etc.
    earned: bool         # for scoring runs
    rbi: bool            # did this produce an RBI?

@dataclass(frozen=True)
class Team:
    name: str
    lineup: list[LineupSlot]  # 9 active batting-order slots (with DH)
```

### 3.5 Diamond Data (per at-bat cell)

Each batter's diamond in the scorecard represents **that runner's full journey**, regardless of which batter caused each advancement. This matches traditional scorebook convention.

```python
@dataclass
class DiamondState:
    """Visual state of one at-bat cell's diamond. Derived from events."""
    result_type: ResultType       # structured at-bat result
    fielders: str                 # fielder notation for display (e.g. "6-3")
    segments: dict[tuple[BaseCode, BaseCode], SegmentState]
    # e.g. (HOME, FIRST): LIT, (FIRST, SECOND): LIT, etc.
    final_base: BaseCode          # where the runner ended up
    final_state: RunnerFinalState # SCORED, LEFT_ON_BASE, OUT
    annotations: list[str]        # e.g. ["SB"] written along a segment
```

### 3.6 Structured Enums

All result and advance types are strict enums. The engine uses these for stat classification — no parsing of free-form text needed.

#### ResultType (at-bat outcome — drives stat counting)

| Value | Display | Counts as AB? | Counts as Hit? | Counts as Out? |
|-------|---------|:---:|:---:|:---:|
| `SINGLE` | 1B | Yes | Yes | No |
| `DOUBLE` | 2B | Yes | Yes | No |
| `TRIPLE` | 3B | Yes | Yes | No |
| `HOME_RUN` | HR | Yes | Yes | No |
| `WALK` | BB | No | No | No |
| `INTENTIONAL_WALK` | IBB | No | No | No |
| `HIT_BY_PITCH` | HBP | No | No | No |
| `STRIKEOUT` | K | Yes | No | Yes* |
| `STRIKEOUT_LOOKING` | Kl | Yes | No | Yes* |
| `GROUND_OUT` | GB | Yes | No | Yes |
| `FLY_OUT` | FB | Yes | No | Yes |
| `FOUL_OUT` | F | Yes | No | Yes |
| `LINE_OUT` | L | Yes | No | Yes |
| `DOUBLE_PLAY` | DP | Yes | No | Yes |
| `TRIPLE_PLAY` | TP | Yes | No | Yes |
| `SAC_FLY` | SF | No | No | Yes |
| `SAC_BUNT` | SAC | No | No | Yes |
| `FIELDERS_CHOICE` | FC | Yes | No | No |
| `REACHED_ON_ERROR` | E | Yes | No | No |
| `CATCHERS_INTERFERENCE` | CI | No | No | No |

*\* Strikeouts count as an out by default, but when `batter_reached=True` (dropped third strike), the batter is NOT out — the K still counts for the pitcher's stats and as an AB, but does not produce an out in the `outs_on_play` field.*

#### AdvanceType (how a runner moved between bases)

| Value | Display | Used in |
|-------|---------|---------|
| `ON_HIT` | (hit type) | BaseEvent, RunnerAdvanceEvent |
| `ON_BB` | BB | BaseEvent |
| `ON_HBP` | HBP | BaseEvent |
| `ON_FC` | FC | BaseEvent, RunnerAdvanceEvent |
| `ON_ERROR` | E | BaseEvent, RunnerAdvanceEvent |
| `ON_SAC` | SAC/SF | RunnerAdvanceEvent |
| `ON_WP` | WP | RunnerAdvanceEvent |
| `ON_PB` | PB | RunnerAdvanceEvent |
| `ON_THROW` | (fielder) | RunnerAdvanceEvent |
| `ON_CI` | CI | BaseEvent |

#### BaserunnerType (standalone baserunner events)

| Value | Display |
|-------|---------|
| `SB` | SB (stolen base) |
| `CS` | CS (caught stealing) |
| `PO` | PO (pickoff) |
| `WP` | WP (wild pitch) |
| `PB` | PB (passed ball) |
| `BK` | BK (balk) |
| `OBR` | OBR (out on base running) |

#### SubType (substitution type)

| Value | Display |
|-------|---------|
| `PINCH_HIT` | PH |
| `PINCH_RUN` | PR |
| `DEFENSIVE` | DEF |
| `PITCHER_CHANGE` | PITCH |

### 3.7 Defensive Position Numbers

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
│                             │
│  ┌───────────────────────┐  │
│  │ HalfInning Transition │  │◄── shown when 3rd out recorded
│  │ (summary + continue)  │  │
│  └───────────────────────┘  │
│                             │
│  ┌───────────────────────┐  │
│  │ End Game Prompt       │  │◄── triggered automatically or by G key
│  │ (confirm + save)      │  │
│  └───────────────────────┘  │
└──────┬──────────────────────┘
       │ game ended
       ▼
┌─────────────────────────────┐
│      GameOverScreen         │
│  Final score summary        │
│  [Save]  [Discard]  [Back]  │
└─────────────────────────────┘
```

### 4.1 Half-Inning Transition

When the 3rd out is recorded (via at-bat outs, caught stealing, pickoff, etc.), a **transition overlay** appears:

```
  ╔══════════════════════════════════════╗
  ║      End of Top 4th                  ║
  ╠══════════════════════════════════════╣
  ║  Cardinals: 0 R, 2 H, 0 E, 1 LOB   ║
  ║                                      ║
  ║  Score: Cardinals 3 — Cubs 1         ║
  ╠══════════════════════════════════════╣
  ║  Press [Enter] to continue           ║
  ║  to Bottom 4th                       ║
  ╚══════════════════════════════════════╝
```

- Shows runs/hits/errors/LOB for the half-inning just completed
- Shows current overall score
- Waits for **Enter** before switching to the other team's tab
- Auto-save triggers at this point

### 4.2 End Game Detection & Prompt

The app detects when a game should end and prompts the user:

| Condition | When detected |
|-----------|---------------|
| **Regulation end** | After bottom of 9th (or later) with home team leading |
| **Walk-off** | Home team takes the lead in bottom of 9th or later |
| **Visitor ahead after 9** | After top of 10th+ if away team leads after bottom of previous inning — *actually*: after bottom of 9th+ completes with away team leading |
| **Early end** | User presses **G** (End Game) at any time |

When triggered:

```
  ╔══════════════════════════════════════╗
  ║         End Game?                    ║
  ╠══════════════════════════════════════╣
  ║  Final: Cardinals 3 — Cubs 1        ║
  ║                                      ║
  ║  [Y] End game    [N] Continue        ║
  ╚══════════════════════════════════════╝
```

- **Y** transitions to GameOverScreen
- **N** allows play to continue (extra innings, or user changed their mind)
- For walk-offs, the prompt appears immediately after the winning run scores (not at end of inning)
- **G** key allows manual game end at any time (rain delay, mercy rule, etc.)

---

## 5. GameScreen Layout

The GameScreen is the heart of the application. It has two tabs — one per team — and uses a split layout:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  Baseball Scorebook   [AWAY: Cardinals] [HOME: Cubs]   Inning: 4th TOP  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  BATTING: Cardinals (Away)           FIELDING: Cubs (Home)               ║
║  ┌───────────────────────────────┐   ┌──────────────────────────────┐    ║
║  │  SCORECARD (away batters)     │   │  DEFENSIVE ALIGNMENT         │    ║
║  │  9 rows × 9+ inning cols     │   │  1  P  John Smith            │    ║
║  │  each cell = diamond widget   │   │  2  C  Mike Jones            │    ║
║  └───────────────────────────────┘   │  3  1B Bob Williams          │    ║
║                                      │  4  2B ...                   │    ║
║  ┌──────────────────────────────────┐│  5  3B ...                   │    ║
║  │  INNING TOTALS (R/H/E/LOB)      ││  6  SS ...                   │    ║
║  │  Inn: 1  2  3  4  5  6  7  8  9 ││  7  LF ...                   │    ║
║  │  R:   0  0  2  ...              ││  8  CF ...                   │    ║
║  │  H:   1  0  3  ...              ││  9  RF ...                   │    ║
║  │  E:   0  0  0  ...              │└──────────────────────────────┘    ║
║  │  LOB: 0  1  1  ...              │                                    ║
║  └──────────────────────────────────┘                                    ║
║                                                                          ║
║  SCORELINE: Away 0 | 0 | 2 | ...        Home 0 | 1 | 0 | ...           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ [N] New AB [R] Runner [E] Edit [S] Sub [G] End [L] Log [?] Help [Q] Quit║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Tab Behavior

- **Away tab** shows: Away team's scorecard + Home team's defensive alignment
- **Home tab** shows: Home team's scorecard + Away team's defensive alignment
- Tabs auto-switch when the half-inning changes

---

## 6. Diamond Widget (Per At-Bat Cell)

Each at-bat cell contains a miniature baseball diamond rendered with Unicode box-drawing and line characters. The diamond tracks **that runner's full journey** around the bases — including advances caused by later batters. This matches traditional scorebook convention.

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
  │  Result: 1B              │
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
- Advances to second on next batter's single → 1B→2B segment lit (via RunnerAdvanceEvent)
- Scores on a double → 2B→3B→Home segments lit, home diamond filled green

Each `BaseEvent` on the batter's diamond and each `RunnerAdvanceEvent` targeting that batter's cell contribute segments. The DiamondWidget reads this combined list and renders the appropriate path segments and annotations.

### 6.4 Play Code Annotations in the Diamond

The at-bat result is written below the diamond in standard scoring notation:

```
  K          (strikeout swinging — batter is out)
  K  →1B     (strikeout, dropped 3rd strike — batter reaches 1B)
  6-3        (ground out, shortstop to first)
  F8         (fly out to center field)
  E6         (error by shortstop)
  1B ↑SB     (single, then stolen base)
```

The dropped third strike case (`K →1B`) renders the K as the result but lights the Home→1B segment on the diamond. The stat engine records: AB=yes, K=yes, Out=no (because `batter_reached=True`).

Annotations along base path segments show *how* the runner advanced (e.g., "SB" along the 1B→2B segment, "WP" along 2B→3B).

---

## 7. Scorecard Grid Layout

### 7.1 Column Structure

```
┌────┬──────────────────┬────┬──────────────────────────────────┬───┬───┬───┐
│ #  │ Player           │ Pos│  1   │  2   │  3   │ … │  9   │ AB│ R │ H │
├────┼──────────────────┼────┼──────┼──────┼──────┼───┼──────┼───┼───┼───┤
│ 1  │ J. Smith         │ CF │ ◆-cell│ ◆-cell│      │   │      │ 2 │ 0 │ 1 │
│    │ ─── T. Davis     │ CF │      │ ◆-cell│      │   │      │ 1 │ 0 │ 0 │
│ 2  │ M. Jones         │ 2B │      │       │      │   │      │   │   │   │
│ …  │ …                │ …  │      │       │      │   │      │   │   │   │
│ 9  │ B. Williams      │ DH │      │       │      │   │      │   │   │   │
├────┴──────────────────┴────┴──────┴──────┴──────┴───┴──────┴───┴───┴───┤
│ R: 0  0  2  0  0  0  1  0  0 = 3   H: 7   E: 1   LOB: 5              │
└──────────────────────────────────────────────────────────────────────────┘
```

Substitutions appear as a horizontal divider (`───`) within the batting-order slot, with the new player's name and position below. Multiple substitutions for the same slot stack vertically.

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
  FIELDING: Cubs (Home)       Inning 4 TOP
  ┌─────────────────────────────────────┐
  │  1  P   Kyle Hendricks              │
  │  2  C   Willson Contreras           │
  │  3  1B  Anthony Rizzo               │
  │  4  2B  Javier Baez                 │
  │  5  3B  Kris Bryant                 │
  │  6  SS  Addison Russell             │
  │  7  LF  Kyle Schwarber              │
  │  8  CF  Albert Almora               │
  │  9  RF  Jason Heyward               │
  │     DH  Kyle Schwarber              │
  └─────────────────────────────────────┘
  [E] Edit alignment  [S] Substitution
```

- Defense updates when a substitution is recorded
- A visual indicator (bold / color) highlights the current pitcher
- Error attribution: when an error is recorded, the fielder's name is pulled from this alignment

---

## 9. At-Bat Entry Modal

When the user presses **Enter** on a scorecard cell or **N** for a new at-bat, a modal appears:

```
  ╔══════════════════════════════════════╗
  ║    At-Bat Entry — Batter: J. Smith   ║
  ╠══════════════════════════════════════╣
  ║  Result:     [Single ▼]             ║
  ║  Fielder(s): [____]  (e.g. 6-3)    ║
  ║  Outs:       [0 ▼]                  ║
  ║  ☐ Batter reached (dropped 3rd K)  ║
  ║                                      ║
  ║  Batter base path:                  ║
  ║  ┌─────────────────────────────┐    ║
  ║  │ → 1B  via ON_HIT            │    ║
  ║  │ [+ Add advance]            │    ║
  ║  └─────────────────────────────┘    ║
  ║                                      ║
  ║  Runner advances:                    ║
  ║  (pre-populated from base state)    ║
  ║  ┌─────────────────────────────┐    ║
  ║  │ #3 T.Davis: 2B → [3B ▼]    │    ║
  ║  │   How: [ON_HIT ▼]          │    ║
  ║  │ #5 R.Jones:  1B → [2B ▼]    │    ║
  ║  │   How: [ON_HIT ▼]          │    ║
  ║  └─────────────────────────────┘    ║
  ║                                      ║
  ║  RBI: [0]  Scored: [ ]  Notes: [  ] ║
  ║                                      ║
  ║  ┌────────────────┐                 ║
  ║  │  Diamond Prev. │ (live preview)  ║
  ║  └────────────────┘                 ║
  ╠══════════════════════════════════════╣
  ║    [OK]               [Cancel]       ║
  ╚══════════════════════════════════════╝
```

- **Result** is a `ResultType` dropdown — structured enum, not free-form
- **Fielders** is a text field for fielder notation (display only, e.g. "6-3")
- **Outs** dropdown: auto-filled based on result type (1 for most outs, 2 for DP, 3 for TP, 0 for hits/walks) — user can override
- **Batter reached** checkbox: shown only for strikeouts. When checked, the batter reaches base despite the K (dropped third strike). The K counts for pitcher stats and AB, but `outs_on_play` is set to 0
- **Batter base path** auto-populates based on result type (single → 1B, double → 2B, etc.) — user can add further advances
- **Runner advances** are **pre-populated** for all current baserunners. Default destination is the next forced base:
  - Each runner is pushed forward by one base per base occupied behind them
  - Example: bases loaded, batter singles → runner on 3B defaults to HOME, runner on 2B defaults to 3B, runner on 1B defaults to 2B
  - Example: runner on 1B only, batter doubles → runner on 1B defaults to 3B (not forced, but common)
  - User can override any destination (e.g., runner goes 1B→HOME on a double to the gap)
  - User can mark a runner as OUT instead of advancing
- Diamond preview updates in real-time as events are entered
- Tabbing through fields is fully supported

### 9.1 Auto-Population Logic

When the result type is selected, the modal pre-fills runner destinations using baseball conventions:

| Result | Batter goes to | Runner defaults |
|--------|---------------|-----------------|
| Single | 1B | Each runner advances 1 base |
| Double | 2B | Each runner advances 2 bases (scores from 2B/3B) |
| Triple | 3B | All runners score |
| Home Run | HOME | All runners score |
| Walk / HBP | 1B | Only forced runners advance (runner on 1B→2B, etc.) |
| Out (any) | OUT | Runners stay (user adjusts manually if needed) |
| Fielder's Choice | 1B | One runner marked OUT (user selects which) |

These are **defaults** — the user always has final say. The pre-population saves keystrokes for the ~80% of plays that follow standard patterns.

---

## 10. Substitution Workflow

Triggered by **S** in the main view. Flexible like a paper scorebook — no roster required, just write in the new player:

```
  ╔══════════════════════════════════════╗
  ║         Substitution                 ║
  ╠══════════════════════════════════════╣
  ║  Team:    [Away ▼]                   ║
  ║  Type:    [Pinch Hitter ▼]           ║
  ║           (Pinch Hitter / Pinch      ║
  ║            Runner / Defense Change   ║
  ║            / Pitcher Change)         ║
  ║                                      ║
  ║  Lineup slot: [#3 ▼]                ║
  ║  Leaving:     J. Smith (CF)          ║
  ║  Entering:    [_______________]      ║
  ║  Number:      [___]                  ║
  ║  New Pos:     [CF ▼]                 ║
  ║                                      ║
  ║  ☐ Also move another player's       ║
  ║    position (double switch)          ║
  ║  ┌─────────────────────────────┐    ║
  ║  │ Player: [#5 K.Bryant ▼]    │    ║
  ║  │ New Pos: [LF ▼]            │    ║
  ║  └─────────────────────────────┘    ║
  ╠══════════════════════════════════════╣
  ║    [OK]               [Cancel]       ║
  ╚══════════════════════════════════════╝
```

- Entering player name and number are free-text fields (no roster lookup required)
- Double-switch checkbox reveals additional position-swap fields
- A new `LineupSlot` is created with `entered_inning` set
- The scorecard displays a horizontal divider after the last at-bat of the replaced player
- The defensive alignment updates immediately

---

## 10.5. Baserunner Event Modal

Triggered by **R** in the main view. Used for any baserunner movement that occurs **outside** a completed plate appearance — stolen bases, caught stealing, pickoffs, wild pitch advances, passed ball advances, and balks.

```
  ╔══════════════════════════════════════╗
  ║       Baserunner Event               ║
  ╠══════════════════════════════════════╣
  ║  Runner: [#3 T.Davis on 1B ▼]       ║
  ║  To:     [2B ▼]                      ║
  ║  How:    [____]  (e.g. SB, CS 2-6)  ║
  ║  Out:    [ ]                         ║
  ║  Notes:  [____]                      ║
  ╠══════════════════════════════════════╣
  ║    [OK]               [Cancel]       ║
  ╚══════════════════════════════════════╝
```

- **Runner** dropdown lists current baserunners (derived from `GameState.runners`)
- **To** defaults to next base; can be changed (e.g., 1B→3B on a steal of third, or OUT for caught stealing)
- **How** is free-form text — standard codes: `SB`, `CS`, `PO` (pickoff), `WP`, `PB`, `BK`
- **Out** checkbox — if checked, the runner is removed from the bases and an out is recorded
- Creates a `BaserunnerEvent` which updates the runner's original diamond cell (lights up the appropriate segment with the annotation)
- Multiple runner events can be entered in sequence (e.g., double steal: enter one for each runner)

### How it appears on the diamond

A stolen base from 1B→2B lights up the 1B→2B segment on the runner's diamond with an "SB" annotation along the path. A caught stealing shows `✕` (red) at the destination base. This matches how a paper scorebook records these events — on the runner's own cell, not the batter's.

### Distinction from At-Bat runner advances

| Scenario | Entry point | Event type |
|----------|-------------|------------|
| Runner scores on a single | At-Bat Modal → "Runner advances" | `RunnerAdvanceEvent` |
| Runner steals 2nd between pitches | **R** key → Baserunner Event Modal | `BaserunnerEvent` |
| Runner advances on wild pitch | **R** key → Baserunner Event Modal | `BaserunnerEvent` |
| Runner caught stealing | **R** key → Baserunner Event Modal (Out checked) | `BaserunnerEvent` |

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

- Highlighted: current inning column, leading team row
- Extends dynamically beyond 9 columns for extra innings

---

## 12. Game Log / Play-by-Play

A scrollable `GameLogWidget` panel toggled with **L**, showing a text play-by-play generated from the event log:

```
  ┌─ PLAY-BY-PLAY ────────────────────────────────┐
  │ 4th TOP  J. Smith singles to center field (1B) │
  │ 4th TOP  M. Jones grounds into 4-6-3 DP;      │
  │          Smith out at 2nd                       │
  │ 4th TOP  B. Williams walks (BB)                │
  │ 4th TOP  ─── End of inning (3 outs) ───       │
  │ 4th BOT  A. Rizzo flies out to left (F7)       │
  └────────────────────────────────────────────────┘
```

- Auto-generated from the event store — no extra data entry needed
- Each `AtBatEvent` and `RunnerAdvanceEvent` produces a log line
- Substitutions are noted inline (e.g., "T. Davis pinch-hits for J. Smith")
- Panel can be docked left, right, or bottom via CSS layout

---

## 13. Save / Load System

### 13.1 File Format

Games are saved as pretty-printed JSON. The event log is the source of truth:

```json
{
  "version": "1.0",
  "date": "2026-03-27",
  "stadium": "Wrigley Field",
  "away": {
    "name": "Cardinals",
    "starting_lineup": [...]
  },
  "home": {
    "name": "Cubs",
    "starting_lineup": [...]
  },
  "events": [
    {"type": "at_bat", "inning": 1, "half": "TOP", ...},
    {"type": "runner_advance", ...},
    {"type": "baserunner", ...},
    {"type": "substitution", ...},
    ...
  ],
  "completed": false,
  "notes": ""
}
```

### 13.2 File Location

- Default save directory: `~/.baseball-scorebook/games/`
- Filename: `YYYY-MM-DD_Away-vs-Home.json`
- User can override path on save

### 13.3 Auto-Save

- Auto-save every 5 minutes to `~/.baseball-scorebook/autosave/YYYY-MM-DD_Away-vs-Home.json`
- Recovery prompt on next launch if auto-save is detected that is newer than the last manual save
- Auto-save also triggers on every half-inning change

### 13.4 Load Game Browser

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

## 14. Keyboard Shortcut Reference

| Key | Context | Action |
|-----|---------|--------|
| `↑ ↓ ← →` | Scorecard | Navigate cells |
| `Enter` | Scorecard cell | Open at-bat entry / edit |
| `N` | GameScreen | New at-bat (next in order) |
| `R` | GameScreen | Baserunner event (SB, CS, WP, etc.) |
| `E` | Scorecard cell | Edit existing at-bat |
| `S` | GameScreen | Substitution dialog |
| `G` | GameScreen | End game (prompts for confirmation) |
| `L` | GameScreen | Toggle play-by-play log panel |
| `D` | GameScreen | Toggle defensive alignment panel |
| `T` | GameScreen | Switch between Away / Home tabs |
| `Ctrl+S` | GameScreen | Save game |
| `Ctrl+Z` | GameScreen | Undo last event |
| `Ctrl+Y` | GameScreen | Redo last undone event |
| `F1` / `?` | Anywhere | Help overlay |
| `Q` / `Ctrl+C` | Anywhere | Quit (with unsaved-changes prompt) |
| `ESC` | Modal | Close / cancel |
| `Tab` | Modal | Next field |
| `Shift+Tab` | Modal | Previous field |

---

## 15. Implementation Phases

### Phase 1 — Foundation & Event Engine
- [ ] Project scaffolding (`pyproject.toml`, package structure)
- [ ] Constants / enums (`constants.py`: Position, BaseCode, HalfCode, ResultType, AdvanceType, BaserunnerType, SubType)
- [ ] Stat classification logic (ResultType → counts_as_ab, counts_as_hit, counts_as_out)
- [ ] Core data classes (`Player`, `LineupSlot`, `Team`, `BaseEvent`)
- [ ] Event types (`AtBatEvent`, `RunnerAdvanceEvent`, `BaserunnerEvent`, `SubstitutionEvent`, `ErrorEvent`, `EditEvent`)
- [ ] Event store (append, undo/redo, replay with EditEvent correction support)
- [ ] `GameState` derivation from event replay (including dropped 3rd strike: K + batter_reached)
- [ ] Runner advance auto-population logic (§9.1 defaults)
- [ ] End-game detection logic (regulation end, walk-off, manual)
- [ ] JSON serialization / deserialization (events + starting lineups)
- [ ] Unit tests for models, event store, state derivation, stat classification, and serialization

### Phase 2 — Core TUI Widgets
- [ ] `DiamondWidget` — static diamond rendering with all visualization states
- [ ] `DiamondWidget` — dynamic update from `DiamondState` (lit segments, annotations)
- [ ] `LineupRowWidget` — single batter row (with substitution dividers)
- [ ] `ScorecardWidget` — full scorecard grid (9 rows × dynamic columns)
- [ ] `DefenseWidget` — fielding alignment panel
- [ ] `InningTotalsWidget` — R/H/E/LOB row
- [ ] `ScorelineWidget` — pinned scoreboard (extends for extra innings)
- [ ] `GameLogWidget` — scrollable play-by-play generated from events

### Phase 3 — Screens & Interaction
- [ ] `HomeScreen` — new/load game
- [ ] `LineupEditorScreen` — pre-game lineup entry (9 slots per team, DH always)
- [ ] `GameScreen` — main layout (tabs, split panels)
- [ ] At-bat entry modal (with runner advances and live diamond preview)
- [ ] Substitution modal (with double-switch support)
- [ ] Baserunner event modal (SB, CS, WP, PB, BK, pickoff)
- [ ] Edit-cell modal (re-opens at-bat entry pre-filled; appends EditEvent on save)
- [ ] Half-inning transition overlay (summary + Enter to continue)
- [ ] End-game prompt (auto-detected + manual via G key)
- [ ] Keyboard navigation and focus management

### Phase 4 — Game Logic & Polish
- [ ] Automatic LOB calculation (derived from events)
- [ ] Run/hit/error counting per inning
- [ ] Earned run determination
- [ ] Error attribution to defensive fielders
- [ ] Extra innings — dynamic column extension, walk-off detection
- [ ] Auto-save (every 5 minutes + half-inning change)
- [ ] Help overlay
- [ ] End-to-end integration tests

---

## 16. Visual Design Principles

1. **Authenticity** — mirror a real paper scorebook as closely as possible within terminal constraints
2. **Density without clutter** — show everything at once but make each element clearly legible
3. **Minimal-keypress workflow** — entering an at-bat should require as few keystrokes as possible
4. **Immediate feedback** — diamond lines update the moment a base event is confirmed
5. **Resilience** — no data is ever lost; every change is undoable via event sourcing
6. **Flexibility** — the app is a tool, not a rules engine; the scorekeeper is always in control
