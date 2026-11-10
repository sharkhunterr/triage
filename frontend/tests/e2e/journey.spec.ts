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

test('a check of a library shows its gaps, moves nothing, and keeps them out of the review', async ({
  page,
}) => {
  await signIn(page)
  await go(page, 'Check')
  await expect(page.getByRole('switch', { name: /Respect locks/ })).toBeChecked()
  await page.getByLabel('Folder to scan').selectOption('/movies/Films')
  await page.getByRole('button', { name: 'Start the scan' }).click()
  await expect(page.getByText(/^Finished/)).toBeVisible({ timeout: 20_000 })
  await expect(page.getByRole('tab', { name: /^Gaps \(1\)/ })).toBeVisible()
  await expect(page.getByText('Spirited Away')).toBeVisible()
  // where it is, and where Triage would send it
  const gap = page.getByRole('listitem').filter({ hasText: 'Spirited Away' })
  await expect(gap.getByText('Movies')).toBeVisible()
  await expect(gap.getByText('Animation').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Leave it there' })).toBeVisible()
  await expectAccessible(page)
  await page.getByRole('tab', { name: /^In place/ }).click()
  await expect(page.getByRole('tab', { name: /^In place/ })).toHaveAttribute('aria-selected', 'true')
  await go(page, 'Review')
  await expect(page.getByText('Spirited Away')).toHaveCount(0)
})

test('decide all, and analyze with a choice of scope', async ({ page }) => {
  await signIn(page)
  await go(page, 'Review')
  await page.getByRole('button', { name: 'Decide all…' }).click()
  const dialog = page.getByRole('dialog')
  const roger = dialog.getByRole('group', { name: /Who Framed Roger Rabbit/ })
  await expect(roger.getByRole('radio', { name: 'Later' })).toBeChecked()
  await dialog.getByRole('button', { name: 'Best guess everywhere' }).click()
  await expect(roger.getByRole('radio', { name: 'Later' })).not.toBeChecked()
  await expectAccessible(page)
  await dialog.getByRole('button', { name: 'Cancel' }).click()

  await page.getByRole('button', { name: 'Analyze…' }).click()
  await page
    .getByRole('dialog')
    .getByLabel(/New only/)
    .check()
  await expect(page.getByRole('dialog').getByRole('button', { name: /^Analyze \d+ movies?$/ })).toBeVisible()
  await expectAccessible(page)
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click()
})

test('the review queue: apply the confident proposals, decide a held movie', async ({ page }) => {
  await signIn(page)
  await go(page, 'Review')
  await page.getByRole('tab', { name: /Proposals/ }).click()
  await page.getByRole('button', { name: 'Apply the confident proposals' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click()
  await expect(page.getByText(/being moved/)).toBeVisible()

  await page.getByRole('tab', { name: /To decide/ }).click()
  const held = page.locator('section').filter({ hasText: 'Who Framed Roger Rabbit' }).first()
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
  await page.getByRole('button', { name: 'Analyze' }).click()
  await expect(page.getByText("Analyzed with today's rules")).toBeVisible()
})

test('a movie decided by hand is locked, and the lock can be removed', async ({ page }) => {
  await signIn(page)
  await go(page, 'History')
  const roger = page.getByRole('listitem').filter({ hasText: 'Who Framed Roger Rabbit' }).first()
  // locked once the move is done: the list is read again until then
  await expect(async () => {
    await page.reload()
    await expect(roger.getByRole('img', { name: /Locked in/ })).toBeVisible({ timeout: 2_000 })
  }).toPass({ timeout: 20_000 })
  await roger.click()
  await page.getByRole('button', { name: /Locked in/ }).click()
  await page.getByRole('button', { name: 'Unlock' }).click()
  await expect(page.getByText(/Lock removed/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Unlock' })).toHaveCount(0)
})

test('the dashboard chart: sorted, by category, analysed', async ({ page }) => {
  await signIn(page)
  await page.goto('/')
  const chart = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Last 30 days' }) })
  await chart.getByRole('button', { name: 'By category' }).click()
  await expect(chart.getByText(/movies? sorted into \d+ categor/)).toBeVisible()
  await chart.getByRole('button', { name: 'Analysed' }).click()
  await expect(chart.getByText(/analysed · \d+ % sure/)).toBeVisible()
  await expect(chart.getByRole('listitem').filter({ hasText: /^ ?In doubt$/ })).toBeVisible()
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

test('the activity page shows the last analyses step by step', async ({ page }) => {
  await signIn(page)
  await page.goto('/activity')
  await expect(page.getByRole('heading', { name: 'Last jobs' })).toBeVisible()
  await expect(page.getByText('Classify a movie').first()).toBeVisible()
  await expect(page.getByText('Rules').first()).toBeVisible()
  await expectAccessible(page)
})

test('settings and status pages', async ({ page }) => {
  await signIn(page)
  await go(page, 'Settings')
  await expect(page.getByRole('heading', { name: 'Mode' })).toBeVisible()
  await page.getByRole('button', { name: 'Test' }).first().click()
  await expect(page.getByText('Radarr (demo)')).toBeVisible()
  await page.getByRole('button', { name: 'Refresh folders' }).click()
  await expect(page.getByText('Radarr folders refreshed: 3 folders')).toBeVisible()
  await expectAccessible(page)
  await page.goto('/status')
  await expect(page.getByText('Radarr (demo)')).toBeVisible()
  await expectAccessible(page)
})
