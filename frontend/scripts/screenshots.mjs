// Screenshots for the README, taken from Triage in demo mode (TRIAGE_DEMO=1).
// Usage: node scripts/screenshots.mjs <base-url> <output-dir>   (PW_CHROMIUM_PATH to use a local Chromium)
import { chromium } from '@playwright/test'

const [base = 'http://127.0.0.1:9595', out = '../docs/images'] = process.argv.slice(2)
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined })

async function session(viewport, scale = 1) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: scale, colorScheme: 'dark' })
  await context.addInitScript(() => localStorage.setItem('triage.locale', 'en'))
  const page = await context.newPage()
  await page.goto(base)
  const setup = page.getByRole('heading', { name: 'Welcome to Triage' })
  await page.getByRole('heading', { name: /Welcome to Triage|Sign in/ }).waitFor()
  if (await setup.isVisible()) {
    await page.getByLabel('Username').fill('owner')
    await page.getByLabel('Password', { exact: true }).fill('correct horse battery')
    await page.getByLabel('Confirm the password').fill('correct horse battery')
    await page.getByRole('button', { name: 'Create my account' }).click()
  } else {
    await page.getByLabel('Username').fill('owner')
    await page.getByLabel('Password').fill('correct horse battery')
    await page.getByRole('button', { name: 'Sign in' }).click()
  }
  await page.getByRole('heading', { name: /Dashboard|Set up Triage/ }).waitFor()
  if (await page.getByRole('heading', { name: 'Set up Triage' }).isVisible()) {
    if (viewport.width > 1000) {
      await page.getByRole('button', { name: "Let's go" }).click()
      await page.getByRole('button', { name: 'Test' }).click()
      await page.getByText('Radarr (demo)').waitFor()
      await page.screenshot({ path: `${out}/wizard.png` })
    }
    await page.getByRole('button', { name: 'Skip the setup' }).click()
    await page.getByRole('heading', { name: 'Dashboard' }).waitFor()
  }
  return { context, page }
}

const shot = (page, name) => page.screenshot({ path: `${out}/${name}.png` })
const settle = (page) => page.waitForTimeout(800)

const { context, page } = await session({ width: 1280, height: 860 })

// Categories from the preset, libraries picked
await page.goto(`${base}/categories`)
await page.getByRole('button', { name: 'Use this preset' }).click()
for (const [name, folder] of [
  ['Animation', '/movies/Dessins animés'],
  ['Movies', '/movies/Films'],
]) {
  const card = page.locator('section').filter({ has: page.getByRole('heading', { name, exact: true }) })
  await card.getByRole('button', { name: 'Edit' }).click()
  await page.getByRole('dialog').getByLabel('Library').selectOption(folder)
  await page.getByRole('dialog').getByRole('button', { name: 'Save' }).click()
  await page.getByRole('dialog').waitFor({ state: 'hidden' })
}
await settle(page)
await shot(page, 'categories')
await page
  .locator('section')
  .filter({ has: page.getByRole('heading', { name: 'Animation', exact: true }) })
  .getByRole('button', { name: 'Edit' })
  .click()
await settle(page)
await shot(page, 'category-editor')
await page.keyboard.press('Escape')

// A scan of the Films library
await page.goto(`${base}/scans`)
await page.getByLabel('Folder to scan').selectOption('/movies/Films')
await page.getByRole('button', { name: 'Start the scan' }).click()
await page.getByText('Finished').waitFor({ timeout: 20_000 })
await settle(page)
await shot(page, 'scan')

// Review queue, then apply the confident proposals
await page.goto(`${base}/review`)
await page.getByRole('tab', { name: /To decide/ }).click()
await settle(page)
await shot(page, 'review')
await page.getByRole('tab', { name: /Proposals/ }).click()
await page.getByRole('button', { name: 'Apply the confident proposals' }).click()
await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click()
await page.waitForTimeout(3000)

// A decision explained
await page.goto(`${base}/history`)
await page.getByText('Toy Story').first().click()
await page.getByText('Metadata (facts)').waitFor()
await settle(page)
await page.screenshot({ path: `${out}/decision.png`, fullPage: true })

await page.goto(base)
await settle(page)
await shot(page, 'dashboard')
await page.goto(`${base}/settings`)
await settle(page)
await shot(page, 'settings')
await context.close()

// Phone
const phone = await session({ width: 390, height: 844 }, 2)
await phone.page.goto(`${base}/review`)
await phone.page.getByRole('tab', { name: /To decide/ }).click()
await settle(phone.page)
await phone.page.screenshot({ path: `${out}/mobile-review.png` })
await phone.page.goto(base)
await settle(phone.page)
await phone.page.screenshot({ path: `${out}/mobile-dashboard.png` })
await phone.context.close()

await browser.close()
console.log('screenshots written to', out)
