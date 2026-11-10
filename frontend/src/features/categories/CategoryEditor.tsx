import { Plus, Trash2 } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import type { Category, CategoryInput, RootFolder, RuleInput } from '../../api/categories'
import { useSaveCategory } from '../../api/categories'
import { ApiError } from '../../api/client'
import { Button, Dialog, Field, Input, Select, Switch, Textarea } from '../../design-system'
import { useT } from '../../i18n'
import { RefreshFolders } from './RefreshFolders'

const FIELDS: RuleInput['field'][] = ['genre', 'keyword', 'company', 'certification', 'original_language']
const OPERATORS: NonNullable<RuleInput['operator']>[] = ['is', 'contains', 'is_not']

// Rows get a client-side key so React keeps each rule's inputs while rows are added or removed.
type Row = RuleInput & { key: number }
let nextKey = 1
const row = (rule: RuleInput): Row => ({ ...rule, key: nextKey++ })
const emptyRule = (): Row =>
  row({ field: 'genre', operator: 'is', value: '', weight: 30, decisive: false, excludes: false })

type Effect = 'weight' | 'decisive' | 'excludes'
const effectOf = (rule: RuleInput): Effect =>
  rule.excludes ? 'excludes' : rule.decisive ? 'decisive' : 'weight'

function initial(category?: Category): CategoryInput {
  if (!category) return { name: '', description: '', root_folder_path: null, is_fallback: false, rules: [] }
  return {
    name: category.name,
    description: category.description,
    root_folder_path: category.root_folder_path,
    is_fallback: category.is_fallback,
    rules: category.rules.map(({ field, operator, value, weight, decisive, excludes }) => ({
      field,
      operator,
      value,
      weight,
      decisive,
      excludes,
    })),
  }
}

