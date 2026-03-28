const JSON_HEADERS = {
  'Content-Type': 'application/json',
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: JSON_HEADERS,
    ...options,
  })

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const detail = payload?.detail ?? payload?.message ?? response.statusText
    throw new Error(detail || 'Request failed')
  }

  return payload
}

export const api = {
  health: () => request('/api/health'),
  listSavedGames: () => request('/api/games/saved'),
  createGame: (body) =>
    request('/api/games', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  loadGame: (filename) =>
    request('/api/games/load', {
      method: 'POST',
      body: JSON.stringify({ filename }),
    }),
  fetchGame: (sessionId) => request(`/api/games/${sessionId}`),
  fetchAtBatDraft: (sessionId, resultType) =>
    request(`/api/games/${sessionId}/drafts/at-bat`, {
      method: 'POST',
      body: JSON.stringify({ resultType }),
    }),
  commitAtBat: (sessionId, body) =>
    request(`/api/games/${sessionId}/commands/at-bat`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  commitBaserunner: (sessionId, body) =>
    request(`/api/games/${sessionId}/commands/baserunner`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  commitSubstitution: (sessionId, body) =>
    request(`/api/games/${sessionId}/commands/substitution`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  undo: (sessionId) =>
    request(`/api/games/${sessionId}/undo`, {
      method: 'POST',
    }),
  redo: (sessionId) =>
    request(`/api/games/${sessionId}/redo`, {
      method: 'POST',
    }),
  saveGame: (sessionId, filename = null) =>
    request(`/api/games/${sessionId}/save`, {
      method: 'POST',
      body: JSON.stringify({ filename }),
    }),
  acknowledgeTransition: (sessionId) =>
    request(`/api/games/${sessionId}/acknowledge-transition`, {
      method: 'POST',
    }),
}

