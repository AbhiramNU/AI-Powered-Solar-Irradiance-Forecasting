import { useMemo, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip, { type TooltipRow } from '../components/ChartTooltip'
import { SiteDateFields } from '../components/SiteDatePicker'
import { useSiteDate } from '../lib/useSiteDate'
import { Card, ErrorState, Loading, PageHeader, Stat, Swatch } from '../components/ui'
import { fmt, formatDate, hourLabel, useSites } from '../lib/data'

const ROWS: TooltipRow[] = [
  { key: 'p50', label: 'P50 power', color: 'var(--series-model)', kind: 'line', unit: 'kW', digits: 1 },
  { key: 'band', label: 'P10–P90 range', color: 'var(--series-band)', kind: 'box', unit: 'kW', digits: 1 },
  { key: 'actual', label: 'From actual GHI', color: 'var(--series-actual)', kind: 'dot', unit: 'kW', digits: 1 },
]

export default function EnergyEstimate() {
  const sites = useSites()
  const sel = useSiteDate(sites.data)
  const [capacity, setCapacity] = useState(100)
  const [pr, setPr] = useState(75)

  // Simplified PV model: P(kW) = GHI(W/m²) / 1000 × capacity(kWp) × performance ratio
  const factor = (capacity * (pr / 100)) / 1000

  const rows = useMemo(() => {
    if (!sel.day || !sel.forecasts.data) return []
    const d = sel.day
    const k = (v: number | null) => (v == null ? null : v * factor)
    return sel.forecasts.data.hours.map((h, i) => ({
      hour: h,
      p10: k(d.p10[i]),
      p50: k(d.p50[i]),
      p90: k(d.p90[i]),
      band: d.p10[i] != null && d.p90[i] != null ? [k(d.p10[i]), k(d.p90[i])] : null,
      actual: k(d.actual[i]),
    }))
  }, [sel.day, sel.forecasts.data, factor])

  if (sites.error) return <ErrorState message={sites.error} />
  if (!sites.data) return <Loading />

  const d = sel.day
  // Daily energy (kWh) = daily irradiation (kWh/m²) × capacity (kWp) × PR, from calibrated daily totals.
  const daily = d?.daily
  const e = daily && {
    p10: daily.p10 * capacity * (pr / 100),
    p50: daily.p50 * capacity * (pr / 100),
    p90: daily.p90 * capacity * (pr / 100),
    actual: daily.actual == null ? null : daily.actual * capacity * (pr / 100),
  }
  const peak = rows.reduce((m, r) => (r.p50 != null && r.p50 > m.v ? { v: r.p50, h: r.hour } : m), { v: 0, h: 0 })

  return (
    <>
      <PageHeader eyebrow="04 · Energy Estimate" title="Turn sunlight into an energy estimate" subtitle="Convert hourly irradiance forecasts into expected generation for a plant of your size." />

      <div className="controls">
        <SiteDateFields sites={sites.data} siteId={sel.siteId} date={sel.date} dates={sel.dates} setSite={sel.setSite} setDate={sel.setDate} />
        <div className="field" style={{ maxWidth: 180 }}>
          <label htmlFor="cap">System capacity (kWp)</label>
          <input
            id="cap"
            type="number"
            min={1}
            step={10}
            value={capacity}
            onChange={(ev) => setCapacity(Math.max(1, Number(ev.target.value) || 1))}
          />
        </div>
        <div className="field" style={{ minWidth: 220 }}>
          <label htmlFor="pr">Performance ratio: {pr}%</label>
          <input id="pr" type="range" min={60} max={90} value={pr} onChange={(ev) => setPr(Number(ev.target.value))} style={{ height: 40 }} />
        </div>
      </div>

      {sel.forecasts.error && <ErrorState message={sel.forecasts.error} />}
      {sel.forecasts.loading && <Loading />}

      {e && (
        <div className="stack">
          <div className="grid cols-4">
            <Stat accent label="P50 energy (expected)" value={fmt(e.p50, 1)} unit="kWh" note={`Peak ${fmt(peak.v, 1)} kW at ${hourLabel(peak.h)}`} />
            <Stat label="P10 energy (conservative)" value={fmt(e.p10, 1)} unit="kWh" note="Plan commitments against this" />
            <Stat label="P90 energy (high)" value={fmt(e.p90, 1)} unit="kWh" />
            <Stat label="Energy from actual GHI" value={fmt(e.actual, 1)} unit="kWh" note={e.actual == null ? 'Not available' : `${fmt(e.actual / capacity, 2)} kWh/kWp specific yield`} />
          </div>

          <Card title="Hourly power generation" subtitle={`${sel.site?.name} · ${sel.date ? formatDate(sel.date) : ''} · ${capacity.toLocaleString('en-IN')} kWp at ${pr}% PR`}>
            <div className="legend" style={{ marginBottom: 12 }}>
              {ROWS.map((r) => (
                <span key={r.key} className="legend-item">
                  <Swatch color={r.color} kind={r.kind} />
                  {r.label}
                </span>
              ))}
            </div>
            <div style={{ height: 360 }}>
              <ResponsiveContainer>
                <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                  <CartesianGrid stroke="#f4ece6" vertical={false} />
                  <XAxis dataKey="hour" tickFormatter={hourLabel} tick={{ fontSize: 12, fill: '#80695c' }} axisLine={{ stroke: '#e3d4c8' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#80695c' }} axisLine={false} tickLine={false} width={52}
                    label={{ value: 'Power (kW)', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 12, fill: '#80695c' } }} />
                  <Tooltip cursor={{ stroke: '#fdba74' }} content={<ChartTooltip rows={ROWS} title={(h) => `${hourLabel(Number(h))} IST`} />} />
                  <Area dataKey="band" stroke="none" fill="var(--series-band)" fillOpacity={0.7} isAnimationActive={false} />
                  <Line dataKey="p50" stroke="var(--series-model)" strokeWidth={3} dot={false} activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
                  <Line dataKey="actual" stroke="var(--series-actual)" strokeWidth={1} strokeDasharray="2 3"
                    dot={{ r: 3.5, fill: 'var(--series-actual)', stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="Assumptions">
            <ul className="prose" style={{ margin: 0, paddingLeft: 20 }}>
              <li><strong>Formula:</strong> Power (kW) = GHI (W/m²) ÷ 1000 × capacity (kWp) × performance ratio. Daily energy = daily irradiation (kWh/m²) × capacity × performance ratio.</li>
              <li><strong>Horizontal irradiance:</strong> uses GHI with no plane-of-array transposition, so tilted arrays will differ.</li>
              <li><strong>Daily range</strong> comes from calibrated daily P10/P90, not from adding up hourly P10/P90, which would overstate it.</li>
              <li><strong>Performance ratio</strong> ({pr}%) bundles typical losses: temperature, soiling, inverter, wiring.</li>
              <li>This is a simplified estimate. A production version would use <code>pvlib</code> transposition and temperature models.</li>
            </ul>
          </Card>
        </div>
      )}
    </>
  )
}
