export function createAtBatForm(draft) {
  return {
    title: `New At-Bat — #${draft.battingOrder} ${draft.batterName} (${draft.half} ${draft.inning})`,
    resultType: draft.resultType,
    fielders: '',
    outsOnPlay: draft.outsOnPlay,
    batterReached: false,
    batterReachedVisible: draft.batterReachedVisible,
    batterDestination: draft.batterDestination,
    runnerAdvances: draft.runnerDefaults.map((item) => ({
      ...item,
      toBase: item.destination,
    })),
    rbiCount: 0,
    notes: '',
    dirty: {
      outsOnPlay: false,
      batterReached: false,
      batterDestination: false,
      runnerAdvances: {},
    },
  }
}

export function mergeAtBatDraft(previous, draft) {
  const dirtyRunnerAdvances = previous?.dirty?.runnerAdvances ?? {}
  return {
    ...previous,
    title: `New At-Bat — #${draft.battingOrder} ${draft.batterName} (${draft.half} ${draft.inning})`,
    resultType: draft.resultType,
    outsOnPlay: previous?.dirty?.outsOnPlay ? previous.outsOnPlay : draft.outsOnPlay,
    batterReachedVisible: draft.batterReachedVisible,
    batterReached: previous?.dirty?.batterReached ? previous.batterReached : false,
    batterDestination: previous?.dirty?.batterDestination
      ? previous.batterDestination
      : draft.batterDestination,
    runnerAdvances: draft.runnerDefaults.map((item) => ({
      ...item,
      toBase: dirtyRunnerAdvances[item.fromBase] ?? item.destination,
    })),
  }
}

