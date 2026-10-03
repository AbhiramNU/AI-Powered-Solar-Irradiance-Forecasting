import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleMarker, MapContainer, TileLayer, Tooltip as MapTooltip } from 'react-leaflet'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import 'leaflet/dist/leaflet.css'
import ChartTooltip from '../components/ChartTooltip'
import { Card, ErrorState, Loading, PageHeader, Swatch } from '../components/ui'
import { fmt, formatMonth, signed, useMetrics, useMonthly, useSites } from '../lib/data'

/* Sequential single-hue ramp (light → dark orange) for error magnitude */
const RAMP = ['#fff7ed', '#fed7aa', '#fdba74', '#fb923c', '#ea580c', '#c2410c', '#7c2d12']

function rampColor(t: number) {
  const x = Math.max(0, Math.min(1, t)) * (RAMP.length - 1)
  const i = Math.min(RAMP.length - 2, Math.floor(x))
  const f = x - i
  const a = RAMP[i].match(/\w\w/g)!.map((h) => parseInt(h, 16))
  const b = RAMP[i + 1].match(/\w\w/g)!.map((h) => parseInt(h, 16))
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`
}

type SortKey = 'name' | 'mae' | 'rmse' | 'skill' | 'coverage'

export default function LocationComparison() {
  const sites = useSites()
  const metrics = useMetrics()
  const monthly = useMonthly()
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: 'mae', asc: true })

  const rows = useMemo(() => {
    if (!sites.data || !metrics.data) return []
    return sites.data.map((s) => {
      const m = metrics.data!.by_site[s.site_id]
      return {
        ...s,
        mae: m?.ml_model_p50.mae ?? NaN,
        rmse: m?.ml_model_p50.rmse ?? NaN,
        skill: m?.ml_model_p50.skill ?? NaN,
        coverage: m?.coverage ?? NaN,
        nwpMae: m?.raw_nwp.mae ?? NaN,
        persMae: m?.persistence.mae ?? NaN,
      }
    })
  }, [sites.data, metrics.data])

  const sorted = useMemo(() => {
    const r = [...rows]
    r.sort((a, b) => {
      const va = a[sort.key]
      const vb = b[sort.key]
      const c = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number)
      return sort.asc ? c : -c
    })
    return r
  }, [rows, sort])

  if (sites.error || metrics.error) return <ErrorState message={(sites.error || metrics.error)!} />
  if (!sites.data || !metrics.data) return <Loading />

  const maes = rows.map((r) => r.mae)
  const [minMae, maxMae] = [Math.min(...maes), Math.max(...maes)]
  const best = rows.find((r) => r.mae === minMae)
  const worst = rows.find((r) => r.mae === maxMae)

  const heat = monthly.data
  const heatVals = heat ? Object.values(heat.by_site).flat().filter((v): v is number => v != null) : []
  const [hMin, hMax] = [Math.min(...heatVals), Math.max(...heatVals)]

  const th = (key: SortKey, label: string, right = true) => (
    <th className={right ? 'r' : ''} aria-sort={sort.key === key ? (sort.asc ? 'ascending' : 'descending') : 'none'}>
      <button
        type="button"
        onClick={() => setSort((s) => ({ key, asc: s.key === key ? !s.asc : key === 'name' || key === 'mae' || key === 'rmse' }))}
        style={{ all: 'inherit', cursor: 'pointer', padding: 0, background: 'none' }}
      >
        {label} {sort.key === key ? (sort.asc ? '▲' : '▼') : ''}
      </button>
    </th>
  )

  return (
    <>
      <PageHeader eyebrow="03 · Location Comparison" title="How does performance vary across sites?" subtitle="Per-site performance on the test period: daylight hours, scored against ERA5." />

      <div className="stack">
        <div className="grid cols-2">
          <Card title="Site scorecard" subtitle={`Lowest error: ${best?.name} (${fmt(best?.mae, 2)} W/m²) · Highest: ${worst?.name} (${fmt(worst?.mae, 2)} W/m²)`}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {th('name', 'Site', false)}
                    <th>Climate zone</th>
                    {th('mae', 'MAE')}
                    {th('rmse', 'RMSE')}
                    {th('skill', 'Skill vs NWP')}
                    {th('coverage', 'Coverage')}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((r) => (
                    <tr key={r.site_id}>
                      <td><Link to={`/forecast?site=${r.site_id}`}><b>{r.name}</b></Link></td>
                      <td>{r.climate_zone}</td>
                      <td className="r">{fmt(r.mae, 2)}</td>
                      <td className="r">{fmt(r.rmse, 2)}</td>
                      <td className="r">{signed(r.skill)}%</td>
                      <td className="r">
                        <span className={`pill ${r.coverage >= 75 && r.coverage <= 85 ? 'good' : 'warn'}`}>{fmt(r.coverage, 1)}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="card-sub" style={{ marginTop: 10 }}>MAE and RMSE in W/m². Coverage target 75–85%. Click a site to open its forecast.</p>
          </Card>

          <Card title="Site map" subtitle="Marker colour = ML model MAE (darker = higher error)">
            <MapContainer center={[22.5, 78]} zoom={4} scrollWheelZoom={false} attributionControl>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                className="map-tiles"
              />
              {rows.map((r) => (
                <CircleMarker
                  key={r.site_id}
                  center={[r.latitude, r.longitude]}
                  radius={11}
                  pathOptions={{ color: '#ffffff', weight: 2, fillColor: rampColor(0.3 + 0.7 * ((r.mae - minMae) / (maxMae - minMae || 1))), fillOpacity: 1 }}
                >
                  <MapTooltip permanent direction="right" offset={[12, 0]} className="map-label">
                    {r.name} · {fmt(r.mae, 1)}
                  </MapTooltip>
                </CircleMarker>
              ))}
            </MapContainer>
          </Card>
        </div>

        <Card title="ML model vs raw weather forecast, by site" subtitle={`Daylight MAE in W/m². The model has lower error than the raw forecast at ${rows.filter((r) => r.mae < r.nwpMae).length} of ${rows.length} sites (against ERA5).`}>
          <div className="legend" style={{ marginBottom: 10 }}>
            <span className="legend-item"><Swatch color="var(--series-model)" kind="box" />SuryaCast ML (P50)</span>
            <span className="legend-item"><Swatch color="var(--series-nwp)" kind="box" />Raw weather forecast</span>
            <span className="legend-item"><Swatch color="var(--series-persistence)" kind="box" />Persistence (idealised)</span>
          </div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2} barCategoryGap="22%">
                <CartesianGrid stroke="#f4ece6" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#523e33' }} tickLine={false} axisLine={{ stroke: '#e3d4c8' }} />
                <YAxis tick={{ fontSize: 12, fill: '#80695c' }} tickLine={false} axisLine={false} width={40} />
                <Tooltip
                  cursor={{ fill: '#fff7ed' }}
                  content={
                    <ChartTooltip
                      title={(n) => n}
                      rows={[
                        { key: 'mae', label: 'SuryaCast ML', color: 'var(--series-model)', kind: 'box', unit: 'W/m²', digits: 2 },
                        { key: 'nwpMae', label: 'Raw weather forecast', color: 'var(--series-nwp)', kind: 'box', unit: 'W/m²', digits: 2 },
                        { key: 'persMae', label: 'Persistence (idealised)', color: 'var(--series-persistence)', kind: 'box', unit: 'W/m²', digits: 2 },
                      ]}
                    />
                  }
                />
                <Bar dataKey="mae" fill="var(--series-model)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="nwpMae" fill="var(--series-nwp)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="persMae" fill="var(--series-persistence)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Monthly error heatmap" subtitle="ML model daylight MAE (W/m²) by site and month, test period. Darker cells = larger error.">
          {monthly.error && <p className="card-sub">Site × month matrix unavailable: {monthly.error}</p>}
          {heat && (
            <div className="table-wrap">
              <div className="heatmap" style={{ gridTemplateColumns: `110px repeat(${heat.months.length}, minmax(44px, 1fr))`, minWidth: 560 }}>
                <div />
                {heat.months.map((m) => (
                  <div key={m} className="hm-col">{formatMonth(m)}</div>
                ))}
                {sites.data.map((s) => (
                  <HeatRow key={s.site_id} name={s.name} values={heat.by_site[s.site_id] ?? []} months={heat.months} min={hMin} max={hMax} />
                ))}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
                <span className="num">{fmt(hMin, 0)}</span>
                <span style={{ width: 160, height: 10, borderRadius: 999, background: `linear-gradient(90deg, ${RAMP.join(',')})` }} />
                <span className="num">{fmt(hMax, 0)} W/m²</span>
              </div>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}

function HeatRow({ name, values, months, min, max }: { name: string; values: (number | null)[]; months: string[]; min: number; max: number }) {
  return (
    <>
      <div className="hm-label">{name}</div>
      {months.map((m, i) => {
        const v = values[i]
        const t = v == null ? 0 : (v - min) / (max - min || 1)
        return (
          <div
            key={m}
            className="hm-cell"
            title={`${name}, ${formatMonth(m)}: ${fmt(v, 1)} W/m²`}
            style={{ background: v == null ? '#f7f1ec' : rampColor(t), color: t > 0.55 ? '#fff' : 'var(--ink)' }}
          >
            {fmt(v, 0)}
          </div>
        )
      })}
    </>
  )
}
