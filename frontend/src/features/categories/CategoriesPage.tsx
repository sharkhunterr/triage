import { ArrowDown, ArrowUp, FolderOpen, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react'
import { useState } from 'react'
import {
  type Category,
  useApplyPreset,
  useCategories,
  useDeleteCategory,
  usePresets,
  useReorderCategories,
  useRootFolders,
} from '../../api/categories'
import {
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  useToast,
} from '../../design-system'
import { useT } from '../../i18n'
import { CategoryEditor } from './CategoryEditor'
import { CategoryDot } from './colors'

/** Ready-made categories: the starters on an empty page; beside existing categories, the add-ons
 * (Shows, Concerts…) whose categories are not there yet. */
export function PresetCard({ existing }: { existing?: string[] }) {
  const t = useT()
  const presets = usePresets()
  const apply = useApplyPreset()
  const toast = useToast()
  const have = new Set((existing ?? []).map((name) => name.toLowerCase()))
  const shown = (presets.data ?? []).filter((preset) =>
    existing === undefined
      ? !preset.addon
      : preset.addon && !preset.categories.every((c) => have.has(c.name.toLowerCase())),
  )
  if (!shown.length) return null
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {shown.map((preset) => (
        <Card key={preset.key} className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-accent" aria-hidden />
            <h2 className="font-semibold">{preset.name}</h2>
          </div>
          <p className="text-sm text-muted">{preset.description}</p>
          <ul className="flex flex-wrap gap-2">
            {preset.categories.map((c) => (
              <li key={c.name}>
                <Badge tone={c.is_fallback ? 'neutral' : 'accent'}>{c.name}</Badge>
              </li>
            ))}
          </ul>
          <Button
            variant="primary"
            loading={apply.isPending}
            onClick={() =>
              apply.mutate(preset.key, { onSuccess: () => toast(t('categories.presetApplied'), 'success') })
            }
          >
            {preset.addon ? t('categories.addPreset', { name: preset.name }) : t('categories.applyPreset')}
          </Button>
        </Card>
      ))}
    </div>
  )
}

export function CategoriesPage() {
  const t = useT()
  const categories = useCategories()
  const folders = useRootFolders()
  const remove = useDeleteCategory()
  const reorder = useReorderCategories()
  const [editing, setEditing] = useState<Category | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Category | null>(null)

  const move = (index: number, delta: number) => {
    const ids = (categories.data ?? []).map((c) => c.id)
    const [id] = ids.splice(index, 1)
    if (id === undefined) return
    ids.splice(index + delta, 0, id)
    reorder.mutate(ids)
  }

  return (
    <>
      <PageHeader
        title={t('categories.title')}
        description={t('categories.subtitle')}
        actions={
          <Button
            variant="primary"
            icon={<Plus className="size-4" aria-hidden />}
            onClick={() => setEditing('new')}
          >
            {t('categories.new')}
          </Button>
        }
      />
      {categories.isPending && <Spinner label={t('common.loading')} />}
      {categories.isError && (
        <ErrorState
          title={t('common.error')}
          onRetry={() => categories.refetch()}
          retryLabel={t('common.retry')}
        />
      )}
      {categories.data?.length === 0 && (
        <div className="flex flex-col gap-4">
          <EmptyState title={t('categories.emptyTitle')} description={t('categories.emptyDescription')} />
          <PresetCard />
        </div>
      )}
      <ul className="flex flex-col gap-3">
        {categories.data?.map((category, index, all) => (
          <li key={category.id}>
            <Card className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="flex items-center gap-2 font-semibold">
                    <CategoryDot id={category.id} />
                    {category.name}
                  </h2>
                  {category.is_fallback && <Badge>{t('categories.fallbackBadge')}</Badge>}
                  <Badge tone="info">{t('categories.ruleCount', { count: category.rules.length })}</Badge>
                </div>
                <p className="mt-1 flex items-center gap-1 text-sm">
                  <FolderOpen className="size-4 text-muted" aria-hidden />
                  {category.root_folder_path ? (
                    <code className="truncate">{category.root_folder_path}</code>
                  ) : (
                    <span className="text-warning">{t('categories.noLibraryWarning')}</span>
                  )}
                </p>
                {category.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-muted">{category.description}</p>
                )}
              </div>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t('categories.moveUp')}
                  disabled={index === 0}
                  onClick={() => move(index, -1)}
                >
                  <ArrowUp className="size-4" aria-hidden />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t('categories.moveDown')}
                  disabled={index === all.length - 1}
                  onClick={() => move(index, 1)}
                >
                  <ArrowDown className="size-4" aria-hidden />
                </Button>
                <Button
                  size="sm"
                  icon={<Pencil className="size-4" aria-hidden />}
                  onClick={() => setEditing(category)}
                >
                  {t('common.edit')}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t('common.delete')}
                  disabled={all.length <= 1}
                  onClick={() => setDeleting(category)}
                >
                  <Trash2 className="size-4" aria-hidden />
                </Button>
              </div>
            </Card>
          </li>
        ))}
      </ul>
      {categories.data?.length ? (
        <section aria-labelledby="addons" className="mt-8 flex flex-col gap-3">
          <h2 id="addons" className="font-semibold">
            {t('categories.addons')}
          </h2>
          <PresetCard existing={categories.data.map((c) => c.name)} />
        </section>
      ) : null}

      {editing && (
        <CategoryEditor
          open
          onOpenChange={(open) => !open && setEditing(null)}
          category={editing === 'new' ? undefined : editing}
          folders={folders.data}
        />
      )}
      <Dialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={t('categories.deleteTitle', { name: deleting?.name ?? '' })}
        description={t('categories.deleteDescription')}
        closeLabel={t('common.close')}
      >
        <div className="flex justify-end gap-2">
          <Button onClick={() => setDeleting(null)}>{t('common.cancel')}</Button>
          <Button
            variant="danger"
            loading={remove.isPending}
            onClick={() => deleting && remove.mutate(deleting.id, { onSuccess: () => setDeleting(null) })}
          >
            {t('common.delete')}
          </Button>
        </div>
      </Dialog>
    </>
  )
}
