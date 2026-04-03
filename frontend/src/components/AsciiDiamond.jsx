/**
 * AsciiDiamond — Renders a miniature baseball diamond using ASCII/Unicode art.
 *
 * Ported from the original Python TUI widget (baseball_scorebook/widgets/diamond.py).
 *
 * Layout (8 lines × 14 chars):
 *       2B
 *      ╱  ╲
 *    3B    1B
 *      ╲  ╱
 *       ◇
 *   6-3  1B
 *   (annot)
 */

const MARKER_SCORED = '◆'
const MARKER_LOB = '●'
const MARKER_OUT = '✕'
const MARKER_HOME = '◇'

/** Build a lookup: "BASE1-BASE2" → "DIM"|"LIT"|"SCORED" */
function buildSegMap(segments) {
  const map = {}
  for (const seg of segments ?? []) {
    map[`${seg.fromBase}-${seg.toBase}`] = seg.state
  }
  return map
}

/** Return CSS class name for a segment state. */
function segClass(state) {
  if (state === 'SCORED') return 'seg-scored'
  if (state === 'LIT') return 'seg-lit'
  return 'seg-dim'
}

/**
 * Return [glyph2, cssClass] for the home plate position.
 * glyph2 is always 1 character (home plate label is 1 char: ◇/◆/✕).
 */
function homeMarker(cell) {
  if (cell.finalBase === 'HOME') {
    if (cell.finalState === 'SCORED') return [MARKER_SCORED, 'base-scored']
    if (cell.finalState === 'OUT') return [MARKER_OUT, 'base-out']
  }
  return [MARKER_HOME, 'seg-dim']
}

/**
 * Return [glyph, cssClass] for a non-home base.
 * Always returns 2-character glyph to maintain alignment.
 * Returns null if the runner is not at this base.
 */
function baseMarker(cell, base) {
  if (cell.finalBase !== base) return null
  // Pad single-char markers to 2 chars for alignment with "1B"/"2B"/"3B"
  if (cell.finalState === 'LEFT_ON_BASE') return [MARKER_LOB + ' ', 'base-lob']
  if (cell.finalState === 'OUT') return [MARKER_OUT + ' ', 'base-out']
  if (cell.finalState === 'RUNNING') return [MARKER_LOB + ' ', 'base-running']
  return null
}

/**
 * A "text part" is { text, cls } where cls is a CSS class name.
 * We build an array of parts per line, then render them as <span> elements.
 */
function p(text, cls = 'seg-dim') {
  return { text, cls }
}

/** Render an empty (no at-bat) diamond — 8 lines of dim ASCII art. */
function buildEmptyLines() {
  return [
    [p('      2B      ')],
    [p('     '), p('╱', 'seg-dim'), p('  '), p('╲', 'seg-dim'), p('     ')],
    [p('   3B    1B   ')],
    [p('     '), p('╲', 'seg-dim'), p('  '), p('╱', 'seg-dim'), p('     ')],
    [p('      ◇       ')],
    [p('              ')],
    [p('              ')],
    [p('              ')],
  ]
}

/** Center a string to exactly `width` chars, padding with spaces. */
function center(str, width) {
  const s = str.slice(0, width)
  const pad = width - s.length
  const left = Math.floor(pad / 2)
  const right = pad - left
  return ' '.repeat(left) + s + ' '.repeat(right)
}

/** Build the 8 lines of ASCII parts for a populated cell. */
function buildFilledLines(cell) {
  const segMap = buildSegMap(cell.segments)

  const clsH1 = segClass(segMap['HOME-FIRST'])
  const cls12 = segClass(segMap['FIRST-SECOND'])
  const cls23 = segClass(segMap['SECOND-THIRD'])
  const cls3H = segClass(segMap['THIRD-HOME'])

  // Second base (in center top — single char in original but "2B" is 2 chars)
  const sm2 = baseMarker(cell, 'SECOND')
  const [g2, c2] = sm2 ?? ['2B', 'base-normal']

  // Third base
  const sm3 = baseMarker(cell, 'THIRD')
  const [g3, c3] = sm3 ?? ['3B', 'base-normal']

  // First base
  const sm1 = baseMarker(cell, 'FIRST')
  const [g1, c1] = sm1 ?? ['1B', 'base-normal']

  // Home plate (always 1 char)
  const [gH, cH] = homeMarker(cell)

  // Result label — center to 14 chars
  const resultDisplay = cell.resultDisplay ?? ''
  const fielders = cell.fielders ?? ''
  const label = fielders ? `${fielders}  ${resultDisplay}` : resultDisplay
  const labelLine = center(label, 14)

  // Annotations — center to 14 chars
  const annots = (cell.annotations ?? []).join(' · ')
  const annotLine = annots ? center(annots, 14) : ''

  return [
    // Line 0:  "      2B      "
    [p('      '), p(g2, c2), p('      ')],
    // Line 1:  "     ╱  ╲     "
    [p('     '), p('╱', cls23), p('  '), p('╲', cls12), p('     ')],
    // Line 2:  "   3B    1B   "
    [p('   '), p(g3, c3), p('    '), p(g1, c1), p('   ')],
    // Line 3:  "     ╲  ╱     "
    [p('     '), p('╲', cls3H), p('  '), p('╱', clsH1), p('     ')],
    // Line 4:  "      ◇       " (1 char home + 7 spaces = 8 right)
    [p('      '), p(gH, cH), p('       ')],
    // Line 5: result label
    [p(labelLine, 'diamond-result')],
    // Line 6: annotations
    annotLine ? [p(annotLine, 'diamond-annot')] : [p('              ')],
    // Line 7: blank
    [p('              ')],
  ]
}

/**
 * AsciiDiamond component.
 *
 * Props:
 *   cell — the DiamondState snapshot object from the API (may be null/undefined)
 */
export function AsciiDiamond({ cell }) {
  const lines = cell ? buildFilledLines(cell) : buildEmptyLines()

  return (
    <pre className="ascii-diamond" aria-label={cell ? `${cell.resultDisplay ?? ''} ${cell.fielders ?? ''}`.trim() : 'empty'}>
      {lines.map((parts, lineIdx) => (
        <span key={lineIdx} className="ascii-diamond-line">
          {parts.map((part, partIdx) => (
            <span key={partIdx} className={part.cls}>
              {part.text}
            </span>
          ))}
          {'\n'}
        </span>
      ))}
    </pre>
  )
}
