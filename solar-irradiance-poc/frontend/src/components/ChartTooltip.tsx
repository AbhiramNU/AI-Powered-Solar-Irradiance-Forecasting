import type { ReactNode } from 'react'
import { fmt } from '../lib/data'
import { Swatch, type SwatchKind } from './ui'

export interface TooltipRow {
  key: string
  label: string
  color: string
  kind: SwatchKind
  unit?: string
  digits?: number
}

interface Props {
  active?: boolean
  label?: string | number
  payload?: { payload: Record<string, unknown> }[]
  rows: TooltipRow[]
  title: (label: string | number) => ReactNode
}

/** Shared hover tooltip: reads values straight off the hovered datum so ranges render as "low – high". */
export default function ChartTooltip({ active, label, payload, rows, title }: Props) {
  if (!active || !payload?.length || label == null) return null
  const datum = payload[0].payload
  return (
    <div className="tt">
      <div className="tt-title">{title(label)}</div>
      {rows.map((r) => {
        const v = datum[r.key]
        if (v === undefined) return null
        const text = Array.isArray(v)
          ? `${fmt(v[0] as number, r.digits ?? 0)} – ${fmt(v[1] as number, r.digits ?? 0)}`
          : fmt(v as number | null, r.digits ?? 0)
        return (
          <div className="tt-row" key={r.key}>
            <span>
              <Swatch color={r.color} kind={r.kind} />
              {r.label}
            </span>
            <b>
              {text}
              {r.unit && text !== '—' ? ` ${r.unit}` : ''}
            </b>
          </div>
        )
      })}
    </div>
  )
}
