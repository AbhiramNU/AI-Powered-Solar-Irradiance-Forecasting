import { Link } from 'react-router-dom'
import { LogoMark } from '../components/Layout'
import { PAGES } from '../lib/pages'
import { Stat } from '../components/ui'
import { fmt, signed, useMetrics, useSites } from '../lib/data'

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
          <div className="hero-maker">A product of Sahasranshu Technologies</div>
          <p className="lead">
            Next-day solar irradiance forecasting. SuryaCast predicts hourly GHI with P10/P50/P90 ranges for five Indian sites
            from public weather forecasts, and shows every prediction next to what happened.
          </p>
          <div className="hero-actions">
            <Link to="/forecast" className="btn">View forecast →</Link>
            <Link to="/accuracy" className="btn ghost">See accuracy</Link>
          </div>
        </div>
        <div style={{ display: 'grid', placeItems: 'center' }}>
          <div style={{ width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, var(--sun-100) 0%, var(--sun-50) 60%, transparent 72%)', display: 'grid', placeItems: 'center' }}>
            <LogoMark size={168} />
          </div>
        </div>
      </section>

      {o && (
        <div className="grid cols-4" style={{ marginBottom: 28 }}>
          <Stat accent label="Model MAE (test, daylight)" value={fmt(o.ml_model_p50.mae, 1)} unit="W/m²" note="Against ERA5" />
          <Stat label="Skill vs raw weather forecast" value={signed(o.ml_model_p50.skill)} unit="%" note={
            metrics.data?.independent_check
              ? `Against NASA POWER: ${signed(metrics.data.independent_check.ml_model_p50.skill)}%`
              : 'Against ERA5'
          } />
          <Stat label="P10–P90 coverage" value={fmt(o.p10_p90_coverage, 1)} unit="%" note="Daylight hours, target 75–85%" />
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
