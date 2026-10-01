import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip, { type TooltipRow } from '../components/ChartTooltip'
import { Card, ErrorState, Loading, PageHeader, Stat, Swatch } from '../components/ui'
import { fmt, formatMonth, useMetrics, useMonthly, type ModelMetrics } from '../lib/data'

const MODELS = [
  { key: 'ml_model_p50', label: 'SuryaCast ML (P50)', color: 'var(--series-model)' },
  { key: 'raw_nwp', label: 'Raw weather forecast (NWP)', color: 'var(--series-nwp)' },
  { key: 'persistence', label: 'Persistence baseline', color: 'var(--series-persistence)' },
] as const

const TARGET = [75, 85]
const axis = { tick: { fontSize: 12, fill: '#6b7f73' }, tickLine: false }

export default function AccuracyScorecard() {
  const metrics = useMetrics()
  const monthly = useMonthly()

  const monthlyRows = useMemo(
    () =>
      monthly.data?.months.map((m, i) => ({
        month: m,
        ml_model_p50: monthly.data!.overall.ml_model_p50[i],
        raw_nwp: monthly.data!.overall.raw_nwp[i],
        persistence: monthly.data!.overall.persistence[i],
      })) ?? [],
    [monthly.data],
  )

  if (metrics.error) return <ErrorState message={metrics.error} />
  if (!metrics.data) return <Loading />

  const o = metrics.data.overall
  const ml = o.ml_model_p50
  const coverage = o.p10_p90_coverage
  const coverageOk = coverage >= TARGET[0] && coverage <= TARGET[1]
  const skillVsPers = (1 - ml.mae / o.persistence.mae) * 100

  const barRows = MODELS.map((m) => ({ model: m.label, color: m.color, ...(o[m.key] as ModelMetrics) }))
  const conf = metrics.data.by_confidence
  const confRows = conf
    ? (['High', 'Medium', 'Low'] as const).filter((k) => conf[k]).map((k) => ({ level: k, ...conf[k] }))
    : []
  const totalCount = confRows.reduce((a, r) => a + r.count, 0)

  const lineRows: TooltipRow[] = MODELS.map((m) => ({ key: m.key, label: m.label, color: m.color, kind: 'line', unit: 'W/m²', digits: 1 }))

  return (
    <>
      <PageHeader eyebrow="02 · Accuracy Scorecard" title="How accurate is SuryaCast?" subtitle="Model performance across the unseen 2026 test period (January – September, all five sites)." />

      <div className="stack">
        <Card>
          <p style={{ fontSize: '1.05rem', color: 'var(--ink-2)' }}>
            Across five Indian sites in 2026, the LightGBM model achieved a mean absolute error of{' '}
            <strong style={{ color: 'var(--green-800)' }}>{fmt(ml.mae, 2)} W/m²</strong>, outperforming both the raw weather
            forecast (<strong>{fmt(o.raw_nwp.mae, 2)} W/m²</strong>) and the persistence baseline (
            <strong>{fmt(o.persistence.mae, 2)} W/m²</strong>).
          </p>
        </Card>

        <div className="grid cols-4">
          <Stat accent label="ML model P50 MAE" value={fmt(ml.mae, 2)} unit="W/m²" note={`RMSE ${fmt(ml.rmse, 2)} W/m²`} />
          <Stat label="Skill vs raw NWP" value={`+${fmt(ml.skill, 1)}`} unit="%" note="MAE reduction vs weather model" />
          <Stat label="Skill vs persistence" value={`+${fmt(skillVsPers, 1)}`} unit="%" note="MAE reduction vs yesterday-repeats" />
          <Stat
            label="P10–P90 coverage"
            value={fmt(coverage, 1)}
            unit="%"
            note={
              <span className={`pill ${coverageOk ? 'good' : 'warn'}`} style={{ marginTop: 2 }}>
                {coverageOk ? '✓ Within' : '! Outside'} 75–85% target
              </span>
            }
          />
        </div>

        <Card title="Model vs baselines" subtitle="2026 test set, all hours. Lower error is better.">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th className="r">MAE (W/m²)</th>
                  <th className="r">RMSE (W/m²)</th>
                  <th className="r">nRMSE (%)</th>
                  <th className="r">Bias (W/m²)</th>
                  <th className="r">Skill</th>
                </tr>
              </thead>
              <tbody>
                {barRows.map((r, i) => (
                  <tr key={r.model} className={i === 0 ? 'highlight' : ''}>
                    <td>
                      <span className="legend-item">
                        <Swatch color={r.color} kind="box" />
                        {r.model}
                      </span>
                    </td>
                    <td className="r">{fmt(r.mae, 2)}</td>
                    <td className="r">{fmt(r.rmse, 2)}</td>
                    <td className="r">{fmt(r.nrmse, 2)}</td>
                    <td className="r">{r.bias > 0 ? '+' : ''}{fmt(r.bias, 2)}</td>
                    <td className="r">
                      {i === 0 ? `+${fmt(r.skill, 1)}% vs NWP` : i === 1 ? `+${fmt(r.skill, 1)}% vs persistence` : 'Reference'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid cols-2">
          <Card title="MAE by model" subtitle="Mean absolute error, W/m²">
            <ErrorBars rows={barRows} metric="mae" />
          </Card>
          <Card title="RMSE by model" subtitle="Root mean squared error, W/m² — penalises large misses">
            <ErrorBars rows={barRows} metric="rmse" />
          </Card>
        </div>

        <Card
          title="Monthly performance trend"
          subtitle="Monthly MAE (W/m²) on the 2026 test period. Errors rise for every model during the monsoon (Jun–Sep), when cloud cover is hardest to predict."
        >
          {monthly.error && <p className="card-sub">Monthly breakdown unavailable: {monthly.error}</p>}
          {monthlyRows.length > 0 && (
            <>
              <div className="legend" style={{ marginBottom: 10 }}>
                {MODELS.map((m) => (
                  <span key={m.key} className="legend-item">
                    <Swatch color={m.color} kind="line" />
                    {m.label}
                  </span>
                ))}
              </div>
              <div style={{ height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={monthlyRows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke="#eef2ef" vertical={false} />
                    <XAxis dataKey="month" tickFormatter={formatMonth} {...axis} axisLine={{ stroke: '#cfdcd3' }} />
                    <YAxis {...axis} axisLine={false} width={40} />
                    <Tooltip
                      cursor={{ stroke: '#86efac' }}
                      content={<ChartTooltip rows={lineRows} title={(m) => new Date(`${m}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })} />}
                    />
                    {MODELS.map((m) => (
                      <Line key={m.key} dataKey={m.key} stroke={m.color} strokeWidth={m.key === 'ml_model_p50' ? 3 : 2}
                        dot={{ r: 4, fill: m.color, stroke: '#fff', strokeWidth: 2 }} activeDot={{ r: 5 }} isAnimationActive={false} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </Card>

        <div className="grid cols-2">
          <Card title="Uncertainty calibration" subtitle="Share of actual values that fall inside the P10–P90 band. Target: 75%–85%.">
            <div className="gauge" role="img" aria-label={`Coverage ${fmt(coverage, 1)}%, target 75 to 85%`}>
              <div className="gauge-fill" style={{ width: `${Math.min(100, coverage)}%` }} />
              <div className="gauge-target" style={{ left: `${TARGET[0]}%`, width: `${TARGET[1] - TARGET[0]}%` }} />
              <div className="gauge-marker" style={{ left: `${Math.min(100, coverage)}%` }}>{fmt(coverage, 2)}%</div>
            </div>
            <div className="gauge-scale">
              <span>0%</span>
              <span>Target band 75–85%</span>
              <span>100%</span>
            </div>
            <p className="card-sub" style={{ marginTop: 14 }}>
              Quantile crossings (P10 &gt; P50 or P50 &gt; P90): <strong>{o.quantile_crossings ?? '—'}</strong>
            </p>
          </Card>

          {confRows.length > 0 && (
            <Card title="Does the confidence label mean something?" subtitle="MAE by forecast-confidence level, 2026 test set">
              <div className="stack" style={{ gap: 12 }}>
                {confRows.map((r) => {
                  const maxMae = Math.max(...confRows.map((x) => x.mae))
                  return (
                    <div key={r.level}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                        <span><b>{r.level}</b> <span className="card-sub">· {fmt((r.count / totalCount) * 100, 0)}% of hours</span></span>
                        <span className="num"><b>{fmt(r.mae, 2)}</b> W/m²</span>
                      </div>
                      <div style={{ height: 10, background: '#eef2ef', borderRadius: 999 }}>
                        <div style={{ height: '100%', width: `${(r.mae / maxMae) * 100}%`, background: 'var(--green-700)', borderRadius: 999 }} />
                      </div>
                    </div>
                  )
                })}
                <p className="card-sub">Low-confidence hours carry ~{fmt(confRows[confRows.length - 1].mae / confRows[0].mae, 0)}× the error of high-confidence hours, so operators can trust the label to flag risky days.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  )
}

function ErrorBars({ rows, metric }: { rows: { model: string; color: string; mae: number; rmse: number }[]; metric: 'mae' | 'rmse' }) {
  return (
    <div style={{ height: 240 }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 48, bottom: 0, left: 0 }} barCategoryGap={10}>
          <CartesianGrid stroke="#eef2ef" horizontal={false} />
          <XAxis type="number" {...axis} axisLine={false} />
          <YAxis type="category" dataKey="model" width={170} {...axis} axisLine={false} tick={{ fontSize: 12, fill: '#3d5246' }} />
          <Tooltip
            cursor={{ fill: '#f0fdf4' }}
            content={<ChartTooltip rows={[{ key: metric, label: metric.toUpperCase(), color: 'var(--green-700)', kind: 'box', unit: 'W/m²', digits: 2 }]} title={(m) => m} />}
          />
          <Bar
            dataKey={metric}
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
            label={{ position: 'right', fontSize: 12, fill: '#3d5246', formatter: (v: unknown) => fmt(Number(v), 1) }}
            shape={(p: unknown) => {
              const { x, y, width, height, payload } = p as { x: number; y: number; width: number; height: number; payload: { color: string } }
              const r = Math.min(4, width / 2)
              return <path d={`M${x},${y}h${width - r}a${r},${r} 0 0 1 ${r},${r}v${height - 2 * r}a${r},${r} 0 0 1 -${r},${r}h-${width - r}z`} fill={payload.color} />
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
