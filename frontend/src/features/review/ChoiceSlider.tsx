import { Ban, Bot, Check, ChevronLeft, ChevronRight, MapPin } from 'lucide-react'
import { type KeyboardEvent, type PointerEvent, type ReactNode, useRef, useState } from 'react'
import { useCategories } from '../../api/categories'
import type { DecisionSummary } from '../../api/decisions'
import { Button, cx } from '../../design-system'
import { useT } from '../../i18n'
import { categoryColor, tint } from '../categories/colors'
import { useDecisionAction } from '../decisions/DecisionActions'
import { choiceConfidence } from '../decisions/parts'

type Stop = { id: number | null; key: string | null; name: string }

const trim = (path: string) => path.replace(/\/+$/, '')

/** Where a waiting movie goes, as a line of the libraries: the one it is in (a pin), the one chosen
 * (the thumb, with its confidence), the way between them in their colors. Slide or tap, then confirm;
 * back on its own library, the movie is left there. */
export function ChoiceSlider({ decision, aside }: { decision: DecisionSummary; aside?: ReactNode }) {
  const t = useT()
  const categories = useCategories()
  const action = useDecisionAction()
  const track = useRef<HTMLDivElement>(null)

  const libraries: Stop[] = (categories.data ?? [])
    .filter((c) => c.root_folder_path)
    .map((c) => ({ id: c.id, key: c.key, name: c.name }))
  const here = decision.from_root_folder ? trim(decision.from_root_folder) : null
  const hereCategory = (categories.data ?? []).find(
    (c) => c.root_folder_path && here !== null && trim(c.root_folder_path) === here,
  )
  // a folder that is no category's library (the intake folder): its own stop, first
  const stops: Stop[] = hereCategory
    ? libraries
    : [{ id: null, key: null, name: here?.split('/').pop() || '—' }, ...libraries]
  const origin = hereCategory ? stops.findIndex((s) => s.id === hereCategory.id) : 0
  const proposed = decision.target_category ?? decision.top_category
  const suggested = stops.findIndex((s) => s.id === proposed?.id)
  const [picked, setPicked] = useState<number | null>(null)
  const index = picked ?? (suggested >= 0 ? suggested : origin)
  const chosen = stops[index]
  if (!categories.data || !chosen) return null

  const last = Math.max(1, stops.length - 1)
  const at = (i: number) => (stops.length === 1 ? 50 : (i / last) * 100)
  const stays = index === origin
  const excluded = chosen.key !== null && decision.excluded.includes(chosen.key)
  const ai = decision.ai
  const aiPicked = Boolean(ai && !ai.error && chosen.key && ai.category === chosen.key)

  const nearest = (clientX: number) => {
    const box = track.current?.getBoundingClientRect()
    if (!box || box.width === 0) return index
    const ratio = Math.min(1, Math.max(0, (clientX - box.left) / box.width))
    return Math.round(ratio * last)
  }
  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    setPicked(nearest(event.clientX))
  }
  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) setPicked(nearest(event.clientX))
  }
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const moves: Record<string, number> = {
      ArrowRight: index + 1,
      ArrowUp: index + 1,
      ArrowLeft: index - 1,
      ArrowDown: index - 1,
      Home: 0,
      End: stops.length - 1,
    }
    if (!(event.key in moves)) return
    event.preventDefault()
    setPicked(Math.min(stops.length - 1, Math.max(0, moves[event.key] ?? index)))
  }
  const confirm = () => {
    if (stays) {
      if (decision.status === 'proposed') action.mutate({ id: decision.id, action: 'dismiss' })
      else action.mutate({ id: decision.id, action: 'apply', body: { target: 'intake' } })
    } else if (chosen.id !== null) {
      action.mutate({ id: decision.id, action: 'apply', body: { category_id: chosen.id } })
    }
  }

  const from = categoryColor(stops[origin]?.id)
  const to = categoryColor(chosen.id)
  const left = Math.min(at(origin), at(index))
  const width = Math.abs(at(index) - at(origin))
  const forward = index >= origin
  // a text over or under a stop, centred on it; at the ends, kept inside the row's padding
  const anchor = (i: number) => ({
    left: `${at(i)}%`,
    transform:
      stops.length > 1 && i === 0
        ? 'translateX(max(-50%, -1.75rem))'
        : stops.length > 1 && i === last
          ? 'translateX(min(-50%, calc(1.75rem - 100%)))'
          : 'translateX(-50%)',
  })
  const percent = (stop: Stop) =>
    stop.key ? `${Math.round(choiceConfidence(decision, stop.key) * 100)} %` : null

  return (
    <div className="flex w-full flex-col gap-2">
      <div className="px-7">
        {/* how sure Triage is of each library; the chosen one in a badge */}
        <div className="relative mb-1 h-5" aria-hidden>
          {stops.map((stop, i) => {
            const isAi = Boolean(ai && !ai.error && stop.key && ai.category === stop.key)
            const out = stop.key !== null && decision.excluded.includes(stop.key)
            if (i === index)
              return (
                <span
                  key={stop.id ?? 'here'}
                  className="absolute top-0 inline-flex h-5 items-center gap-1 rounded-full px-2 text-[11px] font-semibold whitespace-nowrap text-surface tabular-nums shadow-sm transition-[left] duration-200"
                  style={{ ...anchor(i), background: to }}
                >
                  {stays ? <MapPin className="size-3" /> : null}
                  {excluded ? t('choice.excluded') : percent(stop)}
                  {aiPicked && ai && !stays ? (
                    <>
                      <Bot className="size-3" />
                      {Math.round(Number(ai.confidence) * 100)} %
                    </>
                  ) : null}
                </span>
              )
            const text = out ? t('choice.excluded') : percent(stop)
            if (!text) return null
            return (
              <span
                key={stop.id ?? 'here'}
                className="absolute top-0 inline-flex h-5 items-center gap-0.5 text-[11px] font-medium whitespace-nowrap tabular-nums"
                style={{ ...anchor(i), color: out ? undefined : categoryColor(stop.id) }}
              >
                {out ? <Ban className="size-3 text-muted" /> : isAi ? <Bot className="size-3" /> : null}
                <span className={out ? 'text-muted' : undefined}>{text}</span>
              </span>
            )
          })}
        </div>
        <div
          ref={track}
          role="slider"
          tabIndex={0}
          aria-label={t('choice.slider')}
          aria-valuemin={0}
          aria-valuemax={stops.length - 1}
          aria-valuenow={index}
          aria-valuetext={stays ? t('choice.stayIn', { name: chosen.name }) : chosen.name}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onKeyDown={onKeyDown}
          className="relative h-6 cursor-pointer touch-none rounded-full outline-offset-8 select-none focus-visible:outline-2"
        >
          <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-surface-2" />
          {/* the way from where it is to where it goes, a light running along it toward the thumb */}
          <div
            className="absolute top-1/2 h-1.5 -translate-y-1/2 overflow-hidden rounded-full transition-all duration-200"
            style={{
              left: `${left}%`,
              width: `${width}%`,
              background: `linear-gradient(to ${forward ? 'right' : 'left'}, ${from}, ${to})`,
            }}
          >
            {stays ? null : (
              <span
                className={cx(
                  'absolute inset-y-0 left-0 w-2/5 motion-reduce:hidden',
                  forward ? 'flow-forward' : 'flow-backward',
                )}
                style={{
                  background:
                    'linear-gradient(90deg, transparent, color-mix(in srgb, var(--surface) 75%, transparent), transparent)',
                }}
              />
            )}
          </div>
          {stops.map((stop, i) => (
            <span
              key={stop.id ?? 'here'}
              aria-hidden
              className={cx(
                'absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full',
                i === origin ? 'grid size-5 place-items-center border-2 bg-surface' : 'size-2.5',
                stop.key !== null && decision.excluded.includes(stop.key) && 'opacity-40',
              )}
              style={
                i === origin
                  ? { left: `${at(i)}%`, borderColor: categoryColor(stop.id) }
                  : { left: `${at(i)}%`, background: categoryColor(stop.id) }
              }
            >
              {i === origin ? <MapPin className="size-3" style={{ color: categoryColor(stop.id) }} /> : null}
            </span>
          ))}
          {/* the thumb, pointing the way (a pin when the movie stays) */}
          <span
            aria-hidden
            className="absolute top-1/2 grid size-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-[3px] border-surface text-surface shadow-md ring-1 ring-border transition-[left] duration-200"
            style={{ left: `${at(index)}%`, background: to }}
          >
            {stays ? (
              <MapPin className="size-3.5" strokeWidth={2.5} />
            ) : forward ? (
              <ChevronRight className="size-4" strokeWidth={3} />
            ) : (
              <ChevronLeft className="size-4" strokeWidth={3} />
            )}
          </span>
        </div>
        {/* the libraries' names, under their stops */}
        <div className="relative mt-1.5 h-4" aria-hidden>
          {stops.map((stop, i) => (
            <button
              key={stop.id ?? 'here'}
              type="button"
              tabIndex={-1}
              onClick={() => setPicked(i)}
              className={cx(
                'absolute top-0 inline-flex max-w-[6.5rem] items-center gap-0.5 truncate text-[11px] leading-4',
                i === index ? 'font-semibold' : 'text-muted',
              )}
              style={{ ...anchor(i), color: i === index ? to : undefined }}
            >
              {i === origin ? <MapPin className="size-2.5 shrink-0" /> : null}
              <span className="truncate">{stop.name}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">{aside}</div>
        <Button
          size="sm"
          variant="ghost"
          className={cx(
            'shrink-0 border whitespace-nowrap',
            stays ? 'border-border' : 'cat-fill hover:opacity-90',
          )}
          style={stays ? undefined : tint(chosen.id)}
          icon={stays ? <MapPin className="size-4" aria-hidden /> : <Check className="size-4" aria-hidden />}
          loading={action.isPending}
          onClick={confirm}
        >
          {stays ? t('check.leave') : t('choice.send', { name: chosen.name })}
        </Button>
      </div>
    </div>
  )
}
