import { startTransition, useEffect, useEffectEvent, useState } from 'react'
import { BrowserRouter, Link, Route, Routes, useNavigate, useParams } from 'react-router-dom'

import { Modal } from './components/Modal'
import { Scorecard } from './components/Scorecard'
import { useGameHotkeys } from './hooks/useGameHotkeys'
import { api } from './lib/api'
import { createAtBatForm, mergeAtBatDraft } from './lib/atBatForm'
import { generatedLineup } from './lib/lineupTemplates'

const POSITION_OPTIONS = [
  ['1', 'P'],
  ['2', 'C'],
  ['3', '1B'],
  ['4', '2B'],
  ['5', '3B'],
  ['6', 'SS'],
  ['7', 'LF'],
  ['8', 'CF'],
  ['9', 'RF'],
  ['10', 'DH'],
]

const RESULT_OPTIONS = [
  'SINGLE',
  'DOUBLE',
  'TRIPLE',
  'HOME_RUN',
  'WALK',
  'INTENTIONAL_WALK',
  'HIT_BY_PITCH',
  'STRIKEOUT',
  'STRIKEOUT_LOOKING',
  'GROUND_OUT',
  'FLY_OUT',
  'FOUL_OUT',
  'LINE_OUT',
  'DOUBLE_PLAY',
  'TRIPLE_PLAY',
  'SAC_FLY',
  'SAC_BUNT',
  'FIELDERS_CHOICE',
  'REACHED_ON_ERROR',
  'CATCHERS_INTERFERENCE',
]

const BASERUNNER_OPTIONS = ['SB', 'CS', 'PO', 'WP', 'PB', 'BK', 'OBR']

const SUB_OPTIONS = ['PINCH_HIT', 'PINCH_RUN', 'DEFENSIVE', 'PITCHER_CHANGE']

function emptyLineup() {
  return {
    name: '',
    lineup: Array.from({ length: 9 }, (_, index) => ({
      battingOrder: index + 1,
      playerName: '',
      playerNumber: '',
      position: '',
    })),
  }
}

function labelForPosition(position) {
  return POSITION_OPTIONS.find(([value]) => value === position)?.[1] ?? position
}

function lookupPlayer(teams, half, battingOrder) {
  const side = half === 'TOP' ? 'away' : 'home'
  return teams[side].lineup.find((slot) => slot.battingOrder === battingOrder)
}

