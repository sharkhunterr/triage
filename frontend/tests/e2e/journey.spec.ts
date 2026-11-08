import { expect, expectAccessible, go, signIn, test } from './fixtures'

// The whole first-day journey, in order (one shared demo database): the setup wizard, categories,
// a preview scan of the intake folder, applying proposals, deciding a held movie, history,
// settings, status. Runs at 360 px and 1280 px.

test.describe.configure({ mode: 'serial' })

test('the setup wizard: test Radarr, pick the intake folder and the libraries, finish', async ({ page }) => {
  await signIn(page, { skipWizard: false })
  await expect(page.getByRole('heading', { name: 'Set up Triage' })).toBeVisible()
  await expectAccessible(page)
  await page.getByRole('button', { name: "Let's go" }).click()

  await expect(page.getByRole('heading', { name: 'Radarr' })).toBeVisible()
  await page.getByRole('button', { name: 'Test' }).click()
  await expect(page.getByText('Radarr (demo)')).toBeVisible()
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Save and continue' }).click()

  await expect(page.getByRole('heading', { name: 'Intake folder' })).toBeVisible()
  await expect(page.getByRole('checkbox', { name: '/movies/Nouveaux' })).toBeChecked()
  await page.getByRole('button', { name: 'Save and continue' }).click()

  await expect(page.getByRole('heading', { name: 'Categories' })).toBeVisible()
  await page.getByRole('button', { name: 'Use this preset' }).click()
  await page.getByLabel('Library for Animation').selectOption('/movies/Dessins animés')
  await page.getByLabel('Library for Movies').selectOption('/movies/Films')
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Save and continue' }).click()

  for (const optional of ['TMDB', 'Local AI', 'Email', 'Overseerr / Jellyseerr']) {
    await expect(page.getByRole('heading', { name: optional })).toBeVisible()
    await page.getByRole('button', { name: 'Skip', exact: true }).click()
  }

  await expect(page.getByRole('heading', { name: 'Ready' })).toBeVisible()
  await expectAccessible(page)
  await page.getByLabel(/Scan \/movies\/Nouveaux now/).uncheck()
  await page.getByRole('button', { name: 'Finish' }).click()
  await expect(page.getByRole('heading', { name: 'Latest decisions' })).toBeVisible()
  await expectAccessible(page)
})

test('categories from the preset, libraries picked', async ({ page }) => {
  await signIn(page)
  await go(page, 'Categories')
  const preset = page.getByRole('button', { name: 'Use this preset' })
  await expect(preset.or(page.getByText('/movies/Films'))).toBeVisible()
  if (await preset.isVisible()) {
    await preset.click()
    await expect(page.getByRole('heading', { name: 'Animation', exact: true })).toBeVisible()
    for (const [name, folder] of [
      ['Animation', '/movies/Dessins animés'],
      ['Movies', '/movies/Films'],
    ] as const) {
      const card = page.locator('section').filter({ has: page.getByRole('heading', { name, exact: true }) })
      await card.getByRole('button', { name: 'Edit' }).click()
      await page.getByRole('dialog').getByLabel('Library').selectOption(folder)
      await page.getByRole('dialog').getByRole('button', { name: 'Save' }).click()
      await expect(page.getByRole('dialog')).toBeHidden()
    }
  }
  await expect(page.getByText('/movies/Films')).toBeVisible()
  await expectAccessible(page)
})

test('a scan of a library proposes moving the misplaced movie, and moves nothing', async ({ page }) => {
  await signIn(page)
  await page.goto('/scans')
  await page.getByLabel('Folder to scan').selectOption('/movies/Films')
  await page.getByRole('button', { name: 'Start the scan' }).click()
  await expect(page.getByText('Finished')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByRole('heading', { name: /To move/ })).toBeVisible()
  await expect(page.getByText('Spirited Away')).toBeVisible()
  await expect(page.getByRole('heading', { name: /Already in place/ })).toBeVisible()
  await expectAccessible(page)
})

test('the review queue: apply the confident proposals, decide a held movie', async ({ page }) => {
  await signIn(page)
  await go(page, 'Review')
  await page.getByRole('tab', { name: /Proposals/ }).click()
  await page.getByRole('button', { name: 'Apply the confident proposals' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click()
  await expect(page.getByText(/being moved/)).toBeVisible()

  await page.getByRole('tab', { name: /To decide/ }).click()
  const held = page.locator('section').filter({ hasText: 'Perfect Blue' }).first()
  await expect(held).toBeVisible()
  await held.getByRole('button', { name: 'Animation' }).click()
  await expect(page.getByText('Done')).toBeVisible()
  await expectAccessible(page)
})

test('history shows the moves and a decision explains itself', async ({ page }) => {
  await signIn(page)
  await go(page, 'History')
  await page.getByText('Toy Story').first().click()
  await expect(page.getByRole('heading', { name: /Toy Story/ })).toBeVisible()
  await expect(page.getByText('Metadata (facts)')).toBeVisible()
  await expect(page.getByText('Local AI (interpretation)')).toBeVisible()
  await expectAccessible(page)
})

test('undo moves: the list first, then every movie goes back', async ({ page }) => {
  await signIn(page)
  await go(page, 'History')
  await page.getByRole('button', { name: 'Undo moves…' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Moves made').selectOption('all')
  await expect(dialog.getByText('Toy Story')).toBeVisible()
  await expectAccessible(page)
  await dialog.getByRole('button', { name: /^Undo \d+ moves?$/ }).click()
  await expect(page.getByText(/going back/)).toBeVisible()
})

test('settings and status pages', async ({ page }) => {
  await signIn(page)
  await go(page, 'Settings')
  await expect(page.getByRole('heading', { name: 'Mode' })).toBeVisible()
  await page.getByRole('button', { name: 'Test' }).first().click()
  await expect(page.getByText('Radarr (demo)')).toBeVisible()
  await expectAccessible(page)
  await page.goto('/status')
  await expect(page.getByText('Radarr (demo)')).toBeVisible()
  await expectAccessible(page)
})
