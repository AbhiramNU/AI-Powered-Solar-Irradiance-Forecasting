import { useMemo, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip, { type TooltipRow } from '../components/ChartTooltip'
import { SiteDateFields } from '../components/SiteDatePicker'
import { useSiteDate } from '../lib/useSiteDate'
import { Banner, Card, ConfidencePill, ErrorState, Loading, PageHeader, Segmented, Stat, Swatch } from '../components/ui'
import { cloudiestDate, fmt, formatDate, hourLabel, sum, useSites } from '../lib/data'

type SeriesKey = 'band' | 'p50' | 'actual' | 'nwp' | 'persistence' | 'clearsky'

const SERIES: (TooltipRow & { key: SeriesKey })[] = [
  { key: 'p50', label: 'P50 forecast', color: 'var(--series-model)', kind: 'line', unit: 'W/m²' },
  { key: 'band', label: 'P10–P90 range', color: 'var(--series-band)', kind: 'box', unit: 'W/m²' },
  { key: 'actual', label: 'Actual GHI', color: 'var(--series-actual)', kind: 'dot', unit: 'W/m²' },
  { key: 'nwp', label: 'Raw weather forecast', color: 'var(--series-nwp)', kind: 'dashed', unit: 'W/m²' },
  { key: 'persistence', label: 'Persistence', color: 'var(--series-persistence)', kind: 'dashed', unit: 'W/m²' },
  { key: 'clearsky', label: 'Clear-sky', color: '#94a3b8', kind: 'dotted', unit: 'W/m²' },
]

export default function ForecastView() {
  const sites = useSites()
  const sel = useSiteDate(sites.data)
  const [visible, setVisible] = useState<Record<SeriesKey, boolean>>({
    band: true, p50: true, actual: true, nwp: true, persistence: false, clearsky: false,
  })
  const [view, setView] = useState<'chart' | 'table'>('chart')
  const [cloudyNote, setCloudyNote] = useState(false)

  const rows = useMemo(() => {
    if (!sel.day || !sel.forecasts.data) return []
    const d = sel.day
    return sel.forecasts.data.hours.map((h, i) => ({
      hour: h,
      band: d.p10[i] != null && d.p90[i] != null ? [d.p10[i], d.p90[i]] : null,
      p10: d.p10[i],
      p50: d.p50[i],
      p90: d.p90[i],
      actual: d.actual[i],
      nwp: d.nwp[i],
      persistence: d.persistence[i],
      clearsky: d.clearsky[i],
    }))
  }, [sel.day, sel.forecasts.data])

  if (sites.error) return <ErrorState message={sites.error} />
  if (!sites.data) return <Loading />

  const d = sel.day
  const totals = d && {
    p10: sum(d.p10) / 1000,
    p50: sum(d.p50) / 1000,
    p90: sum(d.p90) / 1000,
    actual: sum(d.actual) / 1000,
  }
  const errorPct = totals && totals.actual > 0 ? (Math.abs(totals.p50 - totals.actual) / totals.actual) * 100 : null
  const inBand = totals && totals.actual >= totals.p10 && totals.actual <= totals.p90

  const exploreCloudy = () => {
    if (!sel.forecasts.data) return
    const c = cloudiestDate(sel.forecasts.data)
    if (c) {
      sel.setDate(c)
      setCloudyNote(true)
    }
  }

  return (
    <>
      <PageHeader eyebrow="01 · Forecast View" title="Tomorrow's solar forecast" subtitle="Hourly GHI predictions with P10–P90 uncertainty, compared against actuals and the raw weather model." />
      <Banner>
        <Swatch color="var(--green-700)" kind="dot" /> Test period (2026) — model evaluation on unseen data, daytime hours 06:00–19:00 IST.
      </Banner>

      <div className="controls">
        <SiteDateFields
          sites={sites.data}
          siteId={sel.siteId}
          date={sel.date}
          dates={sel.dates}
          setSite={(s) => { setCloudyNote(false); sel.setSite(s) }}
          setDate={(x) => { setCloudyNote(false); sel.setDate(x) }}
        />
        <button className="btn ghost" type="button" onClick={exploreCloudy} disabled={!sel.forecasts.data}>
          ☁ Explore a cloudy day
        </button>
      </div>
      {cloudyNote && (
        <Banner tone="info">☁ Showing the cloudiest test day for {sel.site?.name}. Cloud-driven variability makes solar forecasting harder.</Banner>
      )}

      {sel.forecasts.error && <ErrorState message={sel.forecasts.error} />}
      {sel.forecasts.loading && <Loading />}

      {d && totals && (
        <div className="stack">
          <div className="grid cols-5">
            <Stat accent label="P50 forecast (expected)" value={fmt(totals.p50, 2)} unit="kWh/m²" note="Daily irradiation" />
            <Stat label="P10 (conservative)" value={fmt(totals.p10, 2)} unit="kWh/m²" />
            <Stat label="P90 (high generation)" value={fmt(totals.p90, 2)} unit="kWh/m²" />
            <Stat
              label="Actual"
              value={fmt(totals.actual, 2)}
              unit="kWh/m²"
              note={
                <>
                  {fmt(errorPct, 1)}% daily error · {inBand ? '✓ inside' : '✕ outside'} P10–P90
                </>
              }
            />
            <Stat label="Forecast confidence" value={<ConfidencePill level={d.confidence} />} note="From expected weather variability" />
          </div>

          <Card
            title="Hourly forecast"
            subtitle={`${sel.site?.name} · ${sel.date ? formatDate(sel.date) : ''} · shaded area is the model's P10–P90 prediction range`}
            action={
              <Segmented
                label="View"
                value={view}
                onChange={setView}
                options={[
                  { value: 'chart', label: 'Chart' },
                  { value: 'table', label: 'Table' },
                ]}
              />
            }
          >
            <div className="legend" style={{ marginBottom: 12 }}>
              {SERIES.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  className="legend-item legend-toggle"
                  aria-pressed={visible[s.key]}
                  onClick={() => setVisible((v) => ({ ...v, [s.key]: !v[s.key] }))}
                  title={visible[s.key] ? 'Click to hide' : 'Click to show'}
                >
                  <Swatch color={s.color} kind={s.kind} />
                  {s.label}
                </button>
              ))}
            </div>
            {view === 'chart' ? (
              <div style={{ height: 380 }}>
                <ResponsiveContainer>
                  <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                    <CartesianGrid stroke="#eef2ef" vertical={false} />
                    <XAxis dataKey="hour" tickFormatter={hourLabel} tick={{ fontSize: 12, fill: '#6b7f73' }} axisLine={{ stroke: '#cfdcd3' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 12, fill: '#6b7f73' }} axisLine={false} tickLine={false} width={52}
                      label={{ value: 'GHI (W/m²)', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 12, fill: '#6b7f73' } }} />
                    <Tooltip
                      cursor={{ stroke: '#86efac', strokeWidth: 1 }}
                      content={<ChartTooltip rows={SERIES.filter((s) => visible[s.key])} title={(h) => `${hourLabel(Number(h))} IST`} />}
                    />
                    {visible.band && <Area dataKey="band" stroke="none" fill="var(--series-band)" fillOpacity={0.7} isAnimationActive={false} />}
                    {visible.clearsky && <Line dataKey="clearsky" stroke="#94a3b8" strokeWidth={2} strokeDasharray="2 4" dot={false} isAnimationActive={false} />}
                    {visible.persistence && <Line dataKey="persistence" stroke="var(--series-persistence)" strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />}
                    {visible.nwp && <Line dataKey="nwp" stroke="var(--series-nwp)" strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />}
                    {visible.p50 && <Line dataKey="p50" stroke="var(--series-model)" strokeWidth={3} dot={false} activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />}
                    {visible.actual && (
                      <Line dataKey="actual" stroke="var(--series-actual)" strokeWidth={1} strokeDasharray="2 3"
                        dot={{ r: 4, fill: 'var(--series-actual)', stroke: '#fff', strokeWidth: 2 }} activeDot={{ r: 5 }} isAnimationActive={false} />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Hour (IST)</th>
                      <th className="r">P10</th>
                      <th className="r">P50</th>
                      <th className="r">P90</th>
                      <th className="r">Actual</th>
                      <th className="r">Raw NWP</th>
                      <th className="r">Persistence</th>
                      <th className="r">Clear-sky</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.hour}>
                        <td>{hourLabel(r.hour)}</td>
                        <td className="r">{fmt(r.p10, 0)}</td>
                        <td className="r"><b>{fmt(r.p50, 0)}</b></td>
                        <td className="r">{fmt(r.p90, 0)}</td>
                        <td className="r">{fmt(r.actual, 0)}</td>
                        <td className="r">{fmt(r.nwp, 0)}</td>
                        <td className="r">{fmt(r.persistence, 0)}</td>
                        <td className="r">{fmt(r.clearsky, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="card-sub" style={{ marginTop: 8 }}>All values in W/m².</p>
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  )
}
