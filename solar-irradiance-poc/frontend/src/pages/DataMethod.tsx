import { Fragment } from 'react'
import { Card, PageHeader } from '../components/ui'

const FLOW = [
  { title: 'Day-ahead forecasts', note: 'ECMWF IFS, GFS and ICON via Open-Meteo, in UTC' },
  { title: 'Features', note: 'Forecast fields + pvlib sun position & clear-sky; no observations' },
  { title: 'ML model', note: 'LightGBM quantile regression, tuned on 2025' },
  { title: 'P10 / P50 / P90', note: 'Calibrated per site to 80% daylight coverage' },
  { title: 'Daily totals', note: 'Calibrated daily irradiation & energy' },
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
                This PoC predicts <strong>next-day hourly Global Horizontal Irradiance (GHI)</strong> for 5 Indian sites, with P10,
                P50 and P90 values, using only information available the evening before. Pages show <strong>06:00–19:00 IST</strong>;
                each hourly value is the mean over the hour centred on its label (12:00 = 11:30–12:30 IST).
              </p>
            </div>
          </Card>

          <Card title="2. Data sources & privacy">
            <div className="prose">
              <p>Public, modelled and satellite-derived data only:</p>
              <ul>
                <li><strong>Forecast input</strong>: Open-Meteo Previous Runs, day-ahead fields from pinned models ECMWF IFS (primary), GFS and ICON.</li>
                <li><strong>Reference "actual"</strong>: ERA5 reanalysis, pinned (the archive's default returns a different product for recent years).</li>
                <li><strong>Independent check</strong>: NASA POWER satellite-derived GHI, never used for training.</li>
                <li><strong>pvlib-python</strong>: solar position and clear-sky irradiance averaged over each hour, with site altitude.</li>
              </ul>
              <p>All data are requested in UTC; Open-Meteo's IST output is shifted by whole hours, which mislabels hourly means by 30 minutes.</p>
              <p>
                <em>Privacy:</em> SuryaCast runs entirely on public weather and reanalysis data. No personal user data, proprietary plant
                schematics or private commercial records are ingested or stored.
              </p>
            </div>
          </Card>

          <Card title="3. Training & test periods">
            <div className="prose">
              <ul>
                <li><strong>Train:</strong> 2024</li>
                <li><strong>Validation:</strong> 2025 — early stopping, blend weights, band calibration and confidence thresholds</li>
                <li><strong>Test:</strong> January – September 2026, scored once after refitting on 2024–2025</li>
              </ul>
              <p>Headline metrics use daylight hours only; at night every model is trivially right.</p>
            </div>
          </Card>

          <Card title="4. Model approach">
            <div className="prose">
              <p><strong>LightGBM quantile regression</strong>, one model per quantile.</p>
              <ul>
                <li><strong>Features:</strong> forecast GHI, direct and diffuse radiation, cloud cover, precipitation, temperature, humidity and pressure from three weather models, their clear-sky indices and spread, sun elevation, clear-sky GHI, day of year, hour and site. No observations; the pipeline refuses to build one.</li>
                <li><strong>P50</strong> is blended per site with the raw ECMWF forecast; <strong>P10–P90</strong> is scaled per site to cover 80% of 2025 daylight hours.</li>
                <li><strong>Confidence</strong> comes from forecast cloudiness and disagreement between weather models.</li>
              </ul>
            </div>
          </Card>

          <Card title="5. Limitations & path to production">
            <div className="prose">
              <p><strong>Limitations:</strong></p>
              <ul>
                <li>ERA5 and NASA POWER are modelled or satellite-derived, not plant pyranometers.</li>
                <li>ERA5 comes from the ECMWF model family, like the main forecast input. Much of the model's gain against ERA5 is learning ERA5's systematic differences; see the independent check on the Accuracy page.</li>
                <li>Persistence uses yesterday's ERA5, which is published days later, so it is an idealised reference.</li>
                <li>Each forecast hour comes from the model run about 24 hours earlier, approximating an evening issue time.</li>
              </ul>
              <p><strong>Path to production:</strong></p>
              <ul>
                <li>Integrate ground-sensor pyranometer data via a live telemetry ingestion pipeline.</li>
                <li>Train on longer forecast archives and score against an independent satellite or ground reference.</li>
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
          SuryaCast is a product of Sahasranshu Technologies Private Limited · Rodic InfraAI Innovation Challenge 2026
        </p>
      </div>
    </>
  )
}