export function CategoryEditor({
  open,
  onOpenChange,
  category,
  folders,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  category?: Category
  folders: RootFolder[] | undefined
}) {
  const t = useT()
  const [form, setForm] = useState<CategoryInput>(() => initial(category))
  const [rules, setRules] = useState<Row[]>(() => (form.rules ?? []).map(row))
  const save = useSaveCategory()
  const setRule = (key: number, patch: Partial<RuleInput>) =>
    setRules(rules.map((r) => (r.key === key ? { ...r, ...patch } : r)))

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const body = { ...form, rules: rules.filter((r) => r.value.trim()).map(({ key: _key, ...rule }) => rule) }
    save.mutate({ id: category?.id, body }, { onSuccess: () => onOpenChange(false) })
  }
  const errorCode = save.error instanceof ApiError ? save.error.code : undefined
  const libraries = (folders ?? []).filter((f) => !f.is_intake)

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={category ? t('categories.editTitle') : t('categories.newTitle')}
      closeLabel={t('common.close')}
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field
          label={t('categories.name')}
          error={errorCode === 'duplicate_name' ? t('categories.duplicateName') : undefined}
        >
          {(id, desc) => (
            <Input
              id={id}
              required
              maxLength={60}
              aria-describedby={desc}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          )}
        </Field>
        <Field
          label={t('categories.library')}
          hint={folders ? t('categories.libraryHint') : t('categories.libraryUnavailable')}
          error={
            errorCode === 'unknown_root_folder' || errorCode === 'intake_folder'
              ? t(`categories.error.${errorCode}`)
              : undefined
          }
        >
          {(id, desc) => (
            <Select
              id={id}
              aria-describedby={desc}
              value={form.root_folder_path ?? ''}
              onChange={(e) => setForm({ ...form, root_folder_path: e.target.value || null })}
            >
              <option value="">{t('categories.noLibrary')}</option>
              {libraries.map((f) => (
                <option key={f.path} value={f.path} disabled={!f.accessible}>
                  {f.path}
                  {f.accessible ? '' : ` — ${t('categories.inaccessible')}`}
                </option>
              ))}
              {form.root_folder_path && !libraries.some((f) => f.path === form.root_folder_path) && (
                <option value={form.root_folder_path}>{form.root_folder_path}</option>
              )}
            </Select>
          )}
        </Field>
        <div className="-mt-2">
          <RefreshFolders />
        </div>
        <Field label={t('categories.description')} hint={t('categories.descriptionHint')}>
          {(id, desc) => (
            <Textarea
              id={id}
              maxLength={1000}
              aria-describedby={desc}
              value={form.description ?? ''}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          )}
        </Field>
        <Switch
          checked={form.is_fallback ?? false}
          onCheckedChange={(is_fallback) => setForm({ ...form, is_fallback })}
          label={t('categories.fallback')}
          description={t('categories.fallbackHint')}
        />

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-1 text-sm font-medium">{t('categories.rules')}</legend>
          <p className="text-xs text-muted">{t('categories.rulesHint')}</p>
          {rules.length === 0 && <p className="text-sm text-muted">{t('categories.noRules')}</p>}
          {rules.map((rule) => (
            <div
              key={rule.key}
              className="grid grid-cols-2 gap-2 rounded-lg border border-border p-3 sm:grid-cols-12"
            >
              <Select
                aria-label={t('categories.ruleField')}
                className="sm:col-span-3"
                value={rule.field}
                onChange={(e) => setRule(rule.key, { field: e.target.value as RuleInput['field'] })}
              >
                {FIELDS.map((f) => (
                  <option key={f} value={f}>
                    {t(`field.${f}`)}
                  </option>
                ))}
              </Select>
              <Select
                aria-label={t('categories.ruleOperator')}
                className="sm:col-span-2"
                value={rule.operator}
                onChange={(e) => setRule(rule.key, { operator: e.target.value as RuleInput['operator'] })}
              >
                {OPERATORS.map((o) => (
                  <option key={o} value={o}>
                    {t(`operator.${o}`)}
                  </option>
                ))}
              </Select>
              <Input
                aria-label={t('categories.ruleValue')}
                className="col-span-2 sm:col-span-7"
                placeholder={t(`field.${rule.field}.placeholder`)}
                value={rule.value}
                onChange={(e) => setRule(rule.key, { value: e.target.value })}
              />
              <Select
                aria-label={t('categories.ruleEffect')}
                className="col-span-2 sm:col-span-6"
                value={effectOf(rule)}
                onChange={(e) => {
                  const effect = e.target.value as Effect
                  setRule(rule.key, { decisive: effect === 'decisive', excludes: effect === 'excludes' })
                }}
              >
                {(['weight', 'decisive', 'excludes'] as const).map((effect) => (
                  <option key={effect} value={effect}>
                    {t(`categories.effect.${effect}`)}
                  </option>
                ))}
              </Select>
              {rule.excludes ? (
                <span className="self-center text-xs text-muted sm:col-span-4">
                  {t('categories.effect.excludesHint')}
                </span>
              ) : (
                <Input
                  aria-label={t('categories.ruleWeight')}
                  type="number"
                  min={1}
                  max={100}
                  className="sm:col-span-4"
                  value={rule.weight}
                  onChange={(e) => setRule(rule.key, { weight: Number(e.target.value) })}
                />
              )}
              <Button
                variant="ghost"
                size="sm"
                className="justify-self-end sm:col-span-2"
                aria-label={t('categories.removeRule')}
                onClick={() => setRules(rules.filter((r) => r.key !== rule.key))}
              >
                <Trash2 className="size-4" aria-hidden />
              </Button>
            </div>
          ))}
          <Button
            size="sm"
            icon={<Plus className="size-4" aria-hidden />}
            onClick={() => setRules([...rules, emptyRule()])}
          >
            {t('categories.addRule')}
          </Button>
        </fieldset>

        {save.isError && !errorCode?.match(/name|folder/) && (
          <p role="alert" className="text-sm text-danger">
            {save.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button type="submit" variant="primary" loading={save.isPending}>
            {t('common.save')}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