function Scoreline({ scoreline }) {
  return (
    <section className="scoreline">
      <table>
        <thead>
          <tr>
            <th>Team</th>
            {scoreline.innings.map((inning) => (
              <th key={inning}>{inning}</th>
            ))}
            <th>R</th>
            <th>H</th>
            <th>E</th>
          </tr>
        </thead>
        <tbody>
          {[
            ['away', scoreline.awayName, scoreline.awayRunsByInning, scoreline.totals.away],
            ['home', scoreline.homeName, scoreline.homeRunsByInning, scoreline.totals.home],
          ].map(([key, name, runs, totals]) => (
            <tr key={key}>
              <th>{name}</th>
              {runs.map((value, index) => {
                const inning = scoreline.innings[index]
                const active =
                  scoreline.active.inning === inning &&
                  ((scoreline.active.half === 'TOP' && key === 'away') ||
                    (scoreline.active.half === 'BOTTOM' && key === 'home'))
                return (
                  <td key={`${key}-${inning}`} className={active ? 'scoreline-active' : ''}>
                    {value ?? '—'}
                  </td>
                )
              })}
              <td>{totals.R}</td>
              <td>{totals.H}</td>
              <td>{totals.E}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function InningTotals({ title, totals }) {
  return (
    <section className="totals-card">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th>Stat</th>
            {totals.innings.map((inning) => (
              <th key={inning}>{inning}</th>
            ))}
            <th>TOT</th>
          </tr>
        </thead>
        <tbody>
          {['R', 'H', 'E', 'LOB'].map((stat) => (
            <tr key={stat}>
              <th>{stat}</th>
              {(totals.rows[stat] ?? []).map((value, index) => (
                <td key={`${stat}-${totals.innings[index]}`}>{value}</td>
              ))}
              <td>{totals.totals[stat]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function DefensePanel({ defense, title }) {
  return (
    <section className="defense-card">
      <h3>{title}</h3>
      <ul>
        {defense.map((row) => (
          <li key={row.number}>
            <span>{row.position}</span>
            <strong>{row.playerNumber ? `#${row.playerNumber}` : '—'}</strong>
            <em>{row.playerName}</em>
          </li>
        ))}
      </ul>
    </section>
  )
}

function ToolbarButton({ children, shortcut, ...props }) {
  return (
    <button type="button" className="toolbar-button" {...props}>
      <span>{children}</span>
      <small>{shortcut}</small>
    </button>
  )
}

const HERO_ASCII = `
 ╔══════════════════════════════════════════════════════════════════════╗
 ║  ⚾  B A S E B A L L   S C O R E B O O K                            ║
 ║                                                                      ║
 ║       2B              ─────────────────────────────────────────     ║
 ║      ╱  ╲             │ #  │ Batter      │ Pos │  1  │  2  │  3  │ ║
 ║    3B    1B           ├────┼─────────────┼─────┼─────┼─────┼─────┤ ║
 ║      ╲  ╱             │ 1  │ Player Name │  CF │     │     │     │ ║
 ║       ◇               │ 2  │ Player Name │  2B │     │     │     │ ║
 ║                       └────┴─────────────┴─────┴─────┴─────┴─────┘ ║
 ╚══════════════════════════════════════════════════════════════════════╝`

function HomePage() {
  return (
    <main className="shell home-shell">
      <section className="hero-card">
        <pre className="hero-ascii" aria-hidden="true">{HERO_ASCII}</pre>
        <p className="eyebrow">⚾  Live scoring in the browser</p>
        <h1>Baseball Scorebook</h1>
        <p className="hero-copy">
          A digital paper scorebook. Event-sourced scoring, undo/redo, JSON save files,
          keyboard-first control, and full click support.
        </p>
        <div className="hero-actions">
          <Link className="primary-link" to="/new">
            [ New Game ]
          </Link>
          <Link className="secondary-link" to="/load">
            [ Load Saved Game ]
          </Link>
        </div>
        <p className="hero-shortcuts">
          Hotkeys during game: <kbd>N</kbd> new at-bat · <kbd>R</kbd> runner event ·
          <kbd>S</kbd> substitution · <kbd>Ctrl+Z</kbd> undo · <kbd>Ctrl+Y</kbd> redo ·
          <kbd>L</kbd> toggle log · <kbd>T</kbd> switch tab · <kbd>G</kbd> end game
        </p>
      </section>
    </main>
  )
}

function TeamForm({ title, team, onChange, onGenerate, onSubmit, onBack, busy }) {
  return (
    <main className="shell">
      <section className="form-card">
        <div className="form-header">
          <div>
            <p className="eyebrow">Lineup Entry</p>
            <h1>{title}</h1>
          </div>
          <button type="button" className="secondary-button" onClick={onGenerate}>
            Auto-Generate Lineup
          </button>
        </div>

        <label className="stacked-field">
          <span>Team Name</span>
          <input
            value={team.name}
            onChange={(event) => onChange({ ...team, name: event.target.value })}
            placeholder="Team name"
          />
        </label>

        <div className="lineup-table">
          <div className="lineup-table-head">#</div>
          <div className="lineup-table-head">Player</div>
          <div className="lineup-table-head">No.</div>
          <div className="lineup-table-head">Pos</div>
          {team.lineup.map((slot, index) => (
            <LineupRow
              key={slot.battingOrder}
              slot={slot}
              onChange={(nextSlot) => {
                const next = [...team.lineup]
                next[index] = nextSlot
                onChange({ ...team, lineup: next })
              }}
            />
          ))}
        </div>

        <div className="footer-actions">
          <button type="button" className="ghost-button" onClick={onBack}>
            Back
          </button>
          <button type="button" className="primary-button" onClick={onSubmit} disabled={busy}>
            {busy ? 'Working…' : 'Continue'}
          </button>
        </div>
      </section>
    </main>
  )
}

function LineupRow({ slot, onChange }) {
  return (
    <>
      <div className="lineup-table-cell">{slot.battingOrder}</div>
      <input
        className="lineup-table-cell"
        value={slot.playerName}
        onChange={(event) => onChange({ ...slot, playerName: event.target.value })}
        placeholder={`Player ${slot.battingOrder}`}
      />
      <input
        className="lineup-table-cell"
        value={slot.playerNumber}
        onChange={(event) => onChange({ ...slot, playerNumber: event.target.value })}
        inputMode="numeric"
        placeholder="#"
      />
      <select
        className="lineup-table-cell"
        value={slot.position}
        onChange={(event) => onChange({ ...slot, position: event.target.value })}
      >
        <option value="">Pos</option>
        {POSITION_OPTIONS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </>
  )
}

function NewGamePage() {
  const navigate = useNavigate()
  const [step, setStep] = useState('away')
  const [awayTeam, setAwayTeam] = useState(emptyLineup())
  const [homeTeam, setHomeTeam] = useState(emptyLineup())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function validate(team) {
    if (!team.name.trim()) {
      return 'Team name is required.'
    }
    if (team.lineup.some((slot) => !slot.playerName.trim() || !slot.position)) {
      return 'Fill every player name and position before continuing.'
    }
    return ''
  }

  async function submitCurrent() {
    const currentTeam = step === 'away' ? awayTeam : homeTeam
    const validationError = validate(currentTeam)
    if (validationError) {
      setError(validationError)
      return
    }
    setError('')

    if (step === 'away') {
      setStep('home')
      return
    }

    setBusy(true)
    try {
      const snapshot = await api.createGame({
        awayTeam: {
          ...awayTeam,
          lineup: awayTeam.lineup.map((slot) => ({
            ...slot,
            playerNumber: Number(slot.playerNumber || 0),
          })),
        },
        homeTeam: {
          ...homeTeam,
          lineup: homeTeam.lineup.map((slot) => ({
            ...slot,
            playerNumber: Number(slot.playerNumber || 0),
          })),
        },
      })
      startTransition(() => navigate(`/games/${snapshot.sessionId}`))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <TeamForm
        title={step === 'away' ? 'Enter Away Team' : 'Enter Home Team'}
        team={step === 'away' ? awayTeam : homeTeam}
        onChange={step === 'away' ? setAwayTeam : setHomeTeam}
        onGenerate={() => {
          const generated = generatedLineup(step)
          if (step === 'away') {
            setAwayTeam(generated)
          } else {
            setHomeTeam(generated)
          }
        }}
        onSubmit={submitCurrent}
        onBack={() => {
          if (step === 'away') {
            navigate('/')
            return
          }
          setStep('away')
        }}
        busy={busy}
      />
      {error ? <div className="toast toast-error">{error}</div> : null}
    </>
  )
}

function LoadGamePage() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .listSavedGames()
      .then((payload) => {
        if (cancelled) {
          return
        }
        setItems(payload.items)
        setSelected(payload.items[0]?.filename ?? '')
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError.message)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function openSelected() {
    if (!selected) {
      return
    }
    try {
      const snapshot = await api.loadGame(selected)
      startTransition(() => navigate(`/games/${snapshot.sessionId}`))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <main className="shell">
      <section className="form-card">
        <div className="form-header">
          <div>
            <p className="eyebrow">Saved Games</p>
            <h1>Load Game</h1>
          </div>
        </div>
        {loading ? <p>Loading saved games…</p> : null}
        {!loading && items.length === 0 ? <p>No saved games found yet.</p> : null}
        <div className="saved-list">
          {items.map((item) => (
            <button
              type="button"
              key={item.filename}
              className={`saved-item ${selected === item.filename ? 'saved-item-selected' : ''}`}
              onClick={() => setSelected(item.filename)}
            >
              <strong>{item.stem}</strong>
              <span>{item.filename}</span>
            </button>
          ))}
        </div>
        <div className="footer-actions">
          <button type="button" className="ghost-button" onClick={() => navigate('/')}>
            Back
          </button>
          <button type="button" className="primary-button" onClick={openSelected} disabled={!selected}>
            Open
          </button>
        </div>
      </section>
      {error ? <div className="toast toast-error">{error}</div> : null}
    </main>
  )
}

function GamePage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [snapshot, setSnapshot] = useState(null)
  const [activeTab, setActiveTab] = useState('away')
  const [showLog, setShowLog] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [atBatForm, setAtBatForm] = useState(null)
  const [runnerForm, setRunnerForm] = useState(null)
  const [subForm, setSubForm] = useState(null)
  const [showEndGame, setShowEndGame] = useState(false)
  const [showTransition, setShowTransition] = useState(false)

  const loadSnapshot = useEffectEvent(async () => {
    if (!sessionId) {
      return
    }
    try {
      const next = await api.fetchGame(sessionId)
      setSnapshot(next)
      setActiveTab(next.state.currentHalf === 'TOP' ? 'away' : 'home')
      setError('')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  })

  useEffect(() => {
    loadSnapshot()
  }, [loadSnapshot])

  useEffect(() => {
    if (snapshot?.pendingTransition) {
      setShowTransition(true)
    }
  }, [snapshot?.pendingTransition])

  const commitSnapshot = useEffectEvent((next, successMessage = '') => {
    setSnapshot(next)
    if (successMessage) {
      setToast(successMessage)
      window.setTimeout(() => setToast(''), 2500)
    }
  })

  async function openAtBatModal(resultType = 'GROUND_OUT') {
    if (!sessionId) {
      return
    }
    try {
      const draft = await api.fetchAtBatDraft(sessionId, resultType)
      setAtBatForm((previous) => (previous ? mergeAtBatDraft(previous, draft) : createAtBatForm(draft)))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  function openRunnerModal() {
    const currentRunners = snapshot?.state.runners ?? []
    if (currentRunners.length === 0) {
      setError('No runners on base.')
      return
    }
    const runner = currentRunners[0]
    setRunnerForm({
      fromBase: runner.base,
      toBase: runner.base === 'FIRST' ? 'SECOND' : runner.base === 'SECOND' ? 'THIRD' : 'HOME',
      how: 'SB',
      fielders: '',
    })
  }

  function openSubstitutionModal() {
    setSubForm({
      team: snapshot?.state.currentHalf === 'TOP' ? 'TOP' : 'BOTTOM',
      battingOrder: 1,
      enteringName: '',
      enteringNumber: 0,
      newPosition: '1',
      subType: 'PINCH_HIT',
    })
  }

  async function execute(action, successMessage = '') {
    if (!sessionId) {
      return
    }
    try {
      const next = await action()
      commitSnapshot(next, successMessage)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  useGameHotkeys(
    {
      onNewAtBat: () => openAtBatModal(),
      onRunnerEvent: () => openRunnerModal(),
      onSubstitution: () => openSubstitutionModal(),
      onEndGame: () => setShowEndGame(true),
      onToggleLog: () => setShowLog((previous) => !previous),
      onSwitchTab: () => setActiveTab((previous) => (previous === 'away' ? 'home' : 'away')),
      onSave: () => execute(() => api.saveGame(sessionId), 'Game saved.'),
      onUndo: () => execute(() => api.undo(sessionId), 'Undone.'),
      onRedo: () => execute(() => api.redo(sessionId), 'Redone.'),
      onQuit: () => navigate('/'),
    },
    Boolean(snapshot),
  )

  if (loading) {
    return <main className="shell"><p>Loading game…</p></main>
  }

  if (!snapshot) {
    return <main className="shell"><p>Game unavailable.</p></main>
  }

  const battingSide = activeTab
  const fieldingSide = activeTab === 'away' ? 'home' : 'away'
  const currentTeam = snapshot.scorecards[battingSide]
  const currentTotals = snapshot.inningTotals[battingSide]
  const currentDefense = snapshot.defense[fieldingSide]
  const selectedSubLineup =
    subForm?.team === 'BOTTOM' ? snapshot.teams.home.lineup : snapshot.teams.away.lineup

  return (
    <>
      <main className="game-shell">
        <header className="top-bar">
          <div>
            <p className="eyebrow">⚾  Live Game</p>
            <h1>{snapshot.state.statusLine}</h1>
          </div>
          <div className="top-actions">
            <ToolbarButton shortcut="[N]" onClick={() => openAtBatModal()}>
              New At-Bat
            </ToolbarButton>
            <ToolbarButton shortcut="[R]" onClick={openRunnerModal}>
              Runner
            </ToolbarButton>
            <ToolbarButton shortcut="[S]" onClick={openSubstitutionModal}>
              Sub
            </ToolbarButton>
            <ToolbarButton shortcut="[^S]" onClick={() => execute(() => api.saveGame(sessionId), 'Game saved.')}>
              Save
            </ToolbarButton>
            <ToolbarButton shortcut="[^Z]" onClick={() => execute(() => api.undo(sessionId), 'Undone.')}>
              Undo
            </ToolbarButton>
            <ToolbarButton shortcut="[^Y]" onClick={() => execute(() => api.redo(sessionId), 'Redone.')}>
              Redo
            </ToolbarButton>
            <ToolbarButton shortcut="[G]" onClick={() => setShowEndGame(true)}>
              End Game
            </ToolbarButton>
          </div>
        </header>

        <Scoreline scoreline={snapshot.scoreline} />

        <div className="tab-bar">
          <button
            type="button"
            className={activeTab === 'away' ? 'tab-button tab-button-active' : 'tab-button'}
            onClick={() => setActiveTab('away')}
          >
            [AWAY] {snapshot.teams.away.name}
          </button>
          <button
            type="button"
            className={activeTab === 'home' ? 'tab-button tab-button-active' : 'tab-button'}
            onClick={() => setActiveTab('home')}
          >
            [HOME] {snapshot.teams.home.name}
          </button>
          <button type="button" className="tab-button" onClick={() => setShowLog((previous) => !previous)}>
            {showLog ? '[L] Hide Log' : '[L] Show Log'}
          </button>
        </div>

        <section className="field-layout">
          <Scorecard
            card={currentTeam}
            interactiveHalf={activeTab === 'away' ? 'TOP' : 'BOTTOM'}
            activeState={snapshot.state}
            onOpenAtBat={() => openAtBatModal()}
          />
          <aside className="sidebar-stack">
            <InningTotals
              title={`${snapshot.teams[battingSide].name} Totals`}
              totals={currentTotals}
            />
            <DefensePanel
              title={`${snapshot.teams[fieldingSide].name} Defense`}
              defense={currentDefense}
            />
          </aside>
        </section>

        {showLog ? (
          <section className="log-card">
            <h3>Game Log</h3>
            <ul>
              {snapshot.gameLog.map((item) => (
                <li key={item.id}>{item.text}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </main>

      {atBatForm ? (
        <Modal title={atBatForm.title} onClose={() => setAtBatForm(null)} wide>
          <div className="modal-grid">
            <label className="stacked-field">
              <span>Result</span>
              <select
                value={atBatForm.resultType}
                onChange={async (event) => {
                  const nextResult = event.target.value
                  const draft = await api.fetchAtBatDraft(sessionId, nextResult)
                  setAtBatForm((previous) => mergeAtBatDraft(previous, draft))
                }}
              >
                {RESULT_OPTIONS.map((resultType) => (
                  <option key={resultType} value={resultType}>
                    {resultType}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-field">
              <span>Fielders</span>
              <input
                value={atBatForm.fielders}
                onChange={(event) => setAtBatForm({ ...atBatForm, fielders: event.target.value })}
                placeholder="6-3"
              />
            </label>
            <label className="stacked-field">
              <span>Outs On Play</span>
              <select
                value={atBatForm.outsOnPlay}
                onChange={(event) =>
                  setAtBatForm({
                    ...atBatForm,
                    outsOnPlay: Number(event.target.value),
                    dirty: { ...atBatForm.dirty, outsOnPlay: true },
                  })
                }
              >
                {[0, 1, 2, 3].map((outs) => (
                  <option key={outs} value={outs}>
                    {outs}
                  </option>
                ))}
              </select>
            </label>
            {atBatForm.batterReachedVisible ? (
              <label className="stacked-field">
                <span>Batter Reached</span>
                <input
                  type="checkbox"
                  checked={atBatForm.batterReached}
                  onChange={(event) =>
                    setAtBatForm({
                      ...atBatForm,
                      batterReached: event.target.checked,
                      dirty: { ...atBatForm.dirty, batterReached: true },
                    })
                  }
                />
              </label>
            ) : null}
            {atBatForm.batterDestination ? (
              <label className="stacked-field">
                <span>Batter Destination</span>
                <select
                  value={atBatForm.batterDestination}
                  onChange={(event) =>
                    setAtBatForm({
                      ...atBatForm,
                      batterDestination: event.target.value,
                      dirty: { ...atBatForm.dirty, batterDestination: true },
                    })
                  }
                >
                  {['FIRST', 'SECOND', 'THIRD', 'HOME'].map((base) => (
                    <option key={base} value={base}>
                      {base}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <label className="stacked-field">
              <span>RBI</span>
              <input
                value={atBatForm.rbiCount}
                onChange={(event) => setAtBatForm({ ...atBatForm, rbiCount: Number(event.target.value || 0) })}
                inputMode="numeric"
              />
            </label>
            <label className="stacked-field stacked-field-wide">
              <span>Notes</span>
              <input
                value={atBatForm.notes}
                onChange={(event) => setAtBatForm({ ...atBatForm, notes: event.target.value })}
                placeholder="Optional scorer note"
              />
            </label>
          </div>
          {atBatForm.runnerAdvances.length > 0 ? (
            <div className="runner-defaults">
              <h3>Runner Advances</h3>
              {atBatForm.runnerAdvances.map((advance) => (
                <label className="stacked-field" key={advance.fromBase}>
                  <span>
                    {advance.fromBase}: #{advance.runnerBattingOrder} {advance.runnerName}
                  </span>
                  <select
                    value={advance.toBase}
                    onChange={(event) =>
                      setAtBatForm({
                        ...atBatForm,
                        runnerAdvances: atBatForm.runnerAdvances.map((item) =>
                          item.fromBase === advance.fromBase ? { ...item, toBase: event.target.value } : item,
                        ),
                        dirty: {
                          ...atBatForm.dirty,
                          runnerAdvances: {
                            ...atBatForm.dirty.runnerAdvances,
                            [advance.fromBase]: event.target.value,
                          },
                        },
                      })
                    }
                  >
                    {['FIRST', 'SECOND', 'THIRD', 'HOME', 'OUT'].map((base) => (
                      <option key={base} value={base}>
                        {base}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          ) : null}
          <div className="footer-actions">
            <button type="button" className="ghost-button" onClick={() => setAtBatForm(null)}>
              Cancel
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={async () => {
                await execute(
                  () =>
                    api.commitAtBat(sessionId, {
                      resultType: atBatForm.resultType,
                      fielders: atBatForm.fielders,
                      outsOnPlay: atBatForm.outsOnPlay,
                      batterReached: atBatForm.batterReached,
                      batterDestination: atBatForm.batterDestination,
                      runnerAdvances: atBatForm.runnerAdvances.map((item) => ({
                        fromBase: item.fromBase,
                        toBase: item.toBase,
                      })),
                      rbiCount: atBatForm.rbiCount,
                      notes: atBatForm.notes,
                    }),
                  'At-bat recorded.',
                )
                setAtBatForm(null)
              }}
            >
              Record At-Bat
            </button>
          </div>
        </Modal>
      ) : null}

      {runnerForm ? (
        <Modal title="Baserunner Event" onClose={() => setRunnerForm(null)}>
          <div className="modal-grid">
            <label className="stacked-field">
              <span>Runner</span>
              <select value={runnerForm.fromBase} onChange={(event) => setRunnerForm({ ...runnerForm, fromBase: event.target.value })}>
                {snapshot.state.runners.map((runner) => {
                  const player = lookupPlayer(snapshot.teams, snapshot.state.currentHalf, runner.battingOrder)
                  return (
                    <option key={runner.base} value={runner.base}>
                      {runner.base} — #{runner.battingOrder} {player?.playerName ?? ''}
                    </option>
                  )
                })}
              </select>
            </label>
            <label className="stacked-field">
              <span>Destination</span>
              <select value={runnerForm.toBase} onChange={(event) => setRunnerForm({ ...runnerForm, toBase: event.target.value })}>
                {['SECOND', 'THIRD', 'HOME', 'OUT'].map((base) => (
                  <option key={base} value={base}>
                    {base}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-field">
              <span>How</span>
              <select value={runnerForm.how} onChange={(event) => setRunnerForm({ ...runnerForm, how: event.target.value })}>
                {BASERUNNER_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-field">
              <span>Fielders</span>
              <input value={runnerForm.fielders} onChange={(event) => setRunnerForm({ ...runnerForm, fielders: event.target.value })} />
            </label>
          </div>
          <div className="footer-actions">
            <button type="button" className="ghost-button" onClick={() => setRunnerForm(null)}>
              Cancel
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={async () => {
                await execute(() => api.commitBaserunner(sessionId, runnerForm), 'Runner event recorded.')
                setRunnerForm(null)
              }}
            >
              Record Runner Event
            </button>
          </div>
        </Modal>
      ) : null}

      {subForm ? (
        <Modal title="Substitution" onClose={() => setSubForm(null)}>
          <div className="modal-grid">
            <label className="stacked-field">
              <span>Team</span>
              <select value={subForm.team} onChange={(event) => setSubForm({ ...subForm, team: event.target.value })}>
                <option value="TOP">Away</option>
                <option value="BOTTOM">Home</option>
              </select>
            </label>
            <label className="stacked-field">
              <span>Lineup Slot</span>
              <select
                value={subForm.battingOrder}
                onChange={(event) => setSubForm({ ...subForm, battingOrder: Number(event.target.value) })}
              >
                {selectedSubLineup.map((slot) => (
                  <option key={slot.battingOrder} value={slot.battingOrder}>
                    {slot.battingOrder}. #{slot.playerNumber} {slot.playerName}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-field">
              <span>Sub Type</span>
              <select value={subForm.subType} onChange={(event) => setSubForm({ ...subForm, subType: event.target.value })}>
                {SUB_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-field">
              <span>Entering Name</span>
              <input value={subForm.enteringName} onChange={(event) => setSubForm({ ...subForm, enteringName: event.target.value })} />
            </label>
            <label className="stacked-field">
              <span>Entering Number</span>
              <input
                value={subForm.enteringNumber}
                onChange={(event) => setSubForm({ ...subForm, enteringNumber: Number(event.target.value || 0) })}
                inputMode="numeric"
              />
            </label>
            <label className="stacked-field">
              <span>Position</span>
              <select value={subForm.newPosition} onChange={(event) => setSubForm({ ...subForm, newPosition: event.target.value })}>
                {POSITION_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="footer-actions">
            <button type="button" className="ghost-button" onClick={() => setSubForm(null)}>
              Cancel
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={async () => {
                await execute(() => api.commitSubstitution(sessionId, subForm), 'Substitution recorded.')
                setSubForm(null)
              }}
            >
              Record Substitution
            </button>
          </div>
        </Modal>
      ) : null}

      {showTransition && snapshot.pendingTransition ? (
        <Modal
          title={`Half Inning Complete — ${snapshot.pendingTransition.completedHalf} ${snapshot.pendingTransition.completedInning}`}
          onClose={async () => {
            const next = await api.acknowledgeTransition(sessionId)
            setSnapshot(next)
            setShowTransition(false)
          }}
        >
          <div className="summary-grid">
            {Object.entries(snapshot.pendingTransition.stats).map(([key, value]) => (
              <div key={key}>
                <strong>{key}</strong>
                <span>{value}</span>
              </div>
            ))}
          </div>
          <p>
            {snapshot.pendingTransition.score.awayName} {snapshot.pendingTransition.score.away} —{' '}
            {snapshot.pendingTransition.score.homeName} {snapshot.pendingTransition.score.home}
          </p>
        </Modal>
      ) : null}

      {showEndGame ? (
        <Modal title={snapshot.gameOver ? 'Game Over Ready' : 'End Game?'} onClose={() => setShowEndGame(false)}>
          <p>
            {snapshot.teams.away.name} {snapshot.state.awayScore} — {snapshot.teams.home.name} {snapshot.state.homeScore}
          </p>
          <div className="footer-actions">
            <button type="button" className="ghost-button" onClick={() => setShowEndGame(false)}>
              Continue Scoring
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => execute(() => api.saveGame(sessionId), 'Game saved.')}
            >
              Save
            </button>
            <button type="button" className="primary-button" onClick={() => navigate('/')}>
              Finish
            </button>
          </div>
        </Modal>
      ) : null}

      {toast ? <div className="toast">{toast}</div> : null}
      {error ? <div className="toast toast-error">{error}</div> : null}
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/new" element={<NewGamePage />} />
        <Route path="/load" element={<LoadGamePage />} />
        <Route path="/games/:sessionId" element={<GamePage />} />
      </Routes>
    </BrowserRouter>
  )
}
