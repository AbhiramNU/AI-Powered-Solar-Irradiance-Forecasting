import { Link } from 'react-router-dom'
import { SunMark } from '../components/Layout'
import { PAGES } from '../lib/pages'
import { Stat } from '../components/ui'
import { fmt, useMetrics, useSites } from '../lib/data'

export default function Home() {
  const metrics = useMetrics()
  const sites = useSites()
  const o = metrics.data?.overall

  return (
    <>
      <section className="hero">
        <div>
          <div className="hero-title">SURYA CAST</div>
          <div className="hero-tag">"See Tomorrow's Sun."</div>
          <p className="lead">
            AI-powered next-day solar irradiance forecasting. SuryaCast predicts hourly GHI with P10/P50/P90 uncertainty bands across
            five Indian climate zones, helping operators plan renewable generation with confidence.
          </p>
          <div className="hero-actions">
            <Link to="/forecast" className="btn">View forecast →</Link>
            <Link to="/accuracy" className="btn ghost">See accuracy</Link>
          </div>
        </div>
        <div style={{ display: 'grid', placeItems: 'center' }}>
          <div style={{ width: 168, height: 168, borderRadius: '50%', background: 'var(--green-100)', display: 'grid', placeItems: 'center' }}>
            <div style={{ width: 112, height: 112, borderRadius: '50%', background: 'var(--green-700)', display: 'grid', placeItems: 'center' }}>
              <SunMark size={64} />
            </div>
          </div>
        </div>
      </section>

      {o && (
        <div className="grid cols-4" style={{ marginBottom: 28 }}>
          <Stat accent label="Model MAE (2026 test)" value={fmt(o.ml_model_p50.mae, 2)} unit="W/m²" />
          <Stat label="Skill vs raw weather forecast" value={`+${fmt(o.ml_model_p50.skill, 1)}`} unit="%" />
          <Stat label="P10–P90 coverage" value={fmt(o.p10_p90_coverage, 1)} unit="%" note="Target 75–85%" />
          <Stat label="Sites covered" value={sites.data?.length ?? '—'} note={sites.data?.map((s) => s.name).join(' · ')} />
        </div>
      )}

      <h2 style={{ marginBottom: 14 }}>Explore the dashboard</h2>
      <div className="grid cols-3">
        {PAGES.map((p) => (
          <Link key={p.path} to={p.path} className="card page-card">
            <span className="num-badge">{p.num}</span>
            <h3>{p.label}</h3>
            <p>{p.blurb}</p>
          </Link>
        ))}
      </div>
    </>
  )
}
