import { AlertTriangle, Inbox, Loader2, X } from 'lucide-react'
import { Dialog as RadixDialog, Switch as RadixSwitch } from 'radix-ui'
import {
  type ButtonHTMLAttributes,
  createContext,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  useCallback,
  useContext,
  useId,
  useState,
} from 'react'

const cx = (...classes: (string | false | null | undefined)[]) => classes.filter(Boolean).join(' ')

// ------------------------------------------------------------------ Button
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
  loading?: boolean
  icon?: ReactNode
}

export function Button({
  variant = 'secondary',
  size = 'md',
  loading,
  icon,
  className,
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
        size === 'sm' ? 'h-9 px-3 text-sm' : 'h-11 px-4 text-sm',
        variant === 'primary' && 'bg-accent text-accent-contrast hover:opacity-90',
        variant === 'secondary' && 'border border-border bg-surface text-text hover:bg-surface-2',
        variant === 'ghost' && 'text-text hover:bg-surface-2',
        variant === 'danger' && 'bg-danger text-white hover:opacity-90',
        className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  )
}

// ------------------------------------------------------------------ Card, Badge, headings
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={cx('rounded-card border border-border bg-surface p-4', className)}>
      {children}
    </section>
  )
}

export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'
const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-muted',
  accent: 'bg-accent/15 text-accent',
  success: 'bg-success/15 text-success',
  warning: 'bg-warning/15 text-warning',
  danger: 'bg-danger/15 text-danger',
  info: 'bg-info/15 text-info',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        TONES[tone],
      )}
    >
      {children}
    </span>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

// ------------------------------------------------------------------ Form fields
export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: ReactNode
  error?: string
  children: (id: string, describedBy?: string) => ReactNode
}) {
  const id = useId()
  const describedBy = hint || error ? `${id}-desc` : undefined
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children(id, describedBy)}
      {(hint || error) && (
        <p id={describedBy} className={cx('text-xs', error ? 'text-danger' : 'text-muted')}>
          {error ?? hint}
        </p>
      )}
    </div>
  )
}

const control =
  'w-full rounded-lg border border-border bg-surface px-3 text-sm text-text placeholder:text-muted focus-visible:outline-2'

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(control, 'h-11', props.className)} />
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx(control, 'min-h-24 py-2', props.className)} />
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx(control, 'h-11 pr-8', className)} />
}

export function Switch({
  checked,
  onCheckedChange,
  label,
  description,
}: {
  checked: boolean
  onCheckedChange: (value: boolean) => void
  label: string
  description?: string
}) {
  const id = useId()
  return (
    <div className="flex items-start justify-between gap-4">
      <label htmlFor={id} className="flex flex-col">
        <span className="text-sm font-medium">{label}</span>
        {description && <span className="text-xs text-muted">{description}</span>}
      </label>
      <RadixSwitch.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        className="relative h-6 w-11 shrink-0 rounded-full bg-surface-2 border border-border transition-colors data-[state=checked]:bg-accent"
      >
        <RadixSwitch.Thumb className="block size-5 translate-x-0.5 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-[1.3rem]" />
      </RadixSwitch.Root>
    </div>
  )
}

// ------------------------------------------------------------------ States
export function Spinner({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 p-8 text-muted">
      <Loader2 className="size-5 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-card border border-dashed border-border p-8 text-center">
      <Inbox className="size-8 text-muted" aria-hidden />
      <p className="font-medium">{title}</p>
      <p className="max-w-md text-sm text-muted">{description}</p>
      {action}
    </div>
  )
}

export function ErrorState({
  title,
  description,
  onRetry,
  retryLabel,
}: {
  title: string
  description?: string
  onRetry?: () => void
  retryLabel?: string
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded-card border border-danger/40 bg-danger/5 p-6 text-center"
    >
      <AlertTriangle className="size-6 text-danger" aria-hidden />
      <p className="font-medium">{title}</p>
      {description && <p className="text-sm text-muted">{description}</p>}
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ Dialog
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  closeLabel,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: ReactNode
  closeLabel: string
}) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
        <RadixDialog.Content className="fixed inset-x-0 bottom-0 z-50 max-h-[90dvh] overflow-y-auto rounded-t-2xl border border-border bg-surface p-5 shadow-xl sm:inset-auto sm:top-1/2 sm:left-1/2 sm:w-full sm:max-w-lg sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <RadixDialog.Title className="text-lg font-semibold">{title}</RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-1 text-sm text-muted">
                  {description}
                </RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close asChild>
              <Button variant="ghost" size="sm" aria-label={closeLabel}>
                <X className="size-4" aria-hidden />
              </Button>
            </RadixDialog.Close>
          </div>
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}

// ------------------------------------------------------------------ Toasts
type Toast = { id: number; tone: Tone; message: string }
const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((message: string, tone: Tone = 'neutral') => {
    const id = Date.now() + Math.random()
    setToasts((all) => [...all, { id, tone, message }])
    setTimeout(() => setToasts((all) => all.filter((t) => t.id !== id)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto rounded-lg border border-border bg-surface px-4 py-2 text-sm shadow-lg"
          >
            <Badge tone={t.tone}>{t.tone === 'danger' ? '!' : '✓'}</Badge>{' '}
            <span className="ml-1">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
export { cx }
