import { AsciiDiamond } from './AsciiDiamond'

function DiamondCell({ cell, interactive, active, onClick }) {
  const className = [
    'diamond-cell',
    interactive ? 'diamond-cell-button' : '',
    active ? 'diamond-cell-active' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button type="button" className={className} onClick={onClick} disabled={!interactive}>
      <AsciiDiamond cell={cell} />
    </button>
  )
}

export function Scorecard({ card, interactiveHalf, activeState, onOpenAtBat }) {
  return (
    <div className="scorecard-panel">
      <div className="scorecard-grid scorecard-header">
        <div className="identity-cell">#</div>
        <div className="identity-cell">No.</div>
        <div className="identity-cell batter-cell">Batter</div>
        <div className="identity-cell">Pos</div>
        {card.innings.map((inning) => (
          <div key={inning} className="inning-head">
            {inning}
          </div>
        ))}
      </div>
      {card.rows.map((row) => (
        <div key={row.battingOrder} className="scorecard-grid scorecard-row">
          <div className="identity-cell">{row.battingOrder}</div>
          <div className="identity-cell jersey-cell">#{row.playerNumber}</div>
          <div className="identity-cell batter-cell">{row.playerName}</div>
          <div className="identity-cell">{row.position}</div>
          {row.cells.map((cell, index) => {
            const inning = card.innings[index]
            const isActive =
              activeState?.currentHalf === interactiveHalf &&
              activeState?.currentBatter?.battingOrder === row.battingOrder &&
              activeState?.currentInning === inning
            return (
              <DiamondCell
                key={`${row.battingOrder}-${inning}`}
                cell={cell}
                interactive={activeState?.currentHalf === interactiveHalf}
                active={isActive}
                onClick={() => onOpenAtBat?.()}
              />
            )
          })}
        </div>
      ))}
    </div>
  )
}


