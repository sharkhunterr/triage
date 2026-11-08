import type { CSSProperties } from 'react'

const PALETTE = 6

/** A category's color, stable across pages: it follows the category id. */
export function categoryColor(id: number | undefined | null): string {
  if (id == null) return 'var(--muted)'
  return `var(--cat-${((((id - 1) % PALETTE) + PALETTE) % PALETTE) + 1})`
}

/** Style for an element tinted with a category's color (pair with the `cat-tint` class). */
export const tint = (id: number | undefined | null) => ({ '--c': categoryColor(id) }) as CSSProperties

export function CategoryDot({
  id,
  className = 'size-2.5',
}: {
  id: number | undefined | null
  className?: string
}) {
  return (
    <span
      aria-hidden
      className={`inline-block shrink-0 rounded-full ${className}`}
      style={{ background: categoryColor(id) }}
    />
  )
}
