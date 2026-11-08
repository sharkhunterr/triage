import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { IntlProvider, useIntl } from 'react-intl'
import en from './en.json'
import fr from './fr.json'

export type Locale = 'en' | 'fr'
const MESSAGES: Record<Locale, Record<string, string>> = { en, fr }
const STORAGE_KEY = 'triage.locale'

function initialLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'fr') return saved
  } catch {
    // storage blocked: the browser's language decides
  }
  return navigator.language.toLowerCase().startsWith('fr') ? 'fr' : 'en'
}

const LocaleContext = createContext<{ locale: Locale; setLocale: (l: Locale) => void }>({
  locale: 'en',
  setLocale: () => {},
})

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale)
  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // not kept, still applied for this visit
    }
  }, [])
  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])
  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale])
  return (
    <LocaleContext.Provider value={value}>
      <IntlProvider locale={locale} messages={MESSAGES[locale]} defaultLocale="en">
        {children}
      </IntlProvider>
    </LocaleContext.Provider>
  )
}

export const useLocale = () => useContext(LocaleContext)

/** `t('key', {values})` — the shorthand used across features. */
export function useT() {
  const intl = useIntl()
  return useCallback(
    (id: string, values?: Record<string, string | number | ReactNode>) =>
      intl.formatMessage({ id }, values as Record<string, string | number>),
    [intl],
  )
}

export const ALL_MESSAGE_IDS = Object.keys(en)
export const FRENCH_MESSAGE_IDS = Object.keys(fr)
