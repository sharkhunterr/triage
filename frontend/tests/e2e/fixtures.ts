import AxeBuilder from '@axe-core/playwright'
import { test as base, expect, type Page } from '@playwright/test'

export const USER = { username: 'owner', password: 'correct horse battery' }

/** Signs in, creating the owner account on the very first run. English interface. */
export async function signIn(page: Page) {
  await page.addInitScript(() => localStorage.setItem('triage.locale', 'en'))
  await page.goto('/')
  const setup = page.getByRole('heading', { name: 'Welcome to Triage' })
  const login = page.getByRole('heading', { name: 'Sign in' })
  await expect(setup.or(login)).toBeVisible()
  if (await setup.isVisible()) {
    await page.getByLabel('Username').fill(USER.username)
    await page.getByLabel('Password', { exact: true }).fill(USER.password)
    await page.getByLabel('Confirm the password').fill(USER.password)
    await page.getByRole('button', { name: 'Create my account' }).click()
  } else {
    await page.getByLabel('Username').fill(USER.username)
    await page.getByLabel('Password').fill(USER.password)
    await page.getByRole('button', { name: 'Sign in' }).click()
  }
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
}

/** No serious or critical accessibility violation on the current page. */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([])
}

export async function go(page: Page, label: string) {
  // The sidebar on desktop, the bottom tab bar on mobile; Scans and Status are reached from links there.
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('link', { name: label })
    .first()
    .click()
}

export const test = base
export { expect }
