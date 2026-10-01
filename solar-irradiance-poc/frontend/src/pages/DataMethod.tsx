import { Fragment } from 'react'
import { Card, PageHeader } from '../components/ui'

const FLOW = [
  { title: 'Weather & solar features', note: 'Open-Meteo NWP, clouds, temp, humidity, pvlib sun position & clear-sky' },
  { title: 'ML model', note: 'LightGBM quantile regression ensemble' },
  { title: 'P10 / P50 / P90', note: 'Calibrated to 75–85% band coverage' },
  { title: 'Daily aggregation', note: 'Hourly GHI → daily irradiation & energy' },
  { title: 'Dashboard', note: 'Forecast, accuracy, locations, energy' },
]

export default function DataMethod() {
  return (
    <>
      <PageHeader eyebrow="05 · Data & Method" title="Data & methodology" subtitle="How SuryaCast is built, what it is trained on, and where it is headed." />

      <div className="stack">
        <Card title="Architecture pipeline">
          <div className="flow">
            {FLOW.map((s, i) => (
              <Fragment key={s.title}>
                {i > 0 && <div className="flow-arrow" aria-hidden>→</div>}
                <div className="flow-step">
                  {s.title}
                  <small>{s.note}</small>
                </div>
              </Fragment>
            ))}
          </div>
        </Card>

        <div className="grid cols-2">
          <Card title="1. Problem statement">
            <div className="prose">
              <p>
                Solar power generation is inherently volatile due to cloud cover and weather changes. Accurate forecasting helps grid
                operators balance supply and demand.
              </p>
              <p>
                This PoC predicts <strong>next-day hourly Global Horizontal Irradiance (GHI)</strong> during daylight hours (
                <strong>06:00–19:00 IST</strong>) across 5 Indian sites, generating P10, P50 and P90 confidence intervals.
              </p>
            </div>
          </Card>

          <Card title="2. Data sources & privacy">
            <div className="prose">
              <p>We strictly use public, modelled and satellite-derived meteorological data:</p>
              <ul>
                <li><strong>Open-Meteo APIs</strong>: Previous Runs, Historical Forecasts (GFS fallback), and ERA5 historical weather for ground truth.</li>
                <li><strong>NASA POWER</strong>: supplemental hourly GHI for cross-checking.</li>
                <li><strong>pvlib-python</strong>: solar position and clear-sky calculations.</li>
              </ul>
              <p>
                <em>Privacy:</em> SuryaCast runs entirely on public weather and reanalysis data. No personal user data, proprietary plant
                schematics or private commercial records are ingested or stored.
              </p>
            </div>
          </Card>

          <Card title="3. Training & test periods">
            <div className="prose">
              <ul>
                <li><strong>Training & tuning:</strong> January 2024 – December 2025</li>
                <li><strong>Test:</strong> January 2026 – September 2026</li>
              </ul>
              <p>The model is strictly evaluated on the unseen 2026 test period to ensure rigorous generalisation.</p>
            </div>
          </Card>

          <Card title="4. Model approach">
            <div className="prose">
              <p>An ensemble <strong>LightGBM quantile regression</strong> model.</p>
              <ul>
                <li><strong>Features:</strong> forecast GHI, low/mid/high cloud cover, temperature, relative humidity, sun elevation, clear-sky GHI, time embeddings and the previous day's clear-sky index.</li>
                <li><strong>Quantiles:</strong> P10 (conservative), P50 (expected), P90 (high generation).</li>
                <li><strong>Calibration:</strong> tuned to a 75%–85% P10–P90 coverage band.</li>
              </ul>
            </div>
          </Card>

          <Card title="5. Limitations & path to production">
            <div className="prose">
              <p><strong>Limitations:</strong> the PoC uses public modelled / satellite-derived data (ERA5, NASA POWER) as a proxy for ground truth rather than actual plant sensors.</p>
              <p><strong>Path to production:</strong></p>
              <ul>
                <li>Integrate ground-sensor pyranometer data via a live telemetry ingestion pipeline.</li>
                <li>Explore recurrent networks or transformers to capture temporal sequence dependencies.</li>
              </ul>
            </div>
          </Card>

          <Card title="6. Source attribution & licensing">
            <div className="prose">
              <ul>
                <li><strong>Open-Meteo</strong>: data provided under CC-BY 4.0.</li>
                <li><strong>NASA POWER</strong>: NASA Langley Research Center POWER Project.</li>
                <li><strong>pvlib-python</strong>: BSD 3-Clause License.</li>
                <li><strong>Map tiles</strong>: © OpenStreetMap contributors (ODbL).</li>
              </ul>
            </div>
          </Card>
        </div>

        <p className="card-sub" style={{ textAlign: 'center' }}>
          SuryaCast — Sahasranshu Technologies Private Limited · Rodic InfraAI Innovation Challenge 2026
        </p>
      </div>
    </>
  )
}
