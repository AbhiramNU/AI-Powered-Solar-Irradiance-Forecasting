import type { ReactNode } from 'react'
import type { Confidence } from '../lib/data'

export function PageHeader({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle?: string }) {
  return (
    <header className="page-head">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      {subtitle && <p className="page-sub">{subtitle}</p>}
    </header>
  )
}

export function Card({
  title,
  subtitle,
  action,
  children,
  className = '',
}: {
  title?: string
  subtitle?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function Stat({
  label,
  value,
  unit,
  note,
  accent,
}: {
  label: string
  value: ReactNode
  unit?: string
  note?: ReactNode
  accent?: boolean
}) {
  return (
    <div className={`card stat ${accent ? 'accent' : ''}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">
        {value}
        {unit && <span className="stat-unit">{unit}</span>}
      </span>
      {note && <span className="stat-note">{note}</span>}
    </div>
  )
}

const confClass: Record<string, string> = { High: 'good', Medium: 'warn', Low: 'bad' }
const confIcon: Record<string, string> = { High: '●●●', Medium: '●●○', Low: '●○○' }

export function ConfidencePill({ level }: { level: Confidence }) {
  if (!level) return <span className="pill neutral">Unknown</span>
  return (
    <span className={`pill ${confClass[level]}`}>
      <span aria-hidden style={{ letterSpacing: 1, fontSize: '0.65rem' }}>
        {confIcon[level]}
      </span>
      {level}
    </span>
  )
}

export function Banner({ children, tone = 'good' }: { children: ReactNode; tone?: 'good' | 'info' }) {
  return (
    <div className={`banner ${tone === 'info' ? 'info' : ''}`} role="note">
      {children}
    </div>
  )
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Loading() {
  return <div className="empty">Loading data…</div>
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="card empty" role="alert">
      Data isn't available yet. <br />
      <small>{message}</small>
    </div>
  )
}

export type SwatchKind = 'line' | 'dashed' | 'dotted' | 'box' | 'dot'

export function Swatch({ color, kind }: { color: string; kind: SwatchKind }) {
  if (kind === 'box') return <span className="swatch-box" style={{ background: color }} />
  if (kind === 'dot') return <span className="swatch-dot" style={{ background: color }} />
  const cls = kind === 'line' ? '' : kind
  return <span className={`swatch-line ${cls}`} style={{ borderTopColor: color }} />
}
