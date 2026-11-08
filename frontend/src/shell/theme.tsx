import { createContext, type ReactNode, useContext, useEffect, useState } from 'react'

export type ThemeChoice = 'system' | 'light' | 'dark'
const STORAGE_KEY = 'triage.theme'

function stored(): ThemeChoice {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'light' || value === 'dark' || value === 'system') return value
  } catch {
    // storage blocked
  }
  return 'system'
}

const ThemeContext = createContext<{ theme: ThemeChoice; setTheme: (t: ThemeChoice) => void }>({
  theme: 'system',
  setTheme: () => {},
})

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeChoice>(stored)
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && media.matches)
      document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    }
    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [theme])
  const setTheme = (next: ThemeChoice) => {
    setThemeState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // not kept
    }
  }
  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>
}

export const useTheme = () => useContext(ThemeContext)
