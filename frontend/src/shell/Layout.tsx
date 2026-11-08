import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  FolderSearch,
  History,
  Inbox,
  LayoutDashboard,
  LogOut,
  Moon,
  Settings,
  Shapes,
  Sun,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router'
import { api } from '../api/client'
import { cx } from '../design-system'
import { type Locale, useLocale, useT } from '../i18n'
import { useTheme } from './theme'

type Counts = { review: number }

const NAV = [
  { to: '/', key: 'nav.dashboard', icon: LayoutDashboard, mobile: true },
  { to: '/review', key: 'nav.review', icon: Inbox, mobile: true, badge: true },
  { to: '/history', key: 'nav.history', icon: History, mobile: true },
  { to: '/scans', key: 'nav.scans', icon: FolderSearch, mobile: false },
  { to: '/categories', key: 'nav.categories', icon: Shapes, mobile: true },
  { to: '/status', key: 'nav.status', icon: Activity, mobile: false },
  { to: '/settings', key: 'nav.settings', icon: Settings, mobile: true },
] as const

function useReviewCount() {
  return useQuery({
    queryKey: ['review-count'],
    queryFn: () => api<Counts>('/review/count'),
    refetchInterval: 30_000,
  }).data?.review
}

export function Layout() {
  const t = useT()
  const reviewCount = useReviewCount()
  const { locale, setLocale } = useLocale()
  const { theme, setTheme } = useTheme()
  const queryClient = useQueryClient()
  const logout = useMutation({
    mutationFn: () => api('/auth/logout', { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries(),
  })
  const dark = theme === 'dark' || (theme === 'system' && document.documentElement.dataset.theme === 'dark')

  const link = (item: (typeof NAV)[number], compact = false) => (
    <NavLink
      key={item.to}
      to={item.to}
      end={item.to === '/'}
      className={({ isActive }) =>
        cx(
          'relative flex items-center gap-3 rounded-lg text-sm font-medium transition-colors',
          compact ? 'flex-1 flex-col gap-1 py-2 text-[11px]' : 'px-3 py-2.5',
          isActive ? 'bg-accent/12 text-accent' : 'text-muted hover:bg-surface-2 hover:text-text',
        )
      }
    >
      <item.icon className={compact ? 'size-5' : 'size-4'} aria-hidden />
      <span>{t(item.key)}</span>
      {'badge' in item && reviewCount ? (
        <span
          className={cx(
            'rounded-full bg-accent px-1.5 text-[10px] font-semibold text-accent-contrast',
            compact ? 'absolute top-1 right-[calc(50%-1.4rem)]' : 'ml-auto',
          )}
        >
          <span aria-hidden>{reviewCount}</span>
          <span className="sr-only">{t('nav.reviewCount', { count: reviewCount })}</span>
        </span>
      ) : null}
    </NavLink>
  )

  return (
    <div className="min-h-dvh lg:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50">
        {t('nav.skip')}
      </a>
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface p-4 lg:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <img src="/favicon.svg" alt="" className="size-7" />
          <span className="text-lg font-semibold">Triage</span>
        </div>
        <nav aria-label={t('nav.main')} className="flex flex-col gap-1">
          {NAV.map((item) => link(item))}
        </nav>
        <div className="mt-auto flex flex-col gap-2 border-t border-border pt-4">
          <label className="flex items-center justify-between text-sm text-muted">
            {t('nav.language')}
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value as Locale)}
              className="rounded-md border border-border bg-surface px-2 py-1 text-text"
            >
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </label>
          <button
            type="button"
            onClick={() => setTheme(dark ? 'light' : 'dark')}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted hover:bg-surface-2"
          >
            {dark ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
            {dark ? t('nav.lightTheme') : t('nav.darkTheme')}
          </button>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted hover:bg-surface-2"
          >
            <LogOut className="size-4" aria-hidden />
            {t('nav.logout')}
          </button>
        </div>
      </aside>

      <main id="main" className="mx-auto w-full max-w-5xl px-4 pt-4 pb-24 lg:px-8 lg:pt-8 lg:pb-8">
        <div className="mb-4 flex items-center gap-2 lg:hidden">
          <img src="/favicon.svg" alt="" className="size-6" />
          <span className="font-semibold">Triage</span>
        </div>
        <Outlet />
      </main>

      <nav
        aria-label={t('nav.main')}
        className="fixed inset-x-0 bottom-0 z-30 flex gap-1 border-t border-border bg-surface px-2 pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        {NAV.filter((i) => i.mobile).map((item) => link(item, true))}
      </nav>
    </div>
  )
}
