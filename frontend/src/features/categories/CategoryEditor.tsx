import { Plus, Trash2 } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import type { Category, CategoryInput, RootFolder, RuleInput } from '../../api/categories'
import { useSaveCategory } from '../../api/categories'
import { ApiError } from '../../api/client'
import { Button, Dialog, Field, Input, Select, Switch, Textarea } from '../../design-system'
import { useT } from '../../i18n'

const FIELDS: RuleInput['field'][] = ['genre', 'keyword', 'company', 'certification', 'original_language']
const OPERATORS: NonNullable<RuleInput['operator']>[] = ['is', 'contains', 'is_not']

const emptyRule = (): RuleInput => ({
  field: 'genre',
  operator: 'is',
  value: '',
  weight: 30,
  decisive: false,
})

function initial(category?: Category): CategoryInput {
  if (!category) return { name: '', description: '', root_folder_path: null, is_fallback: false, rules: [] }
  return {
    name: category.name,
    description: category.description,
    root_folder_path: category.root_folder_path,
    is_fallback: category.is_fallback,
    rules: category.rules.map(({ field, operator, value, weight, decisive }) => ({
      field,
      operator,
      value,
      weight,
      decisive,
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
  const save = useSaveCategory()
  const rules = form.rules ?? []
  const setRule = (index: number, patch: Partial<RuleInput>) =>
    setForm({ ...form, rules: rules.map((r, i) => (i === index ? { ...r, ...patch } : r)) })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const body = { ...form, rules: rules.filter((r) => r.value.trim()) }
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
          {rules.map((rule, index) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: rows have no identity until saved
            <div
              key={index}
              className="grid grid-cols-2 gap-2 rounded-lg border border-border p-3 sm:grid-cols-12"
            >
              <Select
                aria-label={t('categories.ruleField')}
                className="sm:col-span-3"
                value={rule.field}
                onChange={(e) => setRule(index, { field: e.target.value as RuleInput['field'] })}
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
                onChange={(e) => setRule(index, { operator: e.target.value as RuleInput['operator'] })}
              >
                {OPERATORS.map((o) => (
                  <option key={o} value={o}>
                    {t(`operator.${o}`)}
                  </option>
                ))}
              </Select>
              <Input
                aria-label={t('categories.ruleValue')}
                className="col-span-2 sm:col-span-4"
                placeholder={t(`field.${rule.field}.placeholder`)}
                value={rule.value}
                onChange={(e) => setRule(index, { value: e.target.value })}
              />
              <Input
                aria-label={t('categories.ruleWeight')}
                type="number"
                min={1}
                max={100}
                className="sm:col-span-1"
                value={rule.weight}
                onChange={(e) => setRule(index, { weight: Number(e.target.value) })}
              />
              <label className="flex items-center gap-2 text-xs sm:col-span-1">
                <input
                  type="checkbox"
                  checked={rule.decisive ?? false}
                  onChange={(e) => setRule(index, { decisive: e.target.checked })}
                />
                {t('categories.decisive')}
              </label>
              <Button
                variant="ghost"
                size="sm"
                className="justify-self-end sm:col-span-1"
                aria-label={t('categories.removeRule')}
                onClick={() => setForm({ ...form, rules: rules.filter((_, i) => i !== index) })}
              >
                <Trash2 className="size-4" aria-hidden />
              </Button>
            </div>
          ))}
          <Button
            size="sm"
            icon={<Plus className="size-4" aria-hidden />}
            onClick={() => setForm({ ...form, rules: [...rules, emptyRule()] })}
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
