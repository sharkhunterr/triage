import { describe, expect, it } from 'vitest'
import { backFrom } from '../../src/features/decisions/parts'

// A movie's sheet goes back where it was opened from — its list page and filters kept —, else the history.
describe('backFrom', () => {
  it('returns to the page the sheet was opened from', () => {
    expect(backFrom({ from: '/' })).toEqual({ to: '/', label: 'nav.dashboard' })
    expect(backFrom({ from: '/review?tab=proposed&page=3' })).toEqual({
      to: '/review?tab=proposed&page=3',
      label: 'nav.review',
    })
    expect(backFrom({ from: '/activity' })).toEqual({ to: '/activity', label: 'nav.activity' })
    expect(backFrom({ from: '/history?status=held' }).label).toBe('nav.history')
    expect(backFrom({ from: '/scans' }).label).toBe('nav.scans')
  })

  it('falls back on the history, and never leaves the app', () => {
    expect(backFrom(null)).toEqual({ to: '/history', label: 'nav.history' })
    expect(backFrom({ from: 'https://elsewhere.example' })).toEqual({ to: '/history', label: 'nav.history' })
    expect(backFrom({ from: '//elsewhere.example' })).toEqual({ to: '/history', label: 'nav.history' })
    expect(backFrom({ from: '/categories' })).toEqual({ to: '/categories', label: 'common.back' })
  })
})
