import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { useGameHotkeys } from './useGameHotkeys'

function Harness() {
  const [count, setCount] = useState(0)
  useGameHotkeys(
    {
      onNewAtBat: () => setCount((value) => value + 1),
    },
    true,
  )

  return (
    <>
      <input aria-label="editor" />
      <output aria-label="count">{count}</output>
    </>
  )
}

describe('useGameHotkeys', () => {
  it('ignores shortcut keys while an input is focused', async () => {
    const user = userEvent.setup()
    render(<Harness />)

    await user.keyboard('n')
    expect(screen.getByLabelText('count')).toHaveTextContent('1')

    await user.click(screen.getByLabelText('editor'))
    await user.keyboard('n')

    expect(screen.getByLabelText('count')).toHaveTextContent('1')
  })
})

