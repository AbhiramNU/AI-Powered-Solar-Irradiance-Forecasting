import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip, { type TooltipRow } from '../components/ChartTooltip'
import { Card, ErrorState, Loading, PageHeader, Stat, Swatch } from '../components/ui'
import { fmt, formatMonth, signed, useMetrics, useMonthly, type ModelMetrics } from '../lib/data'

const MODELS = [
  { key: 'ml_model_p50', label: 'SuryaCast ML (P50)', color: 'var(--series-model)' },
  { key: 'raw_nwp', label: 'Raw weather forecast (ECMWF)', color: 'var(--series-nwp)' },
  { key: 'persistence', label: 'Persistence (idealised)', color: 'var(--series-persistence)' },
] as const

const TARGET = [75, 85]
const axis = { tick: { fontSize: 12, fill: '#80695c' }, tickLine: false }

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
  const ci = o.skill_interval.vs_raw_nwp
  const beatsNwp = ml.mae < o.raw_nwp.mae
  const ind = metrics.data.independent_check
  const period = metrics.data.test_period

  const barRows = MODELS.map((m) => ({ model: m.label, color: m.color, ...(o[m.key] as ModelMetrics) }))
  const conf = metrics.data.by_confidence
  const confRows = conf
    ? (['High', 'Medium', 'Low'] as const).filter((k) => conf[k]).map((k) => ({ level: k, ...conf[k]! }))
    : []
  const totalCount = confRows.reduce((a, r) => a + r.site_days, 0)

  const lineRows: TooltipRow[] = MODELS.map((m) => ({ key: m.key, label: m.label, color: m.color, kind: 'line', unit: 'W/m²', digits: 1 }))

  return (
    <>
      <PageHeader eyebrow="02 · Accuracy Scorecard" title="How accurate is SuryaCast?" subtitle={`Test period ${period.start} to ${period.end}, all sites, daylight hours, scored against ERA5.`} />

      <div className="stack">
        <Card>
          <p style={{ fontSize: '1.05rem', color: 'var(--ink-2)' }}>
            Against ERA5, the model's mean absolute error is{' '}
            <strong style={{ color: 'var(--sun-800)' }}>{fmt(ml.mae, 1)} W/m²</strong>, {beatsNwp ? 'lower' : 'higher'} than the
            raw weather forecast it starts from (<strong>{fmt(o.raw_nwp.mae, 1)} W/m²</strong>): {signed(ml.skill)}% skill, with a{' '}
            {Math.round(ci.level * 100)}% interval of {signed(ci.low)}% to {signed(ci.high)}%.
            {ind && (
              <>
                {' '}Against the independent NASA POWER reference the model scores {fmt(ind.ml_model_p50.mae, 1)} W/m² and the raw
                forecast {fmt(ind.raw_nwp.mae, 1)} W/m², so {ind.ml_model_p50.mae < ind.raw_nwp.mae
                  ? 'the improvement carries over.'
                  : 'the gain against ERA5 does not carry over to an independent reference (details below).'}
              </>
            )}
          </p>
        </Card>

        <div className="grid cols-4">
          <Stat accent label="ML model P50 MAE" value={fmt(ml.mae, 2)} unit="W/m²" note={`RMSE ${fmt(ml.rmse, 2)} W/m²`} />
          <Stat label="Skill vs raw NWP" value={signed(ml.skill)} unit="%" note={`${Math.round(ci.level * 100)}% interval ${signed(ci.low)} to ${signed(ci.high)}%`} />
          <Stat label="Skill vs persistence" value={signed(skillVsPers)} unit="%" note="Idealised: uses yesterday's ERA5" />
          <Stat
            label="P10–P90 coverage (daylight)"
            value={fmt(coverage, 1)}
            unit="%"
            note={
              <span className={`pill ${coverageOk ? 'good' : 'warn'}`} style={{ marginTop: 2 }}>
                {coverageOk ? '✓ Within' : '! Outside'} 75–85% target
              </span>
            }
          />
        </div>

        <Card title="Model vs baselines" subtitle={`Daylight hours of the test period. Lower error is better. All-hours MAE: ML ${fmt(metrics.data.all_hours.ml_model_p50.mae, 1)}, raw forecast ${fmt(metrics.data.all_hours.raw_nwp.mae, 1)} W/m².`}>
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
                    <td className="r">{signed(r.bias, 2)}</td>
                    <td className="r">
                      {i === 0 ? `${signed(r.skill)}% vs NWP` : i === 1 ? `${signed(r.skill)}% vs persistence` : 'Reference'}
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

        {ind && (
          <Card title="Independent check" subtitle={`${ind.reference}: not used to train the model. ${ind.rows.toLocaleString('en-IN')} daylight test hours.`}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Forecast</th>
                    <th className="r">MAE vs NASA POWER (W/m²)</th>
                    <th className="r">Bias (W/m²)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="highlight"><td>SuryaCast ML (P50)</td><td className="r">{fmt(ind.ml_model_p50.mae, 1)}</td><td className="r">{signed(ind.ml_model_p50.bias, 1)}</td></tr>
                  <tr><td>Raw weather forecast (ECMWF)</td><td className="r">{fmt(ind.raw_nwp.mae, 1)}</td><td className="r">{signed(ind.raw_nwp.bias, 1)}</td></tr>
                  <tr><td>ERA5 (training target)</td><td className="r">{fmt(ind.era5.mae, 1)}</td><td className="r">{signed(ind.era5.bias, 1)}</td></tr>
                </tbody>
              </table>
            </div>
            <p className="card-sub" style={{ marginTop: 10 }}>
              {ind.ml_model_p50.mae < ind.raw_nwp.mae
                ? 'The model also beats the raw forecast against this independent reference.'
                : "The model does not beat the raw forecast against this reference. Its gain against ERA5 mostly comes from learning ERA5's systematic differences from the forecast, not from predicting sunlight better."}
            </p>
          </Card>
        )}

        <Card
          title="Monthly performance trend"
          subtitle="Monthly MAE (W/m², daylight hours) on the test period."
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
                    <CartesianGrid stroke="#f4ece6" vertical={false} />
                    <XAxis dataKey="month" tickFormatter={formatMonth} {...axis} axisLine={{ stroke: '#e3d4c8' }} />
                    <YAxis {...axis} axisLine={false} width={40} />
                    <Tooltip
                      cursor={{ stroke: '#fdba74' }}
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
          <Card title="Uncertainty calibration" subtitle="Share of daylight hours whose actual value falls inside the P10–P90 band. Target: 75%–85%.">
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
              Quantile crossings (P10 &gt; P50 or P50 &gt; P90): <strong>{o.quantile_crossings}</strong> · Daily totals coverage:{' '}
              <strong>{fmt(metrics.data.daily.p10_p90_coverage, 1)}%</strong> of {metrics.data.daily.days} site-days
            </p>
          </Card>

          {confRows.length > 0 && (
            <Card title="Does the confidence label mean something?" subtitle="Daylight MAE by forecast-confidence level, test period">
              <div className="stack" style={{ gap: 12 }}>
                {confRows.map((r) => {
                  const maxMae = Math.max(...confRows.map((x) => x.mae))
                  return (
                    <div key={r.level}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                        <span><b>{r.level}</b> <span className="card-sub">· {fmt((r.site_days / totalCount) * 100, 0)}% of site-days</span></span>
                        <span className="num"><b>{fmt(r.mae, 2)}</b> W/m²</span>
                      </div>
                      <div style={{ height: 10, background: '#f4ece6', borderRadius: 999 }}>
                        <div style={{ height: '100%', width: `${(r.mae / maxMae) * 100}%`, background: 'var(--sun-700)', borderRadius: 999 }} />
                      </div>
                    </div>
                  )
                })}
                <p className="card-sub">Low-confidence days carry about {fmt(confRows[confRows.length - 1].mae / confRows[0].mae, 1)}× the error of high-confidence days.</p>
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
          <CartesianGrid stroke="#f4ece6" horizontal={false} />
          <XAxis type="number" {...axis} axisLine={false} />
          <YAxis type="category" dataKey="model" width={170} {...axis} axisLine={false} tick={{ fontSize: 12, fill: '#523e33' }} />
          <Tooltip
            cursor={{ fill: '#fff7ed' }}
            content={<ChartTooltip rows={[{ key: metric, label: metric.toUpperCase(), color: 'var(--sun-700)', kind: 'box', unit: 'W/m²', digits: 2 }]} title={(m) => m} />}
          />
          <Bar
            dataKey={metric}
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
            label={{ position: 'right', fontSize: 12, fill: '#523e33', formatter: (v: unknown) => fmt(Number(v), 1) }}
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
