import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { isUnauthorized } from './api/client'
import { ToastProvider } from './design-system'
import { CategoriesPage } from './features/categories/CategoriesPage'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { DecisionPage } from './features/decisions/DecisionPage'
import { HistoryPage } from './features/decisions/HistoryPage'
import { ReviewPage } from './features/review/ReviewPage'
import { ScansPage } from './features/scans/ScansPage'
import { SettingsPage } from './features/settings/SettingsPage'
import { StatusPage } from './features/status/StatusPage'
import { I18nProvider } from './i18n'
import { AuthGate } from './shell/AuthGate'
import { Layout } from './shell/Layout'
import { ThemeProvider } from './shell/theme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => !isUnauthorized(error) && count < 2,
      refetchOnWindowFocus: true,
      staleTime: 5_000,
    },
  },
})

export function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <BrowserRouter>
              <AuthGate>
                <Routes>
                  <Route element={<Layout />}>
                    <Route index element={<DashboardPage />} />
                    <Route path="review" element={<ReviewPage />} />
                    <Route path="history" element={<HistoryPage />} />
                    <Route path="decisions/:id" element={<DecisionPage />} />
                    <Route path="scans" element={<ScansPage />} />
                    <Route path="categories" element={<CategoriesPage />} />
                    <Route path="settings" element={<SettingsPage />} />
                    <Route path="status" element={<StatusPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Route>
                </Routes>
              </AuthGate>
            </BrowserRouter>
          </ToastProvider>
        </QueryClientProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
