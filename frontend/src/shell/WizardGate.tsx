import { Navigate, Outlet } from 'react-router'
import { useSettings } from '../api/settings'

/** Sends the owner to the setup wizard until it has been finished or skipped once. */
export function WizardGate() {
  const settings = useSettings()
  if (settings.data && !settings.data.wizard_completed) return <Navigate to="/setup" replace />
  return <Outlet />
}
