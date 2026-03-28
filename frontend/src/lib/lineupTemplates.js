const POSITION_CYCLE = ['8', '4', '6', '3', '9', '5', '7', '2', '1']

const AWAY_NAMES = [
  'Carter Vale',
  'Noah Reyes',
  'Mason Pike',
  'Owen Hart',
  'Luca Voss',
  'Gavin Shaw',
  'Silas Reed',
  'Jonah West',
  'Eli Ward',
]

const HOME_NAMES = [
  'Bennett Cole',
  'Grady Lowe',
  'Wyatt Kerr',
  'Dylan Ross',
  'Hudson Tate',
  'Logan Price',
  'Caleb Snow',
  'Rhett Lane',
  'Parker Dean',
]

function buildLineup(teamName, names, baseNumber) {
  return {
    name: teamName,
    lineup: names.map((playerName, index) => ({
      battingOrder: index + 1,
      playerName,
      playerNumber: baseNumber + index,
      position: POSITION_CYCLE[index],
    })),
  }
}

export function generatedLineup(side) {
  if (side === 'away') {
    return buildLineup('Away Test Club', AWAY_NAMES, 11)
  }
  return buildLineup('Home Test Club', HOME_NAMES, 31)
}

