import { describe, expect, it } from 'vitest'

import { createAtBatForm, mergeAtBatDraft } from './atBatForm'

describe('atBatForm helpers', () => {
  it('preserves a manual runner override when draft defaults recalculate', () => {
    const initial = createAtBatForm({
      battingOrder: 1,
      batterName: 'Carter Vale',
      half: 'TOP',
      inning: 1,
      resultType: 'SINGLE',
      outsOnPlay: 0,
      batterReachedVisible: false,
      batterDestination: 'FIRST',
      runnerDefaults: [
        {
          fromBase: 'FIRST',
          destination: 'SECOND',
          runnerBattingOrder: 9,
          runnerAtBatInning: 1,
          runnerName: 'Eli Ward',
        },
      ],
    })

    const edited = {
      ...initial,
      dirty: {
        ...initial.dirty,
        runnerAdvances: {
          FIRST: 'HOME',
        },
      },
      runnerAdvances: [
        {
          ...initial.runnerAdvances[0],
          toBase: 'HOME',
        },
      ],
    }

    const merged = mergeAtBatDraft(edited, {
      battingOrder: 1,
      batterName: 'Carter Vale',
      half: 'TOP',
      inning: 1,
      resultType: 'DOUBLE',
      outsOnPlay: 0,
      batterReachedVisible: false,
      batterDestination: 'SECOND',
      runnerDefaults: [
        {
          fromBase: 'FIRST',
          destination: 'THIRD',
          runnerBattingOrder: 9,
          runnerAtBatInning: 1,
          runnerName: 'Eli Ward',
        },
      ],
    })

    expect(merged.runnerAdvances[0].toBase).toBe('HOME')
    expect(merged.batterDestination).toBe('SECOND')
  })
})
