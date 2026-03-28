import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import App from './App'

describe('new game lineup flow', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/new')
    vi.restoreAllMocks()
  })

  it('auto-generates and still allows editing the current team lineup', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: /auto-generate lineup/i }))

    const teamName = screen.getByLabelText(/team name/i)
    expect(teamName).toHaveValue('Away Test Club')

    const firstPlayer = screen.getByPlaceholderText('Player 1')
    expect(firstPlayer).toHaveValue('Carter Vale')

    await user.clear(firstPlayer)
    await user.type(firstPlayer, 'Edited Tester')

    expect(firstPlayer).toHaveValue('Edited Tester')
  })
})

