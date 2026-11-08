import en from '../../src/i18n/en.json'
import fr from '../../src/i18n/fr.json'

// Every screen exists in English and French (Constitution IX): no key may be missing in either.
test('English and French define the same messages', () => {
  expect(Object.keys(fr).sort()).toEqual(Object.keys(en).sort())
})

test('placeholders match between languages', () => {
  const placeholders = (text: string) => (text.match(/\{\w+(?=[,}])/g) ?? []).sort()
  for (const [key, text] of Object.entries(en)) {
    expect(placeholders((fr as Record<string, string>)[key] ?? ''), key).toEqual(placeholders(text))
  }
})
