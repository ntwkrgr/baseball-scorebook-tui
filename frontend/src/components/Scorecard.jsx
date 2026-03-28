function markerForCell(cell) {
  if (!cell) {
    return null
  }
  if (cell.finalState === 'SCORED') {
    return '◆'
  }
  if (cell.finalState === 'LEFT_ON_BASE') {
    return '●'
  }
  if (cell.finalState === 'OUT') {
    return '✕'
  }
  return null
}

function DiamondCell({ cell, interactive, active, onClick }) {
  const marker = markerForCell(cell)
  const segmentMap = new Set((cell?.segments ?? []).map((segment) => `${segment.fromBase}-${segment.toBase}:${segment.state}`))
  const className = [
    'diamond-cell',
    interactive ? 'diamond-cell-button' : '',
    active ? 'diamond-cell-active' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button type="button" className={className} onClick={onClick} disabled={!interactive}>
      <div className="diamond-frame">
        <span className={`diamond-segment seg-home-first ${segmentMap.has('HOME-FIRST:LIT') ? 'lit' : ''} ${segmentMap.has('HOME-FIRST:SCORED') ? 'scored' : ''}`} />
        <span className={`diamond-segment seg-first-second ${segmentMap.has('FIRST-SECOND:LIT') ? 'lit' : ''} ${segmentMap.has('FIRST-SECOND:SCORED') ? 'scored' : ''}`} />
        <span className={`diamond-segment seg-second-third ${segmentMap.has('SECOND-THIRD:LIT') ? 'lit' : ''} ${segmentMap.has('SECOND-THIRD:SCORED') ? 'scored' : ''}`} />
        <span className={`diamond-segment seg-third-home ${segmentMap.has('THIRD-HOME:LIT') ? 'lit' : ''} ${segmentMap.has('THIRD-HOME:SCORED') ? 'scored' : ''}`} />
        <span className="diamond-base diamond-top">2B</span>
        <span className="diamond-base diamond-left">3B</span>
        <span className="diamond-base diamond-right">1B</span>
        <span className="diamond-base diamond-home">◇</span>
        {marker ? <span className={`diamond-marker diamond-marker-${cell.finalState.toLowerCase()}`}>{marker}</span> : null}
      </div>
      <div className="diamond-meta">
        <strong>{cell?.resultDisplay ?? ''}</strong>
        <span>{cell?.fielders ?? ''}</span>
        <small>{(cell?.annotations ?? []).join(' · ')}</small>
      </div>
    </button>
  )
}

export function Scorecard({ card, interactiveHalf, activeState, onOpenAtBat }) {
  return (
    <div className="scorecard-panel">
      <div className="scorecard-grid scorecard-header">
        <div className="identity-cell">#</div>
        <div className="identity-cell">No.</div>
        <div className="identity-cell">Batter</div>
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

