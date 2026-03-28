import { expect, test } from '@playwright/test'

test('can create a game with generated lineups and record an at-bat', async ({ page }) => {
  await page.goto('/new')

  await page.getByRole('button', { name: /auto-generate lineup/i }).click()
  await page.getByRole('button', { name: /^continue$/i }).click()

  await page.getByRole('button', { name: /auto-generate lineup/i }).click()
  await page.getByRole('button', { name: /^continue$/i }).click()

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Inning 1 TOP')

  await page.getByRole('button', { name: /new at-bat/i }).click()
  await page.getByRole('dialog', { name: /new at-bat/i }).getByRole('button', { name: /record at-bat/i }).click()

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Outs 1')
  await expect(page.getByText(/at-bat recorded/i)).toBeVisible()
})
